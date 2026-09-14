'''
该文件返回一个list，list中是pydantic对象
'''

import json
from pathlib import Path

from domain.models.product import Product
from domain.models.inventory import InventoryItem
from domain.models.faq import FaqItem


PRODUCT_FILE = Path(__file__).parent / "data" / "products.json"
INVENTORY_FILE = Path(__file__).parent / "data" / "inventory.json"
FAQ_FILE = Path(__file__).parent / "data" / "faq.json"


def load_products():
    with open(PRODUCT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [Product(**item) for item in data["products"]]
# 

def load_inventory():
    with open(INVENTORY_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [InventoryItem(**item) for item in data]


def load_faq():
    with open(FAQ_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [FaqItem(**item) for item in data]



