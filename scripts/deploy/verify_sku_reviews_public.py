"""Verify existing Render demo using uniquely owned fixtures and exact cleanup."""
import argparse
import copy
import json
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen

from bson import ObjectId, json_util
from pymongo import MongoClient
from pymongo.read_concern import ReadConcern
from pymongo.write_concern import WriteConcern
from migrate_sku_reviews import ROOT, COLLECTIONS, fingerprint, read_json, selected_indexes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--connection-file', type=Path, required=True)
    parser.add_argument('--admin-credentials-file', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    config = json.loads(args.connection_file.read_text(encoding='utf-8'))
    assert urlsplit(config['uri']).hostname == 'cluster0.asxeso0.mongodb.net' and config['database'] == 'novamart_demo'
    client = MongoClient(config['uri'], tls=True, replicaSet='atlas-uczcqo-shard-0', tz_aware=True, serverSelectionTimeoutMS=15000)
    db = client[config['database']]
    api, origin = 'https://novamart-api.onrender.com/api/v1', 'https://novamart-web.onrender.com'
    run = 'hardening-' + secrets.token_hex(6)
    emails = [run + suffix + '@example.test' for suffix in ('-a', '-b')]
    sku = run.upper()
    folder = ROOT / '.local/hardening-public' / run
    folder.mkdir(parents=True, exist_ok=False)
    before = fingerprint(db)
    counts = {name: db[name].count_documents({}) for name in COLLECTIONS}
    backup = {'documents': {name: list(db[name].find()) for name in COLLECTIONS},
        'options': list(db.list_collections()), 'indexes': {name:list(db[name].list_indexes()) for name in COLLECTIONS}}
    (folder/'baseline.ejson').write_text(json_util.dumps(backup, json_options=json_util.CANONICAL_JSON_OPTIONS), encoding='utf-8')
    (folder/'ownership.json').write_text(json.dumps({'emails':emails, 'sku':sku, 'categorySlug':run}), encoding='utf-8')
    checks, results = [], {}

    def http(method, path, expected=200, payload=None, token=None, key=None, allowed_origin=True):
        headers = {'Content-Type':'application/json', 'Origin':origin if allowed_origin else 'https://untrusted.example.test'}
        if token: headers['Authorization'] = 'Bearer ' + token
        if key: headers['Idempotency-Key'] = key
        request = Request(api + path, method=method, headers=headers,
            data=json.dumps(payload).encode() if payload is not None else None)
        try: response = urlopen(request, timeout=60)
        except HTTPError as error: response = error
        with response:
            body = json.loads(response.read())
            assert response.status == expected, (method,path,response.status,body.get('error',{}).get('code'))
            assert response.headers.get('Access-Control-Allow-Origin') == (origin if allowed_origin else None)
            checks.append({'method':method,'path':path,'status':response.status})
            return body.get('data', body)

    try:
        http('GET','/health')
        http('GET','/health',allowed_origin=False)
        http('GET','/admin/users',401)
        http('GET','/auth/me',401,token='invalid.jwt.token')
        for kind in ('ELECTRONICS','FASHION','HOME_APPLIANCE'):
            products = http('GET','/products?'+urlencode({'productType':kind,'pageSize':1}))
            assert products and http('GET','/products/'+products[0]['slug'])['attributes']
        http('GET','/products?q=07C')
        password = json.loads(args.admin_credentials_file.read_text(encoding='utf-8'))['adminPassword']
        admin = http('POST','/auth/login',payload={'email':'admin@example.test','password':password})['accessToken']
        tokens, users = [], []
        for email in emails:
            password = secrets.token_urlsafe(24)
            user = http('POST','/auth/register',201,payload={'name':'Kiểm thử hệ thống','email':email,'password':password,'phone':'0901234567'})['user']
            users.append(user)
            tokens.append(http('POST','/auth/login',payload={'email':email,'password':password})['accessToken'])
        customer, other = tokens
        http('GET','/auth/me',token=customer)
        http('GET','/admin/users',403,token=customer)
        profile = http('GET','/users/me',token=customer)
        address = http('POST','/users/me/addresses',201,payload={'expectedVersion':profile['version'],
            'receiverName':'Kiểm thử COD','phone':'0901234567','addressLine':'Địa chỉ kiểm thử','province':'Hồ Chí Minh'},token=customer)['address']['id']
        category = http('POST','/admin/categories',201,payload={'name':'Kiểm thử '+run,'slug':run,'productType':'FASHION'},token=admin)
        product = http('POST','/admin/products',201,payload={'sku':sku,'name':'Áo kiểm thử '+run,'slug':run,
            'categoryId':category['id'],'productType':'FASHION','brand':'','description':'Temporary owned verification',
            'price':1,'stock':0,'images':[],'attributes':{'material':'Cotton','sizes':['S','XL'],'colors':['Đen']},'status':'ACTIVE',
            'tierVariations':[{'name':'Size','options':['S','XL']}],
            'skus':[{'skuId':sku+'-S','tierIndex':[0],'price':100000,'stock':2},
                    {'skuId':sku+'-XL','tierIndex':[1],'price':120000,'stock':3}]},token=admin)
        assert product['stock']==5 and product['price']==100000
        pid=product['id']

        def order(index):
            cart=http('GET','/cart',token=customer)
            selection={'Size':['S','XL'][index], 'skuId':sku+['-S','-XL'][index]}
            http('POST','/cart/items',422,payload={'productId':pid,'quantity':1,'cartVersion':cart['version'],
                'selectedAttributes':{**selection,'skuId':'UNKNOWN'}},token=customer)
            cart=http('POST','/cart/items',payload={'productId':pid,'quantity':1,'cartVersion':cart['version'],'selectedAttributes':selection},token=customer)
            quote=http('GET','/checkout/quote?'+urlencode({'addressId':address,'paymentMethod':'COD'}),token=customer)
            intent={'addressId':address,'paymentMethod':'COD','cartVersion':cart['version'],'quoteToken':quote['quoteToken']}
            http('POST','/orders',422,payload={**intent,'total':1},token=customer,key=run+'-tamper')
            key=run+'-'+secrets.token_hex(4)
            created=http('POST','/orders',201,payload=intent,token=customer,key=key)['order']
            assert http('POST','/orders',payload=intent,token=customer,key=key)['order']['id']==created['id']
            return created

        first=order(0)
        http('GET','/orders/'+first['id'],404,token=other)
        http('POST','/products/'+pid+'/reviews',409,payload={'orderId':first['id'],'rating':5},token=customer)
        for _ in range(2): http('POST','/orders/'+first['id']+'/cancel',payload={'expectedVersion':first['version']},token=customer)
        current=http('GET','/admin/products/'+pid,token=admin)
        assert current['stock']==5 and current['skus'][0]['stock']==2
        window=urlencode({'from':(datetime.now(timezone.utc)-timedelta(days=1)).isoformat(),'to':(datetime.now(timezone.utc)+timedelta(days=1)).isoformat()})
        revenue=http('GET','/admin/dashboard/summary?'+window,token=admin)['totalRevenue']
        second=order(1)
        snapshot=copy.deepcopy(second['items'])
        current=http('GET','/admin/products/'+pid,token=admin)
        updated=copy.deepcopy(current['skus']);updated[1]['price']=140000
        http('PATCH','/admin/products/'+pid,payload={'expectedVersion':current['version'],'skus':updated,'tierVariations':current['tierVariations']},token=admin)
        assert http('GET','/orders/'+second['id'],token=customer)['items']==snapshot
        assert snapshot[0]['priceAtPurchase']==120000
        for action in ('confirm','ship','complete'):
            second=http('POST','/admin/orders/'+second['id']+'/'+action,payload={'expectedVersion':second['version']},token=admin)
        assert second['orderStatus']=='COMPLETED' and second['paymentStatus']=='PAID'
        assert http('GET','/admin/dashboard/summary?'+window,token=admin)['totalRevenue']-revenue==120000
        for report in ('revenue','top-products','category-revenue','order-status'):
            http('GET','/admin/dashboard/'+report+'?'+window,token=admin)
        review={'orderId':second['id'],'rating':5,'reviewText':'Kiểm thử đánh giá sau COD hoàn tất'}
        http('POST','/products/'+pid+'/reviews',404,payload=review,token=other)
        http('POST','/products/'+pid+'/reviews',201,payload=review,token=customer)
        http('POST','/products/'+pid+'/reviews',409,payload=review,token=customer)
        feed=http('GET','/products/'+run+'/reviews?pageSize=1')
        assert feed['stats']['totalReviews']==1 and feed['stats']['averageRating']==5.0
        assert len(feed['reviews'])==1 and not {'userId','orderId','orderCode'}.intersection(feed['reviews'][0])
        assert '***' in feed['reviews'][0]['userSnapshot']['displayName']
        assert http('GET','/products/'+run+'/reviews?rating=4')['reviews']==[]
        current=http('GET','/admin/products/'+pid,token=admin)
        assert current['stock']==4 and [s['stock'] for s in current['skus']]==[2,2]
        blocked=http('GET','/admin/users/'+users[1]['id'],token=admin)
        http('PATCH','/admin/users/'+users[1]['id']+'/status',payload={'expectedVersion':blocked['version'],'status':'BLOCKED'},token=admin)
        http('GET','/auth/me',401,token=other)
        results.update(skuCod='PASS',cancelOnce='PASS',snapshot='PASS',adminLifecycle='PASS',reviews='PASS',security='PASS',revenueDelta=120000)
    finally:
        owners=[u['_id'] for u in db.users.find({'email':{'$in':emails}}, {'_id':1})]
        found=db.products.find_one({'sku':sku})
        category=db.categories.find_one({'slug':run})
        if found:
            assert not db.orders.count_documents({'items.productId':found['_id'],'userId':{'$nin':owners}})
            assert not db.carts.count_documents({'items.productId':found['_id'],'userId':{'$nin':owners}})
        removed={}
        with client.start_session() as session:
            with session.start_transaction(read_concern=ReadConcern('snapshot'),write_concern=WriteConcern('majority')):
                for name in ('reviews','payment_attempts','orders','carts','users'):
                    query={'_id':{'$in':owners}} if name=='users' else {'userId':{'$in':owners}}
                    removed[name]=db[name].delete_many(query,session=session).deleted_count
                if found: removed['products']=db.products.delete_one({'_id':found['_id'],'sku':sku},session=session).deleted_count
                if category:
                    assert not db.products.count_documents({'categoryId':category['_id']},session=session)
                    removed['categories']=db.categories.delete_one({'_id':category['_id'],'slug':run},session=session).deleted_count
        after=fingerprint(db)
        invalid={name:db[name].count_documents({'$nor':[read_json(f'database/validators/{name}.json')]}) for name in COLLECTIONS}
        options={value['name']:value['options'] for value in db.list_collections()}
        validators_match=all(options[name].get('validator')==read_json(f'database/validators/{name}.json')
            and options[name].get('validationLevel')=='strict' and options[name].get('validationAction')=='error' for name in COLLECTIONS)
        indexes_match=True
        for index in selected_indexes():
            actual=db[index['collection']].index_information().get(index['options']['name'])
            indexes_match=indexes_match and bool(actual and actual['key']==list(index['keys'].items())
                and all(actual.get(key)==value for key,value in index['options'].items() if key!='name'))
        report={'recordedAtUtc':datetime.now(timezone.utc).isoformat(),'checks':checks,'results':results,
            'beforeFingerprint':before,'afterFingerprint':after,'exactCleanup':before==after,'counts':counts,
            'afterCounts':{name:db[name].count_documents({}) for name in COLLECTIONS},'invalidDocuments':invalid,
            'removedOwnedDocuments':removed,'validators':7,'declaredIndexes':len(selected_indexes()),
            'canonicalValidatorsMatch':validators_match,'canonicalIndexesMatch':indexes_match,
            'vnpayLive':'DISABLED_NOT_TESTED','resetReseed':False}
        args.report.parent.mkdir(parents=True,exist_ok=True)
        args.report.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
        client.close()
        assert before==after and not any(invalid.values()) and validators_match and indexes_match, 'Inspect integrity receipt; never reset unrelated data'
    assert results.get('skuCod')=='PASS'
    print(json.dumps({'status':'PUBLIC_SKU_REVIEW_PASS','httpChecks':len(checks),'exactCleanup':True}))


if __name__=='__main__': main()
