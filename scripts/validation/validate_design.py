"""Static phase-02 design checks; never connects to MongoDB or runs business APIs."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import unicodedata
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from jsonschema import Draft4Validator, ValidationError, validators

ROOT = Path(__file__).resolve().parents[2]
COLLECTIONS = ("users", "categories", "products", "carts", "orders", "payment_attempts", "reviews")


class ObjectId(str):
    """Type marker for static EJSON checks, not a PyMongo ObjectId implementation."""


class Int32(int):
    pass


class Int64(int):
    pass


def decode(value):
    if isinstance(value, list):
        return [decode(item) for item in value]
    if not isinstance(value, dict):
        return value
    if set(value) == {"$oid"}:
        assert re.fullmatch(r"[a-f0-9]{24}", value["$oid"]), "Bad ObjectId"
        return ObjectId(value["$oid"])
    if set(value) == {"$numberInt"}:
        number = int(value["$numberInt"])
        assert -(2**31) <= number < 2**31, "Int32 overflow"
        return Int32(number)
    if set(value) == {"$numberLong"}:
        number = int(value["$numberLong"])
        assert -(2**63) <= number < 2**63, "Int64 overflow"
        return Int64(number)
    if set(value) == {"$date"}:
        result = datetime.fromisoformat(value["$date"].replace("Z", "+00:00"))
        assert result.utcoffset().total_seconds() == 0, "Examples must use UTC"
        return result
    return {key: decode(item) for key, item in value.items()}


def bson_type(validator, expected, instance, schema):
    types = expected if isinstance(expected, list) else [expected]
    checks = {
        "object": isinstance(instance, dict),
        "array": isinstance(instance, list),
        "string": type(instance) is str,
        "objectId": type(instance) is ObjectId,
        "date": isinstance(instance, datetime),
        "int": type(instance) is Int32,
        "long": type(instance) is Int64,
        "double": type(instance) is float,
        "bool": type(instance) is bool,
        "null": instance is None,
    }
    if not any(checks.get(name, False) for name in types):
        yield ValidationError(f"Expected BSON {types}, found {type(instance).__name__}")


BSONValidator = validators.extend(Draft4Validator, {"bsonType": bson_type})
ALLOWED = {
    "bsonType", "type", "required", "properties", "additionalProperties", "patternProperties",
    "items", "minItems", "maxItems", "uniqueItems", "minLength", "maxLength", "pattern",
    "minProperties", "maxProperties", "minimum", "maximum", "enum", "oneOf", "anyOf",
    "allOf", "not", "description", "title",
}


def audit_schema(schema):
    assert set(schema) <= ALLOWED, f"Unsupported Mongo schema keywords: {set(schema) - ALLOWED}"
    for keyword in ("properties", "patternProperties"):
        for child in schema.get(keyword, {}).values():
            audit_schema(child)
    for keyword in ("items", "not", "additionalProperties"):
        child = schema.get(keyword)
        if isinstance(child, dict):
            audit_schema(child)
    for keyword in ("oneOf", "anyOf", "allOf"):
        for child in schema.get(keyword, []):
            audit_schema(child)


def normalize(value):
    decomposed = unicodedata.normalize("NFKD", value.casefold().replace("đ", "d"))
    return " ".join("".join(c for c in decomposed if not unicodedata.combining(c)).split())


def canonical_hash(value):
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def invariants(data):
    users = {row["_id"]: row for row in data["users"]}
    categories = {row["_id"]: row for row in data["categories"]}
    products = {row["_id"]: row for row in data["products"]}
    orders = {row["_id"]: row for row in data["orders"]}
    for rows in data.values():
        for row in rows:
            assert row["createdAt"] <= row["updatedAt"], "Timestamp order"
    for user in users.values():
        address_ids = [a["_id"] for a in user["addresses"]]
        assert len(address_ids) == len(set(address_ids)), "Duplicate address IDs"
        assert user["defaultAddressId"] is None or user["defaultAddressId"] in address_ids
        assert user["email"] == user["email"].strip().lower(), "Email normalization"
    for product in products.values():
        category = categories[product["categoryId"]]
        assert product["productType"] == category["productType"], "Category/type mismatch"
        assert product["nameNormalized"] == normalize(product["name"]), "Name normalization"
        assert product["brandNormalized"] == normalize(product["brand"]), "Brand normalization"
    for cart in data["carts"]:
        assert cart["userId"] in users
        assert len({item["lineId"] for item in cart["items"]}) == len(cart["items"])
        quantities = Counter()
        for item in cart["items"]:
            assert item["productId"] in products
            assert item["lineId"] == canonical_hash({"productId": str(item["productId"]), "selectedAttributes": item["selectedAttributes"]})
            quantities[item["productId"]] += item["quantity"]
        for product_id, quantity in quantities.items():
            assert quantity <= products[product_id]["stock"], "Cart shared-stock limit"
    for order in orders.values():
        assert order["userId"] in users
        for item in order["items"]:
            assert item["productId"] in products and item["categoryId"] in categories
            assert item["lineTotal"] == item["priceAtPurchase"] * item["quantity"], "Line arithmetic"
            if item["productType"] == "FASHION":
                options = item["attributesSnapshot"]
                for choice, field in (("size", "sizes"), ("color", "colors")):
                    if options.get(field):
                        assert item["selectedAttributes"].get(choice) in options[field], "Historical selection"
        assert order["subtotal"] == sum(item["lineTotal"] for item in order["items"]), "Subtotal arithmetic"
        assert order["total"] == order["subtotal"] + order["shippingFee"] - order["discount"], "Total arithmetic"
        for field in ("paidAt", "completedAt", "cancelledAt", "expiredAt", "stockReleasedAt"):
            if field in order:
                assert order["createdAt"] <= order[field] <= order["updatedAt"], f"Chronology {field}"
        if "completedAt" in order:
            assert order["paidAt"] <= order["completedAt"]
    for attempt in data["payment_attempts"]:
        order = orders[attempt["orderId"]]
        request = attempt["paymentRequest"]
        assert order["paymentMethod"] == "VNPAY" and attempt["userId"] == order["userId"]
        assert attempt["amount"] == order["total"] == request["amountScaled"] // 100
        assert request["amountScaled"] == attempt["amount"] * 100
        assert request["txnRef"] == attempt["txnRef"]
        assert attempt["expiresAt"] == order["paymentExpiresAt"] == request["expiresAt"]
        assert request["createdAt"] < request["expiresAt"]
        if attempt["status"] == "SUCCEEDED":
            assert order["paymentStatus"] == "PAID"
        if attempt["status"] == "REVIEW_REQUIRED":
            assert order["paymentReviewRequired"]


def schema_paths(schema, prefix=""):
    result = set()
    for name, value in schema.get("properties", {}).items():
        path = f"{prefix}.{name}" if prefix else name
        result.add(path)
        result.update(schema_paths(value.get("items", value), path))
    return result


def references(value):
    if isinstance(value, str) and value.startswith("$"):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from references(child)
    elif isinstance(value, list):
        for child in value:
            yield from references(child)


def validate_pipelines(schemas):
    checked = 0
    for path in sorted((ROOT / "database/aggregations").glob("*.json")):
        pipeline = decode(json.loads(path.read_text(encoding="utf-8")))
        collection = "users" if path.stem == "customer-count" else "orders"
        available = schema_paths(schemas[collection])
        stages = []
        for stage in pipeline:
            assert len(stage) == 1
            operator, expression = next(iter(stage.items()))
            assert operator in {"$match", "$sort", "$group", "$unwind", "$limit", "$project", "$count"}
            stages.append(operator)
            if operator in {"$match", "$sort"}:
                assert set(expression) <= available, f"Unknown fields in {path.name}"
            for reference in references(expression):
                if reference == "$$item.quantity":
                    assert "items.quantity" in available
                elif reference.startswith("$$"):
                    raise AssertionError(f"Unexpected variable {reference}")
                else:
                    assert reference[1:] in available, f"Bad reference {reference} in {path.name}"
            if operator == "$group":
                available = set(expression)
            elif operator == "$project":
                available = {key for key, value in expression.items() if value != 0}
            elif operator == "$count":
                available = {expression}
        if path.stem in {"top-products", "category-revenue", "revenue-day", "revenue-month", "sales-summary"}:
            match = pipeline[0]["$match"]
            assert match["orderStatus"] == "COMPLETED" and match["paymentStatus"] == "PAID"
            assert set(match["completedAt"]) == {"$gte", "$lt"}
        if path.stem == "top-products":
            assert {"$match", "$unwind", "$group", "$sort", "$limit"} <= set(stages)
            assert pipeline[-2] == {"$limit": 5}
            assert pipeline[3]["$group"]["revenue"] == {"$sum": "$items.lineTotal"}
        if path.stem.startswith("revenue-"):
            assert {"$match", "$group", "$sort"} <= set(stages)
            group = pipeline[1]["$group"]
            assert group["revenue"] == {"$sum": {"$subtract": ["$subtotal", "$discount"]}}
            assert group["_id"]["$dateTrunc"]["timezone"] == "Asia/Ho_Chi_Minh"
        checked += 1
    assert checked == 8
    return checked


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-report", action="store_true")
    args = parser.parse_args()
    schemas, data = {}, {}
    for collection in COLLECTIONS:
        raw = json.loads((ROOT / f"database/validators/{collection}.json").read_text(encoding="utf-8"))
        assert set(raw) == {"$jsonSchema"}
        schemas[collection] = raw["$jsonSchema"]
        audit_schema(schemas[collection])
        Draft4Validator.check_schema(schemas[collection])
        data[collection] = decode(json.loads((ROOT / f"database/samples/{collection}.json").read_text(encoding="utf-8")))
        for sample in data[collection]:
            BSONValidator(schemas[collection]).validate(sample)
    invariants(data)
    for review in data['reviews']:
        order = next(o for o in data['orders'] if o['_id'] == review['orderId'])
        assert order['userId'] == review['userId'] and order['orderStatus'] == 'COMPLETED' and order['paymentStatus'] == 'PAID'
        assert any(item['productId'] == review['productId'] for item in order['items'])
    failures_checked = 0

    def reject(collection, mutate):
        nonlocal failures_checked
        sample = copy.deepcopy(data[collection][0])
        mutate(sample)
        assert list(BSONValidator(schemas[collection]).iter_errors(sample)), f"Invalid case accepted: {collection}"
        failures_checked += 1

    reject("reviews", lambda x: x.update(rating=Int32(6)))
    reject("users", lambda x: x.update(role="SELLER"))
    reject("users", lambda x: x.update(passwordHash="plaintext"))
    reject("categories", lambda x: x.update(parentId=ObjectId("0" * 24)))
    reject("products", lambda x: x.update(price=10_000_000.0))
    reject("products", lambda x: x.update(stock=True))
    reject("products", lambda x: x.update(productType="OTHER"))
    reject("products", lambda x: x["attributes"].update(ram=Int32(8)))
    reject("products", lambda x: x["attributes"].update({"$where": "bad"}))
    reject("products", lambda x: x.update(images=["javascript:alert(1)"]))
    reject("products", lambda x: x.update(images=["/images/relative.webp"]))
    reject("carts", lambda x: x["items"][0].update(quantity=Int32(0)))
    reject("carts", lambda x: x["items"][0].update(price=Int64(1)))
    reject("orders", lambda x: x["items"][0].pop("priceAtPurchase"))
    reject("orders", lambda x: x.pop("completedAt"))
    reject("orders", lambda x: x.update(paymentStatus="UNPAID"))
    reject("payment_attempts", lambda x: x.update(provider="REAL_PAYMENT"))
    reject("payment_attempts", lambda x: x.update(providerTransactionNo="0"))
    reject("payment_attempts", lambda x: x.update(hashSecret="not-allowed"))
    negative = copy.deepcopy(data["orders"][1])
    negative["total"] = Int64(10_000_000_000)
    assert list(BSONValidator(schemas["orders"]).iter_errors(negative)), "VNPAY amount cap"
    failures_checked += 1
    for collection, field, value in (("orders", "subtotal", Int64(1)), ("products", "nameNormalized", "wrong")):
        bad = copy.deepcopy(data)
        bad[collection][0][field] = value
        try:
            invariants(bad)
        except AssertionError:
            failures_checked += 1
        else:
            raise AssertionError(f"Bad cross-field invariant accepted: {field}")
    extension = copy.deepcopy(data["products"][0])
    extension["attributes"]["connectivity"] = {"wifi": True, "bands": ["2.4GHz", "5GHz"]}
    BSONValidator(schemas["products"]).validate(extension)
    positive_variants = 0
    for method, status, payment in [
        ("COD", "PENDING", "UNPAID"), ("COD", "CONFIRMED", "UNPAID"),
        ("COD", "SHIPPING", "UNPAID"), ("VNPAY", "PENDING", "PENDING"),
        ("VNPAY", "PENDING", "FAILED"), ("VNPAY", "SHIPPING", "PAID"),
    ]:
        sample = copy.deepcopy(data["orders"][0 if method == "COD" else 1])
        sample.update(orderStatus=status, paymentStatus=payment)
        sample.pop("completedAt", None)
        if payment != "PAID":
            sample.pop("paidAt", None)
        BSONValidator(schemas["orders"]).validate(sample)
        positive_variants += 1
    pending = copy.deepcopy(data["payment_attempts"][0])
    pending["status"] = "PENDING"
    for field in ("providerTransactionNo", "responseCode", "transactionStatus", "bankCode", "verifiedAt", "providerPaidAt", "callbackFingerprint"):
        pending.pop(field, None)
    BSONValidator(schemas["payment_attempts"]).validate(pending)
    positive_variants += 1
    failed = copy.deepcopy(data["payment_attempts"][0])
    failed.update(status="FAILED", responseCode="24", transactionStatus="02")
    failed.pop("providerTransactionNo")
    failed.pop("providerPaidAt")
    BSONValidator(schemas["payment_attempts"]).validate(failed)
    positive_variants += 1
    assert {p["productType"] for p in data["products"]} == {"ELECTRONICS", "FASHION", "HOME_APPLIANCE"}
    assert normalize("  ĐIỆN  thoại Áo ") == "dien thoai ao"
    manifest = json.loads((ROOT / "database/indexes/candidate-indexes.json").read_text(encoding="utf-8"))
    names = set()
    for entry in manifest["indexes"]:
        marker = (entry["collection"], entry["name"])
        assert marker not in names
        names.add(marker)
        available = schema_paths(schemas[entry["collection"]])
        assert set(entry["keys"]) <= available
        assert entry["queryPattern"] and entry["fieldOrderReason"]
        for field in entry["equalityFields"] + entry["rangeFields"] + list(entry["sortFields"]):
            assert field in available
        partial = entry["options"].get("partialFilterExpression", {})
        assert set(partial) <= available
        if entry["options"].get("unique"):
            seen = set()
            for row in data[entry["collection"]]:
                if partial.get("status") and row["status"] != partial["status"]:
                    continue
                if "providerTransactionNo" in partial and "providerTransactionNo" not in row:
                    continue
                key = tuple(row[field] for field in entry["keys"])
                assert key not in seen, f"Duplicate unique example key: {marker}"
                seen.add(key)
    pipelines = validate_pipelines(schemas)
    qualified = [o for o in data["orders"] if o["orderStatus"] == "COMPLETED" and o["paymentStatus"] == "PAID"]
    revenue = sum(o["subtotal"] - o["discount"] for o in qualified)
    units = sum(item["quantity"] for o in qualified for item in o["items"])
    assert (revenue, units) == (21_900_000, 5)
    assert sum(o["total"] for o in qualified) - revenue == 60_000, "Shipping excluded"
    report = {
        "status": "STATIC_PASS",
        "validators": len(schemas), "examples": {k: len(v) for k, v in data.items()},
        "negativeCasesRejected": failures_checked, "polymorphicExtensionAccepted": True,
        "additionalLegalStatusVariants": positive_variants,
        "candidateIndexes": len(names), "aggregationDesignsChecked": pipelines,
        "independentFixtureExpectations": {"revenueVnd": revenue, "units": units, "qualifiedOrders": len(qualified)},
        "mongodbConnected": False, "mongodbValidatorsApplied": False, "mongodbPipelinesExecuted": False,
        "benchmarkRun": False, "businessFeaturesImplemented": False,
    }
    if args.write_report:
        (ROOT / "docs/phase-02-validation.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
