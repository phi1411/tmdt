// Generated from canonical artifacts. MongoDB aggregation outputs are verified via PyMongo.
// Optional mongosh/Compass shell demo; shell UI rehearsal is deferred.
const demoDB = db.getSiblingDB("ecommerce_dev");
printjson(demoDB.products.countDocuments({}));
printjson(demoDB.orders.countDocuments({}));
printjson(demoDB.products.find({sku: {$in: ["DEMO-ELE-001", "DEMO-FAS-001", "DEMO-HOM-001"]}}).toArray());
printjson(demoDB.orders.findOne({orderCode: "DEMO-2026-0001"}));
// revenue-day: completedAt revenue cohort; createdAt for order counts.
printjson(demoDB.orders.aggregate([
{"$match": {"orderStatus": "COMPLETED", "paymentStatus": "PAID", "completedAt": {"$gte": ISODate("2026-07-03T00:00:00Z"), "$lt": ISODate("2026-10-01T00:00:00Z")}}},
{"$group": {"_id": {"$dateTrunc": {"date": "$completedAt", "unit": "day", "timezone": "Asia/Ho_Chi_Minh"}}, "revenue": {"$sum": {"$subtract": [
"$subtotal",
"$discount"
]}}, "orders": {"$sum": 1}}},
{"$sort": {"_id": 1}}
]).toArray());
// revenue-month: completedAt revenue cohort; createdAt for order counts.
printjson(demoDB.orders.aggregate([
{"$match": {"orderStatus": "COMPLETED", "paymentStatus": "PAID", "completedAt": {"$gte": ISODate("2026-07-03T00:00:00Z"), "$lt": ISODate("2026-10-01T00:00:00Z")}}},
{"$group": {"_id": {"$dateTrunc": {"date": "$completedAt", "unit": "month", "timezone": "Asia/Ho_Chi_Minh"}}, "revenue": {"$sum": {"$subtract": [
"$subtotal",
"$discount"
]}}, "orders": {"$sum": 1}}},
{"$sort": {"_id": 1}}
]).toArray());
// top-products: completedAt revenue cohort; createdAt for order counts.
printjson(demoDB.orders.aggregate([
{"$match": {"orderStatus": "COMPLETED", "paymentStatus": "PAID", "completedAt": {"$gte": ISODate("2026-07-03T00:00:00Z"), "$lt": ISODate("2026-10-01T00:00:00Z")}}},
{"$sort": {"completedAt": -1, "_id": -1}},
{"$unwind": "$items"},
{"$group": {"_id": "$items.productId", "productName": {"$first": "$items.productName"}, "quantity": {"$sum": "$items.quantity"}, "revenue": {"$sum": "$items.lineTotal"}}},
{"$sort": {"quantity": -1, "revenue": -1, "_id": 1}},
{"$limit": 5},
{"$project": {"_id": 0, "productId": "$_id", "productName": 1, "quantity": 1, "revenue": 1}}
]).toArray());
// category-revenue: completedAt revenue cohort; createdAt for order counts.
printjson(demoDB.orders.aggregate([
{"$match": {"orderStatus": "COMPLETED", "paymentStatus": "PAID", "completedAt": {"$gte": ISODate("2026-07-03T00:00:00Z"), "$lt": ISODate("2026-10-01T00:00:00Z")}}},
{"$sort": {"completedAt": -1, "_id": -1}},
{"$unwind": "$items"},
{"$group": {"_id": "$items.categoryId", "categoryName": {"$first": "$items.categoryName"}, "revenue": {"$sum": "$items.lineTotal"}}},
{"$sort": {"revenue": -1, "_id": 1}},
{"$project": {"_id": 0, "categoryId": "$_id", "categoryName": 1, "revenue": 1}}
]).toArray());
// sales-summary: completedAt revenue cohort; createdAt for order counts.
printjson(demoDB.orders.aggregate([
{"$match": {"orderStatus": "COMPLETED", "paymentStatus": "PAID", "completedAt": {"$gte": ISODate("2026-07-03T00:00:00Z"), "$lt": ISODate("2026-10-01T00:00:00Z")}}},
{"$group": {"_id": null, "totalRevenue": {"$sum": {"$subtract": [
"$subtotal",
"$discount"
]}}, "qualifiedOrders": {"$sum": 1}, "totalProductsSold": {"$sum": {"$sum": {"$map": {"input": "$items", "as": "item", "in": "$$item.quantity"}}}}}},
{"$project": {"_id": 0, "totalRevenue": 1, "qualifiedOrders": 1, "totalProductsSold": 1}}
]).toArray());
// order-count: completedAt revenue cohort; createdAt for order counts.
printjson(demoDB.orders.aggregate([
{"$match": {"createdAt": {"$gte": ISODate("2026-07-03T00:00:00Z"), "$lt": ISODate("2026-10-01T00:00:00Z")}}},
{"$count": "totalOrders"}
]).toArray());
// order-status: completedAt revenue cohort; createdAt for order counts.
printjson(demoDB.orders.aggregate([
{"$match": {"createdAt": {"$gte": ISODate("2026-07-03T00:00:00Z"), "$lt": ISODate("2026-10-01T00:00:00Z")}}},
{"$group": {"_id": "$orderStatus", "count": {"$sum": 1}}},
{"$sort": {"count": -1, "_id": 1}},
{"$project": {"_id": 0, "status": "$_id", "count": 1}}
]).toArray());
// customer-count: completedAt revenue cohort; createdAt for order counts.
printjson(demoDB.users.aggregate([
{"$match": {"role": "CUSTOMER"}},
{"$count": "totalCustomers"}
]).toArray());
printjson(demoDB.products.getIndexes());
printjson(demoDB.orders.getIndexes());
const category = demoDB.categories.findOne({productType: "ELECTRONICS"});
printjson(demoDB.products.find({status: "ACTIVE", categoryId: category._id, price: {$gte: NumberLong("1000000"), $lte: NumberLong("20000000")}}).sort({price: 1, _id: 1}).limit(10).explain("executionStats"));
