"""Locked query names/sorts shared by implemented public/Admin Product APIs."""
PRODUCT_QUERY_FIELDS = frozenset({
    'q', 'categoryId', 'productType', 'brand', 'minPrice', 'maxPrice',
    'size', 'color', 'ram', 'capacity', 'sort', 'page', 'pageSize',
})
PRODUCT_SORTS = {
    'latest': [('createdAt', -1), ('_id', -1)],
    'price_asc': [('price', 1), ('_id', 1)],
    'price_desc': [('price', -1), ('_id', -1)],
}
DEFAULT_PRODUCT_SORT = 'latest'
