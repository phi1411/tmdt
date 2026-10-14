// READ ONLY replay of 07B; do not create/drop indexes or use this DB for checkout.
const benchDb07c = db.getSiblingDB("ecommerce_benchmark");
const benchCommand07c = {
  "find": "products",
  "filter": {
    "status": "ACTIVE",
    "productType": "ELECTRONICS",
    "categoryId": ObjectId("9f279f9b19426a6a465cfd3a"),
    "price": {
      "$gte": 2000000,
      "$lte": 5000000
    }
  },
  "sort": {
    "price": 1,
    "_id": 1
  },
  "projection": {
    "_id": 1,
    "sku": 1,
    "name": 1,
    "slug": 1,
    "categoryId": 1,
    "productType": 1,
    "brand": 1,
    "description": 1,
    "price": 1,
    "stock": 1,
    "images": 1,
    "attributes": 1,
    "status": 1,
    "version": 1,
    "createdAt": 1,
    "updatedAt": 1
  },
  "limit": 20,
  "maxTimeMS": 60000
};
const benchNatural07c = benchDb07c.runCommand({explain:{...benchCommand07c,hint:{$natural:1}},verbosity:"executionStats"});
const benchIndex07c = benchDb07c.runCommand({explain:{...benchCommand07c,hint:"ix_products_category_price"},verbosity:"executionStats"});
printjson({withoutUsingIndex:{plan:benchNatural07c.queryPlanner.winningPlan,stats:benchNatural07c.executionStats},withIndex:{plan:benchIndex07c.queryPlanner.winningPlan,stats:benchIndex07c.executionStats}});
