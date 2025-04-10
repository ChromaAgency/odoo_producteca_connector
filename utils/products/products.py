from typing import List, Optional
from pydantic import BaseModel, Field
import requests
from ..config.config import ConfigProducteca


class Component(BaseModel):
    quantity: Optional[int] = Field(default=None)
    variation_id: Optional[int] = Field(default=None)
    product_id: Optional[int] = Field(default=None)


class Pictures(BaseModel):
    url: str = ''


class Stocks(BaseModel):
    quantity: Optional[int] = Field(default=None)
    available_quantity: Optional[int] = Field(default=None)
    warehouse: str = ''
    warehouse_id: Optional[int] = Field(default=None)
    reserved: Optional[int] = Field(default=None)
    available: Optional[int] = Field(default=None)


class Attributes(BaseModel):
    key: str = ''
    value: str = ''


class Integrations(BaseModel):
    app: Optional[int] = Field(default=None)
    integration_id: Optional[str] = Field(default=None)
    permalink: Optional[str] = Field(default=None)
    status: Optional[str] = Field(default=None)
    listing_type: Optional[str] = Field(default=None)
    safety_stock: Optional[int] = Field(default=None)
    synchronize_stock: Optional[bool] = Field(default=None)
    is_active: Optional[bool] = Field(default=None)
    is_active_or_paused: Optional[bool] = Field(default=None)
    id: Optional[int] = Field(default=None)
    parent_integration: Optional[str] = Field(default=None)


class Variation(BaseModel):
    variation_id: Optional[int] = Field(default=None)
    components: Optional[List[Component]] = Field(default=None)
    pictures: Optional[List[Pictures]] = Field(default=None)
    stocks: Optional[List[Stocks]] = Field(default=None)
    attributes_hash: Optional[str] = Field(default=None)
    primary_color: Optional[str] = Field(default=None)
    thumbnail: Optional[str] = Field(default=None)
    attributes: Optional[List[Attributes]] = Field(default=None)
    integrations: Optional[List[Integrations]] = Field(default=None)
    id: Optional[int] = Field(default=None)
    sku: Optional[str] = Field(default=None)
    barcode: Optional[str] = Field(default=None)


class ResultItem(BaseModel):
    company_id: Optional[int] = Field(default=None)
    product_id: Optional[int] = Field(default=None)
    variations: Optional[List[Variation]] = Field(default=None)
    id: Optional[str] = Field(default=None)


class ResultsResponse(BaseModel):
    results: Optional[List[ResultItem]] = Field(default=None)
    count: Optional[int] = Field(default=None)


class Prices(BaseModel):
    amount: Optional[float] = Field(default=None)
    currency: str = ''
    price_list: str = ''
    price_list_id: Optional[int] = Field(default=None)


class Tags(BaseModel):
    tag: str = ''


class Shipping(BaseModel):
    local_pickup: Optional[bool] = Field(default=None)
    mode: Optional[str] = Field(default=None)
    free_shipping: Optional[bool] = Field(default=None)
    free_shipping_cost: Optional[float] = Field(default=None)
    mandatory_free_shipping: Optional[bool] = Field(default=None)
    free_shipping_method: Optional[str] = Field(default=None)


class MShopsShipping(BaseModel):
    enabled: Optional[bool] = Field(default=None)


class Category(BaseModel):
    meli_id: Optional[str] = Field(default=None)
    accepts_mercadoenvios: Optional[bool] = Field(default=None)
    suggest: Optional[bool] = Field(default=None)
    fixed: Optional[bool] = Field(default=None)


class AttributeCompletion(BaseModel):
    product_identifier_status: Optional[str] = Field(default=None)
    data_sheet_status: Optional[str] = Field(default=None)
    status: Optional[str] = Field(default=None)
    count: Optional[int] = Field(default=None)
    total: Optional[int] = Field(default=None)


class Deals(BaseModel):
    campaign: str = ''
    regular_price: Optional[float] = None
    deal_price: Optional[float] = None


class Product(BaseModel):
    config: Optional[ConfigProducteca] = Field(default=None, exclude=True)
    create_if_not_exist: bool = False
    product_id: Optional[int] = None
    sku: str = ''
    variation_id: Optional[int] = None
    code: str = ''
    name: str = ''
    barcode: str = ''
    attributes: List[Attributes] = []
    tags: List[Tags] = []
    buying_price: Optional[float] = None
    dimensions: Optional[dict] = None
    category: Optional[Category] = None
    brand: str = ''
    notes: str = ''
    deals: List[Deals] = []
    stocks: List[Stocks] = []
    prices: List[Prices] = []
    pictures: List[Pictures] = []
    integrations: Optional[List[Integrations]] = None
    variations: Optional[List[Variation]] = None
    is_simple: Optional[bool] = None
    has_variations: Optional[bool] = None
    thumbnail: Optional[str] = None
    is_archived: Optional[bool] = None
    metadata: Optional[List[str]] = None
    is_original: Optional[bool] = None
    id: Optional[int] = None
    attributes_hash: Optional[str] = None
    primary_color: Optional[str] = None
    has_custom_shipping_costs: Optional[bool] = None
    shipping: Optional[Shipping] = None
    mshops_shipping: Optional[MShopsShipping] = None
    add_free_shipping_cost_to_price: Optional[bool] = None
    attribute_completion: Optional[AttributeCompletion] = None
    catalog_products: Optional[List[str]] = None
    warranty: Optional[str] = None
    domain: Optional[str] = None
    listing_type_id: Optional[str] = None
    catalog_products_status: Optional[str] = None
    tags_list: Optional[List[str]] = None

    endpoint: str = Field(default='products', exclude=True)

    def create(self):
        endpoint_url = self.config.get_endpoint(f'{self.endpoint}/synchronize')
        headers = self.config.headers.copy()
        headers.update({"createifitdoesntexist": str(self.create_if_not_exist).lower()})
        response = requests.post(endpoint_url, data=self.model_dump_json(exclude_none=True), headers=headers)
        return Product(**response.json())

    @classmethod
    def get(cls, config: ConfigProducteca, product_id: int):
        endpoint_url = config.get_endpoint(f'{cls.endpoint}/{product_id}')
        headers = config.headers
        response = requests.get(endpoint_url, headers=headers)
        return cls(config=config, **response.json())

    @classmethod
    def get_bundle(cls, config: ConfigProducteca, product_id: int):
        endpoint_url = config.get_endpoint(f'{cls.endpoint}/{product_id}/bundles')
        headers = config.headers
        response = requests.get(endpoint_url, headers=headers)
        return cls(config=config, **response.json())

    @classmethod
    def get_ml_integration(cls, config: ConfigProducteca, product_id: int):
        endpoint_url = config.get_endpoint(f'{cls.endpoint}/{product_id}/listintegration')
        headers = config.headers
        response = requests.get(endpoint_url, headers=headers)
        return cls(config=config, **response.json())