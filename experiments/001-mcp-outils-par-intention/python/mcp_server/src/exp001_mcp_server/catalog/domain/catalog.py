import unicodedata
from decimal import Decimal

from exp001_mcp_server.catalog.domain.entities.alternative import Alternative
from exp001_mcp_server.catalog.domain.entities.product import Product
from exp001_mcp_server.catalog.domain.entities.stock_line import StockLine
from exp001_mcp_server.catalog.domain.entities.store import Store
from exp001_mcp_server.catalog.domain.entities.store_stock import StoreStock
from exp001_mcp_server.catalog.domain.errors import (
    DepartmentNotFoundError,
    InvalidSearchQueryError,
    ProductNotFoundError,
    StoreNotFoundError,
)
from exp001_mcp_server.catalog.domain.port.product_repository import ProductRepository
from exp001_mcp_server.catalog.domain.port.stock_repository import StockRepository
from exp001_mcp_server.catalog.domain.port.store_repository import StoreRepository
from exp001_mcp_server.catalog.domain.vo.sku_code import SkuCode
from exp001_mcp_server.catalog.domain.vo.store_id import StoreId

PRICE_TOLERANCE = Decimal("0.20")
MAX_ALTERNATIVES = 3


class Catalog:
    def __init__(
        self, products: ProductRepository, stores: StoreRepository, stock: StockRepository
    ) -> None:
        self._products = products
        self._stores = stores
        self._stock = stock

    def stores(self) -> list[Store]:
        return list(self._stores.find_all())

    def product(self, sku: SkuCode) -> Product | None:
        return self._products.find_by_sku(sku)

    def store(self, store_id: StoreId) -> Store | None:
        return self._stores.find_by_id(store_id)

    def require_product(self, sku: SkuCode) -> Product:
        product = self.product(sku)
        if product is None:
            raise ProductNotFoundError(sku)
        return product

    def require_store(self, store_id: StoreId) -> Store:
        store = self.store(store_id)
        if store is None:
            raise StoreNotFoundError(store_id)
        return store

    def departments(self) -> list[str]:
        return sorted({product.department for product in self._products.find_all()})

    def stock(self, sku: SkuCode, store_id: StoreId) -> StockLine | None:
        return self._stock.find(sku, store_id)

    def stores_with_stock(self, sku: SkuCode) -> list[StoreStock]:
        stores = sorted(self._stores.find_all(), key=lambda store: store.store_id.value)
        stocks = (StoreStock(store, self._available(sku, store.store_id)) for store in stores)
        return [stock for stock in stocks if stock.available > 0]

    def similar(self, sku: SkuCode) -> list[Product]:
        reference = self.product(sku)
        if reference is None:
            return []
        low = reference.price * (1 - PRICE_TOLERANCE)
        high = reference.price * (1 + PRICE_TOLERANCE)
        candidates = [
            candidate
            for candidate in self._products.find_all()
            if candidate.type == reference.type
            and candidate.sku != reference.sku
            and low <= candidate.price <= high
        ]
        return sorted(
            candidates,
            key=lambda candidate: (abs(candidate.price - reference.price), candidate.sku.value),
        )

    def alternatives(self, sku: SkuCode, store_id: StoreId) -> list[Alternative]:
        alternatives = (
            Alternative(candidate, self._available(candidate.sku, store_id))
            for candidate in self.similar(sku)
        )
        return [alternative for alternative in alternatives if alternative.available > 0][
            :MAX_ALTERNATIVES
        ]

    def browse(self, department: str | None) -> list[Product]:
        wanted = _fold(department) if department and department.strip() else None
        if wanted is not None and all(_fold(known) != wanted for known in self.departments()):
            raise DepartmentNotFoundError(department or "")
        products = [
            product
            for product in self._products.find_all()
            if wanted is None or _fold(product.department) == wanted
        ]
        return sorted(products, key=lambda product: (product.name, product.sku.value))

    def search(self, query: str, department: str | None) -> list[Product]:
        if not query.strip():
            raise InvalidSearchQueryError("Search query must not be blank")
        words = _fold(query).split()
        return [
            product
            for product in self.browse(department)
            if all(
                word in _fold(f"{product.name} {product.brand} {product.type}") for word in words
            )
        ]

    def _available(self, sku: SkuCode, store_id: StoreId) -> int:
        line = self.stock(sku, store_id)
        return line.available if line is not None else 0


def _fold(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text)
    without_marks = "".join(
        char for char in decomposed if not unicodedata.category(char).startswith("M")
    )
    return without_marks.lower().strip()
