// READ ONLY — no index deletion/creation; same query/results.
const demoDb07c = db.getSiblingDB("ecommerce_dev");
const demoFilter07c = {categoryId:ObjectId("4ad126c3ebc4fb3918f084d4"),status:"ACTIVE",price:{$gte:1000000,$lte:20000000}};
const demoSort07c = {price:1,_id:1};
const demoScan07c = demoDb07c.products.find(demoFilter07c).sort(demoSort07c).limit(10).hint({$natural:1}).explain("executionStats");
const demoIndex07c = demoDb07c.products.find(demoFilter07c).sort(demoSort07c).limit(10).hint("ix_products_category_price").explain("executionStats");
printjson({withoutUsingIndex:{plan:demoScan07c.queryPlanner.winningPlan,stats:demoScan07c.executionStats},withIndex:{plan:demoIndex07c.queryPlanner.winningPlan,stats:demoIndex07c.executionStats}});
