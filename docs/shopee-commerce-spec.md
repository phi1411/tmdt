# Shopee Commerce Clean-Room Specification

> **Evidence boundary.** Public, unauthenticated browser visit to `https://shopee.vn` on 2026-10-15 reached a traffic-verification page for direct homepage/search navigation. Passive requests did include `GET /api/v4/search/search_items?…` returning HTTP 200, plus homepage/account/experiment/subcart traffic; they did **not** show `/api/v4/item/get`, a cart selection endpoint, or a checkout/voucher endpoint. No item/cart/checkout action was exercised; no response body/schema was captured. Consequently, sections below separate NovaMart's verified existing contract from a proposed extension; they do not assert Shopee's internal schema, algorithms, TTL values, endpoint payloads, or voucher policy. No obfuscated/source code was copied.
>
> Browser observations: Playwright `goto` to homepage returned title `Shopee Việt Nam | Mua Sắm Online`, then redirected to `/verify/traffic/error`; search navigation reached the same verification page. A subsequent passive request listing showed `GET /api/v4/search/search_items` returning HTTP 200, alongside `/api/v4/homepage/*`, `/api/v4/account/*`, `/api/v4/experiment/*`, and `/api/v4/web/subcart`. Exact requested target APIs were absent from the observed request list. This bounded attach/session observation is not proof that endpoints do not exist.

## 1. Executive Summary & Architecture Gaps

NovaMart's locked v1 model intentionally has one stock pool and one price per Product; `sizes`/`colors` are descriptive attributes, not SKU-level inventory. Cart lines carry optional `selectedAttributes`, but do not reserve inventory. Checkout revalidates current stock and price, then commits stock decrement, immutable Order snapshots, Order creation, and Cart clearing in one MongoDB transaction. Current pricing has no coupons (`discount=0`); shipping is a configured flat fee. See [database schema](database-schema.md), [business rules](business-rules.md), and [foundation decisions](foundation-decisions.md).

A multi-tier SKU matrix, reservations, and stacked promotions are therefore **proposed extensions only**, not current NovaMart behavior and not verified Shopee implementation facts. They would change stock ownership, cart/checkout consistency, price calculation, order snapshots, validators, indexes, API contracts, and expiry operations. Do not apply the proposed diff without a separately approved phase/ADR and migration plan.

**Evidence-backed gaps against this requested model:**

- Product `price`/`stock` currently live at the Product root; no `tierVariations` or per-model SKU records.
- Cart line identity uses `productId + selectedAttributes`; no exact `modelId` or reservation reference.
- Cart never holds stock; VNPAY order hold exists only after order creation under a fixed payment deadline.
- `orders.discount` is constrained to zero in v1; no voucher breakdown, eligibility decision snapshot, or stacking policy.
- Existing payment expiry is explicit state transition/stock restoration, not TTL deletion. A stock reservation needs the same explicit, idempotent expiry discipline.

## 2. BSON/JSON Schemas (Products, Carts, Orders, Inventory)

The examples are **proposal shapes**, not validator-ready JSON Schema. Use BSON `ObjectId`, `Date`, `long` for money, integer quantities/versions; reject booleans as numeric values. Existing collection and naming conventions remain unless separately approved.

### Product SKU matrix — proposed delta

```json
{
  "variantSchemaVersion": 1,
  "tierVariations": [
    { "tier": 1, "name": "Color", "options": [{ "optionId": "black", "value": "Black" }] },
    { "tier": 2, "name": "Size", "options": [{ "optionId": "m", "value": "M" }] }
  ],
  "models": [
    {
      "modelId": 123456,
      "sku": "SHIRT-BLK-M",
      "optionIds": ["black", "m"],
      "price": { "$numberLong": "250000" },
      "promotionPrice": null,
      "stock": 12,
      "version": 1
    }
  ]
}
```

Proposed invariants: model `optionIds` has exactly one valid option per declared tier; no duplicate option tuple, `modelId`, or SKU within the product; each tuple maps to exactly one model; money is non-negative integer VND and `promotionPrice` is absent/null or `<= price`; stock is a non-negative integer. Whether `modelId` is globally unique, SKU globally unique, options may be unavailable, or price/stock may vary at higher tiers remains a product decision. Root Product price/stock compatibility strategy also remains undecided: remove them, or retain derived display/minimum fields without permitting writes as authority.

### Cart — proposed delta

```json
{
  "items": [
    {
      "lineId": "<sha256>",
      "productId": { "$oid": "..." },
      "modelId": 123456,
      "sku": "SHIRT-BLK-M",
      "quantity": 2,
      "reservationId": { "$oid": "..." }
    }
  ]
}
```

