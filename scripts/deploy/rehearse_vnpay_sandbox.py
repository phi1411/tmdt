"""Prepare/inspect/clean uniquely owned public Sandbox fixtures; never forge IPN."""
import argparse
import json
import secrets
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from urllib.parse import urlencode, urlsplit
from bson import ObjectId, json_util
from pymongo import MongoClient
from pymongo.read_concern import ReadConcern
from pymongo.write_concern import WriteConcern
from migrate_sku_reviews import ROOT, COLLECTIONS, fingerprint

PRIVATE=ROOT/'.local/vnpay-sandbox'
JOURNAL=PRIVATE/'live-journal.json'
API='https://novamart-api.onrender.com/api/v1'
ORIGIN='https://novamart-web.onrender.com'


def http(method,path,payload=None,token=None,key=None,expected=200):
    headers={'Content-Type':'application/json','Origin':ORIGIN}
    if token: headers['Authorization']='Bearer '+token
    if key: headers['Idempotency-Key']=key
    req=Request(API+path,method=method,headers=headers,data=json.dumps(payload).encode() if payload is not None else None)
    try: response=urlopen(req,timeout=60)
    except HTTPError as error: response=error
    with response:
        body=json.loads(response.read())
        assert response.status==expected,(path,response.status,body.get('error',{}).get('code'))
        return body.get('data',body)


def save(journal):
    JOURNAL.write_text(json.dumps(journal,ensure_ascii=False,indent=2),encoding='utf-8')


def prepare(db,admin_file):
    assert not JOURNAL.exists(),'Clean the previous owned rehearsal before starting another'
    assert http('GET','/health')['status']=='ok'
    assert http('GET','/payments/vnpay/ipn')['RspCode']=='97','Merchant verifier is not configured'
    run='vnp-live-'+secrets.token_hex(6)
    journal={'run':run,'email':run+'@example.test','password':secrets.token_urlsafe(24),'sku':run.upper(),
        'beforeFingerprint':fingerprint(db),'beforeCounts':{n:db[n].count_documents({}) for n in COLLECTIONS}}
    save(journal)
    try:
        credentials=json.loads(admin_file.read_text(encoding='utf-8'))
        admin=http('POST','/auth/login',{'email':'admin@example.test','password':credentials['adminPassword']})['accessToken']
        user=http('POST','/auth/register',{'name':'VNPAY Sandbox Test','email':journal['email'],'password':journal['password'],'phone':'0901234567'},expected=201)['user']
        journal['userId']=user['id'];save(journal)
        token=http('POST','/auth/login',{'email':journal['email'],'password':journal['password']})['accessToken']
        profile=http('GET','/users/me',token=token)
        address=http('POST','/users/me/addresses',{'expectedVersion':profile['version'],'receiverName':'Sandbox Test',
            'phone':'0901234567','addressLine':'Địa chỉ kiểm thử','province':'Hồ Chí Minh'},token,expected=201)['address']['id']
        category=http('POST','/admin/categories',{'name':'Sandbox '+run,'slug':run,'productType':'FASHION'},admin,expected=201)
        journal['categoryId']=category['id'];save(journal)
        product=http('POST','/admin/products',{'sku':journal['sku'],'name':'Áo kiểm thử VNPAY','slug':run,
            'categoryId':category['id'],'productType':'FASHION','brand':'','description':'Temporary owned Sandbox rehearsal',
            'price':100000,'stock':10,'images':[],'attributes':{'sizes':['M','XL'],'colors':['Đen'],'material':'Cotton'},'status':'ACTIVE',
            'tierVariations':[{'name':'Size','options':['M','XL']}],
            'skus':[{'skuId':journal['sku']+'-M','tierIndex':[0],'price':100000,'stock':7},
                    {'skuId':journal['sku']+'-XL','tierIndex':[1],'price':120000,'stock':3}]},admin,expected=201)
        journal['productId']=product['id'];save(journal)
        cart=http('GET','/cart',token=token)
        cart=http('POST','/cart/items',{'cartVersion':cart['version'],'productId':product['id'],'quantity':1,
            'selectedAttributes':{'Size':'M','skuId':journal['sku']+'-M'}},token)
        quote=http('GET','/checkout/quote?'+urlencode({'addressId':address,'paymentMethod':'VNPAY'}),token=token)
        created=http('POST','/orders',{'cartVersion':cart['version'],'addressId':address,'paymentMethod':'VNPAY','quoteToken':quote['quoteToken']},
            token,key=run,expected=201)
        journal.update(orderId=created['order']['id'],orderCode=created['order']['orderCode'],payment=created['payment'])
        assert urlsplit(journal['payment']['paymentUrl']).hostname=='sandbox.vnpayment.vn'
        save(journal)
        return {'run':run,'orderCode':journal['orderCode'],'total':created['order']['total'],'expiresAt':created['order']['paymentExpiresAt']}
    except BaseException:
        cleanup(db,journal)
        raise


