"""User-authorized retained COD coupon examples; API writes, no fake payment."""
import hashlib
import json
import secrets
import urllib.request
from pathlib import Path
from urllib.parse import urlencode
from bson import ObjectId, json_util
from bson.int64 import Int64
from pymongo import MongoClient

ROOT = Path(__file__).resolve().parents[2]
PRIVATE = ROOT / '.local/coupon-demo'
PRIVATE.mkdir(parents=True, exist_ok=True)
JOURNAL = PRIVATE / 'journal.json'
BASE = 'https://novamart-api.onrender.com/api/v1'


def http(method, path, payload=None, token=None, key=None):
    headers = {'Content-Type': 'application/json'}
    if token: headers['Authorization'] = 'Bearer ' + token
    if key: headers['Idempotency-Key'] = key
    req = urllib.request.Request(BASE + path, method=method, headers=headers,
                                 data=json.dumps(payload).encode() if payload is not None else None)
    with urllib.request.urlopen(req, timeout=40) as response:
        return json.load(response)['data'] if response.status != 204 else None


def digest(value):
    return hashlib.sha256(json_util.dumps(value, json_options=json_util.CANONICAL_JSON_OPTIONS,
                                         sort_keys=True).encode()).hexdigest()


def main():
    cfg = json.loads((ROOT / '.local/render-deployment/backend-config.json').read_text())
    assert 'cluster0.asxeso0.mongodb.net' in cfg['MONGODB_URI']
    client = MongoClient(cfg['MONGODB_URI'], tz_aware=True, serverSelectionTimeoutMS=15000)
    db = client.novamart_demo
    journal = json.loads(JOURNAL.read_text()) if JOURNAL.exists() else {
        'run': secrets.token_hex(6), 'password': secrets.token_urlsafe(24), 'orders': {}}
    journal.setdefault('email', 'demo-coupons-' + journal['run'] + '@example.test')
    def save(): JOURNAL.write_text(json.dumps(journal, ensure_ascii=False, indent=2), encoding='utf-8')
    save()
    if 'beforeOrdersHash' not in journal:
        before_orders = list(db.orders.find().sort('_id', 1))
        a = db.products.find_one({'sku': 'DEFENSE-FINAL-SKU', 'status': 'ACTIVE'})
        b = db.products.find_one({'sku': 'DEFENSE-FINAL-SNAPSHOT', 'status': 'ACTIVE'})
        assert a and b, 'Retained defense products required; do not silently replace live data'
        journal.update(productA=str(a['_id']), productB=str(b['_id']),
                       beforeOrderIds=[str(o['_id']) for o in before_orders], beforeOrdersHash=digest(before_orders),
                       stocks={str(p['_id']): {'stock':p['stock'],'skus':{s['skuId']:s['stock'] for s in p.get('skus',[])}}
                               for p in (a,b)})
        (PRIVATE / 'before.ejson').write_text(json_util.dumps({'products':[a,b],'orders':before_orders},
            json_options=json_util.CANONICAL_JSON_OPTIONS), encoding='utf-8')
        save()
    if 'userId' not in journal:
        existing = db.users.find_one({'email':journal['email']})
        if existing:
            journal['userId']=str(existing['_id'])
        else:
            journal['userId']=http('POST','/auth/register',{'name':'Khách demo mã giảm giá',
                'email':journal['email'],'password':journal['password'],'phone':'0901234567'})['user']['id']
        save()
    token=http('POST','/auth/login',{'email':journal['email'],'password':journal['password']})['accessToken']
    profile=http('GET','/users/me',token=token)
    if 'addressId' not in journal:
        if profile['addresses']:
            journal['addressId']=profile['addresses'][0]['id']
        else:
            journal['addressId']=http('POST','/users/me/addresses',{'expectedVersion':profile['version'],
                'receiverName':'Khách demo','phone':'0901234567','addressLine':'Địa chỉ minh họa báo cáo NoSQL',
                'province':'Hồ Chí Minh'},token)['address']['id']
        save()

    def fill_cart(code):
        cart=http('GET','/cart',token=token)
        http('DELETE','/cart',{'cartVersion':cart['version']},token)
        product=http('GET','/products/ao-demo-sku-m-xl')
        choice='XL' if code=='DEMO15' else 'M'
        sku=next(s for s in product['skus'] if product['tierVariations'][0]['options'][s['tierIndex'][0]]==choice)
        qty=5 if code=='NOVA25' else 3 if code=='DEMO15' else 1
        cart=http('GET','/cart',token=token)
        cart=http('POST','/cart/items',{'productId':journal['productA'],'quantity':qty,'cartVersion':cart['version'],
            'selectedAttributes':{product['tierVariations'][0]['name']:choice,'skuId':sku['skuId']}},token)
        cart=http('POST','/cart/items',{'productId':journal['productB'],'quantity':1,'selectedAttributes':{},
                                      'cartVersion':cart['version']},token)
        return http('PATCH','/cart/coupon',{'code':code,'cartVersion':cart['version']},token)

    policies={'DEMO10':(10,20000),'DEMO15':(15,40000),'NOVA25':(25,50000)}
    for code,(percent,cap) in policies.items():
        item=journal['orders'].setdefault(code,{})
        if 'intent' not in item:
            fill_cart(code)
            quote=http('GET','/checkout/quote?'+urlencode({'addressId':journal['addressId'],'paymentMethod':'COD'}),token=token)
            assert quote['coupon']['code']==code and quote['discount']==min(quote['subtotal']*percent//100,cap)
            online=http('GET','/checkout/quote?'+urlencode({'addressId':journal['addressId'],'paymentMethod':'VNPAY'}),token=token)
            assert online['total']==quote['total'], 'COD/VNPAY net amount differs'
            item['intent']={'cartVersion':quote['cartVersion'],'addressId':journal['addressId'],
                            'paymentMethod':'COD','quoteToken':quote['quoteToken']}
            item['key']='coupon-demo-'+journal['run']+'-'+code
            save()
        order=http('POST','/orders',item['intent'],token,item['key'])['order']
        item['id']=order['id'];save()
        if order['orderStatus']!='CANCELLED':
            order=http('POST','/orders/'+order['id']+'/cancel',{'expectedVersion':order['version']},token)
        assert order['orderStatus']=='CANCELLED' and order['coupon']['code']==code
        item['cancelled']=True;save()
    cart=fill_cart('NOVA25')
    report={'status':'PASS','purpose':'Intentionally retained coupon demo, user-authorized',
            'userId':journal['userId'],'orders':[],'cart':{'couponCode':'NOVA25','discount':cart['discount'],
                                                       'subtotal':cart['subtotal'],'version':cart['version']}}
    for code,item in journal['orders'].items():
        order=db.orders.find_one({'_id':ObjectId(item['id']),'userId':ObjectId(journal['userId'])})
        assert order['orderStatus']=='CANCELLED' and order['paymentStatus']=='UNPAID'
        assert type(order['discount']) is Int64 and sum(i['discountAllocated'] for i in order['items'])==order['discount']
        assert order['total']==order['subtotal']-order['discount']+order['shippingFee']
        report['orders'].append({k:int(order[k]) if isinstance(order[k],Int64) else order[k]
            for k in ('orderCode','subtotal','discount','shippingFee','total','orderStatus','paymentStatus')}
            | {'id':str(order['_id']),'code':code})
    for pid,stock in journal['stocks'].items():
        product=db.products.find_one({'_id':ObjectId(pid)})
        assert product['stock']==stock['stock'] and {s['skuId']:s['stock'] for s in product.get('skus',[])}==stock['skus']
    old=list(db.orders.find({'_id':{'$in':[ObjectId(i) for i in journal['beforeOrderIds']]}}).sort('_id',1))
    report['oldOrdersUnchanged']=digest(old)==journal['beforeOrdersHash']
    assert report['oldOrdersUnchanged']
    report['stockRestored']=True
    report['paymentAttemptsForDemo']=db.payment_attempts.count_documents({'userId':ObjectId(journal['userId'])})
    assert report['paymentAttemptsForDemo']==0
    report['counts']={n:db[n].count_documents({}) for n in db.list_collection_names()}
    (ROOT/'backend/evidence/coupon-public-demo.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    client.close()
    print(json.dumps({'status':'PASS','orders':report['orders'],'cart':report['cart']},ensure_ascii=True))


if __name__=='__main__':
    main()