Use a stable line identity based on `productId + modelId` (or a canonical tier-option tuple only if the selected model cannot be resolved yet). Never accept client price, discount, stock, or reservation expiry as authoritative. Existing `selectedAttributes` representation requires a versioned compatibility/migration policy; do not silently reinterpret existing line IDs.

### Inventory reservation — proposed separate collection

```json
{
  "_id": { "$oid": "..." },
  "schemaVersion": 1,
  "reservationKey": "<idempotency key scoped to owner/cart intent>",
  "userId": { "$oid": "..." },
  "cartId": { "$oid": "..." },
  "cartVersion": 4,
  "lines": [
    { "productId": { "$oid": "..." }, "modelId": 123456, "quantity": 2 }
  ],
  "status": "ACTIVE",
  "expiresAt": { "$date": "<UTC deadline>" },
  "version": 1,
  "createdAt": { "$date": "<UTC>" },
  "updatedAt": { "$date": "<UTC>" }
}
```

This is a candidate design, not a committed collection. To make `available stock = physical stock - active unexpired reservations` correct under concurrency, either atomically decrement `availableStock` at reservation creation and restore exactly once on release, or prove an equivalent guarded accounting model; a plain read/count of reservations is insufficient under races. Candidate compound indexes: unique idempotency key in its declared scope; `{status, expiresAt}` for expiry polling; line inventory lookup only if the chosen accounting model needs it. Do not add a TTL index as the business expiry mechanism: TTL deletion is asynchronous and cannot atomically restore stock or update Cart/Order.

### Order — proposed immutable snapshots

```json
{
  "items": [
    {
      "productId": { "$oid": "..." },
      "modelId": 123456,
      "sku": "SHIRT-BLK-M",
      "selectedOptions": [{ "tier": 1, "optionId": "black", "value": "Black" }, { "tier": 2, "optionId": "m", "value": "M" }],
      "priceAtPurchase": { "$numberLong": "250000" },
      "quantity": 2,
      "lineTotal": { "$numberLong": "500000" }
    }
  ],
  "pricingSnapshot": {
    "currency": "VND",
    "subtotal": { "$numberLong": "500000" },
    "discountTotal": { "$numberLong": "50000" },
    "shippingFee": { "$numberLong": "0" },
    "total": { "$numberLong": "450000" },
    "discounts": [
      { "voucherId": "<opaque id>", "scope": "PLATFORM", "amount": { "$numberLong": "30000" } },
      { "voucherId": "<opaque id>", "scope": "SHOP", "amount": { "$numberLong": "20000" } }
    ]
  }
}
```

Keep the current Order snapshot immutable principle. Store applied promotion identities, scope, computed amount, and relevant rule/version snapshot needed for audit; do not depend on live voucher records to explain a past order. Exact PII/claim data retention and voucher terms should be minimized and decided before implementation. The sample IDs/amounts above are illustrative, not observed platform data.

## 3. Stock Reservation & Concurrency Invariants

### Proposed state machine

`ACTIVE -> CONSUMED` on successful order commit; `ACTIVE -> RELEASED` on explicit cancellation; `ACTIVE -> EXPIRED` on deadline. Terminal transitions are idempotent. Only one guarded transition may release/consume a reservation. Cancellation/expiry must not restore the same quantity twice. The Order and reservation must agree on ownership, line model IDs, quantities, and reservation status.

### Proposed transactional rules

1. Resolve every requested `modelId` to a current model and validate that it belongs to the Product; validate option tuple, purchasability, integer quantity and per-model bounds.
2. Reserve with an atomic conditional inventory update and expected model/Product version, or an equivalently serializable transaction. Reject if available stock is insufficient. Do not count concurrent reservations using an unguarded aggregate-then-insert sequence.
3. Make reservation creation idempotent for the same owner and canonical cart intent. Same key + same intent returns the existing active reservation; same key + different intent conflicts.
4. Checkout consumes the active reservation and writes Order snapshots, voucher usage/claims, and Cart state in one transaction. Validate `expiresAt > now` at the transaction's chosen authoritative time; if expired, reject and release through the expiry path.
5. Explicit expiry worker scans `{status: ACTIVE, expiresAt <= now}` and transactionally transitions/replenishes inventory with a status predicate. Worker retries must be safe. Monitor oldest overdue active reservation, release failures, reservation contention, and inventory invariant drift.
6. Do not hold inventory inside a transaction while waiting on the user or an external payment provider. Define the reservation lease separately from payment attempts, and document what a paid-late callback does after reservation release; no such policy is currently established for this extension.

