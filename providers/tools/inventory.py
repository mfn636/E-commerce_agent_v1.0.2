from typing import Optional, List

from domain.loader import load_inventory, load_products
from domain.models.product import Product
from domain.models.inventory import InventoryDetail

INVENTORY = load_inventory()
PRODUCTS: List[Product] = load_products()
# 构建ID映射键值对
PRODUCT_MAP = {p.id: p for p in PRODUCTS}


def check_inventory(
    product_id: Optional[str] = None,
    category: Optional[str] = None,
) -> List[InventoryDetail]:
    results = []

    for item in INVENTORY:
        pid = item.product_id
        product = PRODUCT_MAP.get(pid)
        if not product:
            continue

        if product_id and pid != product_id:
            continue

        if category and category not in product.category:
            continue

        results.append(InventoryDetail(
            product_id=pid,
            product_name=product.name,
            stock=item.stock,
            in_stock=item.stock > 0,
        ))

    return results
