"""Additive, backed-up SKU/review migration. Default is read-only planning."""
import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit
from bson import Int64, json_util
from pymongo import MongoClient

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/db'))
from common import COLLECTIONS, selected_indexes, read_json


def fingerprint(db):
    corpus={name:list(db[name].find().sort('_id',1)) for name in COLLECTIONS}
    return hashlib.sha256(json_util.dumps(corpus,json_options=json_util.CANONICAL_JSON_OPTIONS,sort_keys=True).encode()).hexdigest()


def eligible(review, orders):
    order=orders.get(review['orderId'])
    return bool(order and order['userId']==review['userId'] and order['orderStatus']=='COMPLETED'
        and order['paymentStatus']=='PAID' and any(item['productId']==review['productId'] for item in order['items']))


def migrate(client, db, apply=False):
    products=list(db.products.find())
    orders={order['_id']:order for order in db.orders.find()}
    reviews=list(db.reviews.find())
    ids={product['_id'] for product in products}
    if any(review['productId'] not in ids for review in reviews):
        raise RuntimeError('Orphan review requires explicit reconciliation')
    duplicate=list(db.reviews.aggregate([{'$group':{'_id':{'u':'$userId','o':'$orderId','p':'$productId'},'n':{'$sum':1}}},{'$match':{'n':{'$gt':1}}}]))
    if duplicate: raise RuntimeError('Duplicate reviews require explicit reconciliation before unique index')
    quarantined=[review['_id'] for review in reviews if review['status']=='VISIBLE' and not eligible(review,orders)]
    updates=[]
    for product in products:
        fields={}
        if product.get('tierVariations'):
            from copy import deepcopy
            sys.path.insert(0,str(ROOT/'backend'))
            from app.schemas.product_variants import validate_variants
            candidate=deepcopy(product)
            validate_variants(candidate)
            if candidate['stock']!=product['stock'] and any(
                any(item['productId']==product['_id'] for item in order['items']) for order in orders.values()):
                raise RuntimeError('SKU stock mismatch on a referenced Product requires manual inventory reconciliation')
            if candidate['stock']!=product['stock']:fields['stock']=candidate['stock']
            if candidate['price']!=product['price']:fields['price']=Int64(candidate['price'])
        visible=[review for review in reviews if review['productId']==product['_id'] and review['status']=='VISIBLE' and review['_id'] not in quarantined]
        if visible or 'ratingSummary' in product:
            counts={str(i):sum(review['rating']==i for review in visible) for i in range(1,6)}
            total=sum(counts.values())
            summary={'totalReviews':total,'averageRating':round(sum(int(k)*v for k,v in counts.items())/total,1) if total else 0.0,'starsBreakdown':counts}
            if product.get('ratingSummary')!=summary:fields['ratingSummary']=summary
        if fields:
            if product['version']>=2147483647:raise RuntimeError('Product version limit')
            updates.append((product,fields))
    before=fingerprint(db)
    report={'mode':'APPLY' if apply else 'DRY_RUN','database':db.name,'beforeFingerprint':before,
        'counts':{name:db[name].count_documents({}) for name in COLLECTIONS},
        'productUpdates':len(updates),'reviewsPendingAudit':len(quarantined),
        'validators':len(COLLECTIONS),'declaredIndexes':len(selected_indexes())}
    if apply:
        stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        folder=ROOT/'.local/hardening-migration'/stamp
        folder.mkdir(parents=True,exist_ok=False)
        backup={'documents':{name:list(db[name].find()) for name in COLLECTIONS},
            'options':list(db.list_collections()),'indexes':{name:list(db[name].list_indexes()) for name in db.list_collection_names() if name in COLLECTIONS}}
        (folder/'exact-backup.ejson').write_text(json_util.dumps(backup,json_options=json_util.CANONICAL_JSON_OPTIONS),encoding='utf-8')
        assert before==fingerprint(db),'Concurrent database writes detected before migration'
        now=datetime.now(timezone.utc)
        # Data changes only exact planned IDs, with transaction/version guards.
        if updates or quarantined:
            with client.start_session() as session:
                with session.start_transaction():
                    for product,fields in updates:
                        result=db.products.update_one({'_id':product['_id'],'version':product['version']},
                            {'$set':{**fields,'updatedAt':now},'$inc':{'version':1}},session=session)
                        assert result.matched_count==1,'Concurrent Product update'
                    for rid in quarantined:
                        result=db.reviews.update_one({'_id':rid,'status':'VISIBLE'},
                            {'$set':{'status':'PENDING_AUDIT','updatedAt':now}},session=session)
                        assert result.matched_count==1,'Concurrent review update'
        existing=set(db.list_collection_names())
        for name in COLLECTIONS:
            validator=read_json(f'database/validators/{name}.json')
            if name in existing:db.command('collMod',name,validator=validator,validationLevel='strict',validationAction='error')
            else:db.create_collection(name,validator=validator,validationLevel='strict',validationAction='error')
        for index in selected_indexes():
            db[index['collection']].create_index(list(index['keys'].items()),**index['options'])
        invalid={name:db[name].count_documents({'$nor':[read_json(f'database/validators/{name}.json')]}) for name in COLLECTIONS}
        assert not any(invalid.values()),invalid
        report.update(afterFingerprint=fingerprint(db),invalidDocuments=invalid,
            afterCounts={name:db[name].count_documents({}) for name in COLLECTIONS},backup=str(folder/'exact-backup.ejson'))
        assert report['counts']==report['afterCounts'],'Migration must preserve document counts'
        (folder/'receipt.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--connection-file',type=Path)
    parser.add_argument('--database',choices=['ecommerce_dev','ecommerce_test'],default='ecommerce_dev')
    parser.add_argument('--apply',action='store_true')
    parser.add_argument('--report',type=Path)
    args=parser.parse_args()
    if args.connection_file:
        config=json.loads(args.connection_file.read_text(encoding='utf-8'))
        uri=config['uri']; name=config['database']
        parsed=urlsplit(uri)
        assert parsed.scheme=='mongodb+srv' and parsed.hostname=='cluster0.asxeso0.mongodb.net' and name=='novamart_demo'
        client=MongoClient(uri,tls=True,serverSelectionTimeoutMS=15000,replicaSet='atlas-uczcqo-shard-0',tz_aware=True)
    else:
        name=args.database
        client=MongoClient('mongodb://localhost:27017/?replicaSet=rs0',serverSelectionTimeoutMS=5000,tz_aware=True)
        actual=Path(client.admin.command('getCmdLineOpts')['parsed']['storage']['dbPath']).resolve()
        assert actual in {(ROOT/'.local/review/mongo-data').resolve(),(ROOT/'.local/mongodb/data').resolve()},'Unexpected MongoDB storage'
    try:
        hello=client.admin.command('hello')
        assert hello.get('isWritablePrimary') and hello.get('logicalSessionTimeoutMinutes') is not None
        result=migrate(client,client[name],args.apply)
        print(json.dumps(result,indent=2))
        if args.report:
            args.report.parent.mkdir(parents=True,exist_ok=True)
            args.report.write_text(json.dumps(result,indent=2),encoding='utf-8')
    finally:client.close()