TTL duration, renewal rules, max quantity, reservation scope (cart/session/user), multi-device behavior, and the behavior for payment-in-flight are **unresolved**. NovaMart's existing 15-minute VNPAY order deadline and 30-second worker cadence are current payment policy, not evidence or automatic defaults for a new pre-checkout reservation.

## 4. Voucher Stacking Rules & Calculations

No Shopee voucher rule was observable in this session. Do not infer eligibility, stacking order, caps, or precedence from endpoint names. The following is a minimal **proposed contract requiring product decisions**.

### Inputs and validation

Server resolves submitted voucher IDs and validates active window, owner/scope, shop/product/category applicability, minimum spend, per-user/global usage limits, and compatibility. Client-provided discount values are always ignored. Reserve/consume voucher capacity atomically with checkout to prevent over-redemption; failed checkout releases any claim in the same rollback path.

### Explicit stacking policy required

Potential buckets: platform voucher, shop voucher, shipping subsidy. Decide whether at most one voucher is accepted per bucket, whether multiple shops create per-shop voucher groups, whether shipping subsidy competes with other discounts, and whether the order of application changes eligibility. None is specified by current NovaMart business rules or evidenced from Shopee here.

For a chosen policy, define all arithmetic in integer VND. One safe generic cap is:

- `discountAmount = min(calculatedDiscount, configuredVoucherCap, eligibleBase)`
- `eligibleBase >= 0`
- `shippingFeeAfterSubsidy = max(0, shippingFeeBeforeSubsidy - shippingSubsidy)`
- `total = subtotal - merchandiseDiscounts + shippingFeeAfterSubsidy`

The ordering of `eligibleBase` and whether one voucher changes the next voucher's base must be a deliberate rule; do not assume commutativity. Enforce `0 <= total`, configured Order maximum, and no floating-point arithmetic. Persist each applied discount line and the resulting totals in the immutable Order pricing snapshot. Current v1 remains `discount=0`, flat configured shipping, no vouchers.

## 5. Proposed Diff cho NovaMart Validators (products.json, carts.json, orders.json)

This is a change outline, **not an executable validator patch**. Canonical validators are `database/validators/products.json`, `carts.json`, `orders.json`; update schema versioning, samples, backend schemas/services, API contracts, index manifest, migrations, and tests together only after approval.

- **`products.json`:** add bounded `tierVariations[]` and `models[]`; each model includes `modelId`, `sku`, complete `optionIds`, integer-long `price`, optional nullable/omitted `promotionPrice`, non-negative integer `stock`, and `version`. Validator can enforce local types/bounds; cross-array option membership, unique tuples, price ordering, and SKU/model uniqueness need application invariants and appropriate indexes. Decide whether root `price`/`stock` are removed or derived.
- **`carts.json`:** add `modelId` to each item and optional `reservationId` only if reservation lifecycle is approved. Require exactly one authoritative variant selector; reject client money/stock fields. Existing cart documents and `lineId` hashing need a versioned migration or read-compatibility plan.
- **`orders.json`:** extend each immutable item snapshot with `modelId`, selected option snapshots, and model SKU; extend totals with bounded discount lines and per-scope totals. Preserve arithmetic, VND-long, order-state, idempotency, and immutable-snapshot invariants. Voucher usage claim needs a concurrency-safe owner outside the validator (transaction/service + unique/index constraints); JSON Schema cannot enforce aggregate spending or stacking eligibility.
- **Reservation collection:** outside the three requested validators, a new collection needs its own validator, indexes, migration/backfill policy, and explicit expiry worker; do not model TTL deletion as stock restoration.
- **Compatibility gate:** no validator/data change was made. NovaMart's locked v1 has no variant stock, pre-checkout reservations, or voucher stacking; current features and existing Orders remain governed by the linked canonical docs. Any adoption needs an approved schema/ADR decision, exact historical-data impact assessment, migration/rollback plan, and transaction tests against replica set MongoDB.

### Unresolved decisions

1. Variant SKU identity and uniqueness scope; compatibility strategy for root Product `price`/`stock`.
2. Reservation lease duration, renewal, scope, payment interaction, and operational worker ownership.
3. Voucher eligibility, stacking order, per-bucket multiplicity, caps/rounding, usage claim/release semantics, and shop grouping.
4. Whether this specification is research-only or a future NovaMart phase deliverable; no platform API evidence currently resolves these questions.