def additional_order(db,journal):
    token=http('POST','/auth/login',{'email':journal['email'],'password':journal['password']})['accessToken']
    profile=http('GET','/users/me',token=token)
    address=profile['defaultAddressId'] or profile['addresses'][0]['id']
    cart=http('GET','/cart',token=token)
    if not cart['items']:
        cart=http('POST','/cart/items',{'cartVersion':cart['version'],'productId':journal['productId'],'quantity':1,
            'selectedAttributes':{'Size':'M','skuId':journal['sku']+'-M'}},token)
    else:
        assert len(cart['items'])==1 and cart['items'][0]['productId']==journal['productId'] and cart['items'][0]['quantity']==1
    quote=http('GET','/checkout/quote?'+urlencode({'addressId':address,'paymentMethod':'VNPAY'}),token=token)
    key=journal['run']+'-'+secrets.token_hex(4)
    journal.setdefault('additionalKeys',[]).append(key);save(journal)
    created=http('POST','/orders',{'cartVersion':cart['version'],'addressId':address,'paymentMethod':'VNPAY','quoteToken':quote['quoteToken']},token,key=key,expected=201)
    value={'orderId':created['order']['id'],'orderCode':created['order']['orderCode'],'payment':created['payment']}
    journal.setdefault('additionalOrders',[]).append(value);save(journal)
    return {'orderCode':value['orderCode'],'total':created['order']['total'],'expiresAt':created['order']['paymentExpiresAt']}


def inspect(db,journal):
    order=db.orders.find_one({'_id':ObjectId(journal['orderId']),'userId':ObjectId(journal['userId'])})
    assert order
    attempts=list(db.payment_attempts.find({'orderId':order['_id']}))
    product=db.products.find_one({'_id':ObjectId(journal['productId'])})
    return {'recordedAtUtc':datetime.now(timezone.utc).isoformat(),'run':journal['run'],'orderCode':order['orderCode'],
        'orderStatus':order['orderStatus'],'paymentStatus':order['paymentStatus'],'paymentReviewRequired':order['paymentReviewRequired'],
        'total':int(order['total']),'rootStock':product['stock'],'skuStocks':[s['stock'] for s in product['skus']],
        'attempts':[{'status':a['status'],'providerTransactionNo':a.get('providerTransactionNo'),
            'hasVerifiedCallbackFingerprint':bool(a.get('callbackFingerprint'))} for a in attempts]}


def cleanup(db,journal):
    user=db.users.find_one({'email':journal['email']})
    owner=user['_id'] if user else None
    product=db.products.find_one({'sku':journal['sku']})
    category=db.categories.find_one({'slug':journal['run']})
    if product:
        assert db.orders.count_documents({'items.productId':product['_id'],'userId':{'$ne':owner}})==0
        assert db.carts.count_documents({'items.productId':product['_id'],'userId':{'$ne':owner}})==0
    owned={name:list(db[name].find({'_id':owner} if name=='users' else {'userId':owner})) for name in ('users','orders','carts','payment_attempts','reviews')} if owner else {}
    (PRIVATE/(journal['run']+'-cleanup-backup.ejson')).write_text(json_util.dumps(owned,json_options=json_util.CANONICAL_JSON_OPTIONS),encoding='utf-8')
    removed={}
    with db.client.start_session() as session:
        with session.start_transaction(read_concern=ReadConcern('snapshot'),write_concern=WriteConcern('majority')):
            if owner:
                for name in ('reviews','payment_attempts','orders','carts'):
                    removed[name]=db[name].delete_many({'userId':owner},session=session).deleted_count
                removed['users']=db.users.delete_one({'_id':owner,'email':journal['email']},session=session).deleted_count
            if product: removed['products']=db.products.delete_one({'_id':product['_id'],'sku':journal['sku']},session=session).deleted_count
            if category:
                assert db.products.count_documents({'categoryId':category['_id']},session=session)==0
                removed['categories']=db.categories.delete_one({'_id':category['_id'],'slug':journal['run']},session=session).deleted_count
    after=fingerprint(db)
    report={'run':journal['run'],'beforeFingerprint':journal['beforeFingerprint'],'afterFingerprint':after,
        'exactCleanup':journal['beforeFingerprint']==after,'removedOwnedDocuments':removed,'counts':{n:db[n].count_documents({}) for n in COLLECTIONS}}
    (ROOT/'backend/evidence/vnpay-sandbox-cleanup.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    JOURNAL.rename(PRIVATE/(journal['run']+'-finished.json'))
    assert report['exactCleanup'],'Unrelated baseline changed; inspect without resetting data'
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['prepare','add-order','inspect','cleanup'])
    parser.add_argument('--connection-file',type=Path,required=True)
    parser.add_argument('--admin-credentials-file',type=Path)
    args=parser.parse_args()
    config=json.loads(args.connection_file.read_text(encoding='utf-8'))
    assert config['database']=='novamart_demo' and urlsplit(config['uri']).hostname=='cluster0.asxeso0.mongodb.net'
    client=MongoClient(config['uri'],tls=True,replicaSet='atlas-uczcqo-shard-0',tz_aware=True,serverSelectionTimeoutMS=15000)
    try:
        db=client[config['database']]
        if args.action=='prepare':result=prepare(db,args.admin_credentials_file)
        else:
            journal=json.loads(JOURNAL.read_text(encoding='utf-8'))
            result=additional_order(db,journal) if args.action=='add-order' else inspect(db,journal) if args.action=='inspect' else cleanup(db,journal)
        print(json.dumps(result,indent=2))
    finally:client.close()
