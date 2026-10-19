import { test } from 'node:test';
import assert from 'node:assert/strict';
import { paymentViewStatus } from '../src/utils/paymentStatus.ts';

const result = { result:'PENDING', verified:true, confirmed:false, authoritative:false, orderId:'order-a' };
const order = { id:'order-a', orderStatus:'PENDING', paymentStatus:'PENDING', paymentReviewRequired:false };

test('polling authoritative PAID replaces the earlier pending return view', () => {
  assert.equal(paymentViewStatus(result,{...order,paymentStatus:'PAID',orderStatus:'CONFIRMED'}).status,'SUCCESS');
});
test('expired or cancelled/failed order replaces stale pending view', () => {
  for (const state of ['EXPIRED','CANCELLED']) {
    assert.equal(paymentViewStatus(result,{...order,orderStatus:state,paymentStatus:'FAILED'}).status,'FAILED');
  }
});
test('late payment review appears after polling even if original return had no review flag', () => {
  assert.deepEqual(paymentViewStatus(result,{...order,paymentStatus:'REVIEW_REQUIRED',paymentReviewRequired:true}),{status:'PENDING',needsReview:true});
});
test('second payment keeps PAID and displays the review warning', () => {
  assert.deepEqual(paymentViewStatus(result,{...order,paymentStatus:'PAID',paymentReviewRequired:true}),{status:'SUCCESS',needsReview:true});
});
test('invalid signature cannot be turned into a success view by a stale order', () => {
  assert.equal(paymentViewStatus({...result,verified:false,result:'INVALID_SIGNATURE'},{...order,paymentStatus:'PAID'}).status,'INVALID_SIGNATURE');
});
test('order fetched for a different return URL is not used', () => {
  assert.equal(paymentViewStatus(result,{...order,id:'order-b',paymentStatus:'PAID'}).status,'PENDING');
});
