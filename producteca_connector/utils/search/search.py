from typing import List, Optional
from pydantic import BaseModel, Field
import requests
from ..config.config import ConfigProducteca


class FacetValue(BaseModel):
    count: int
    value: str
    label: str


class Facet(BaseModel):
    key: str
    value: List[FacetValue]
    is_collection: bool
    translate: bool


class SearchStocks(BaseModel):
    warehouse: str
    quantity: int
    reserved: int


class SearchPrices(BaseModel):
    price_list_id: int
    price_list: str
    amount: float
    currency: str


class SearchIntegration(BaseModel):
    app: Optional[int]
    integration_id: Optional[str]
    permalink: Optional[str]
    status: Optional[str]
    listing_type: Optional[str]
    safety_stock: Optional[int]
    synchronize_stock: Optional[bool]
    is_active: Optional[bool]
    is_active_or_paused: Optional[bool]
    id: Optional[int]


class SearchDeals(BaseModel):
    campaign: str
    product: int
    variation: str
    deal_price: float
    discount: float
    regular_price: float
    enabled: bool
    currency: str
    id: str


class SearchResultItem(BaseModel):
    search_score: float = Field(..., alias='@search.score')
    id: int
    product_id: int
    company_id: int
    name: str
    code: str
    skus: List[str]
    brand: str
    category: str
    thumbnail: str
    stocks: List[SearchStocks]
    warehouses_with_stock: List[str]
    total_stock: int
    has_pictures: bool
    buying_price: float
    prices: List[SearchPrices]
    integration_ids: List[str]
    integration_apps: List[str]
    integrations: List[SearchIntegration]
    campaigns: List[str]
    app: Optional[int]
    status: Optional[str]
    synchronize_stock: Optional[bool]
    listing_type: Optional[str]
    price_amount: Optional[float]
    price_currency: Optional[str]
    category_id: Optional[str]
    category_base_id: Optional[str]
    category_l1: Optional[str]
    category_l2: Optional[str]
    category_l3: Optional[str]
    category_l4: Optional[str]
    category_l5: Optional[str]
    category_l6: Optional[str]
    has_category: Optional[bool]
    category_fixed: Optional[bool]
    accepts_mercadoenvios: Optional[bool]
    shipping_mode: Optional[str]
    local_pickup: Optional[bool]
    mandatory_free_shipping: Optional[bool]
    free_shipping: Optional[bool]
    free_shipping_cost: Optional[float]
    template: Optional[str]
    youtube_id: Optional[str]
    warranty: Optional[str]
    permalink: Optional[str]
    domain: Optional[str]
    attribute_completion_status: Optional[str]
    attribute_completion_count: Optional[int]
    attribute_completion_total: Optional[int]
    deals: Optional[SearchDeals]
    campaign_status: Optional[List[str]]
    size_chart: Optional[str]
    channel_status: Optional[List[str]]
    channel_category_l1: Optional[List[str]]
    channel_category_l2: Optional[List[str]]
    channel_category_l3: Optional[List[str]]
    channel_category_id: Optional[List[str]]
    channel_synchronizes_stock: Optional[List[str]]
    channel_has_category: Optional[List[str]]
    catalog_products_status: Optional[List[str]]
    metadata: Optional[List[str]]
    integration_tags: Optional[List[str]]
    variations_integration_ids: Optional[List[str]]
    channel_pictures_templates: Optional[List[str]]
    channel_pictures_templates_apps: Optional[List[str]]


class SearchProductResponse(BaseModel):
    count: int
    facets: List[Facet]
    results: List[SearchResultItem]


class SearchProductParams(BaseModel):
    top: Optional[int]
    skip: Optional[int]
    filter: Optional[str] = Field(default=None, alias='$filter')
    search: Optional[str]
    sales_channel: Optional[str] = Field(default='2', alias='salesChannel')


class SearchProduct:
    endpoint: str = 'search/products'

    @classmethod
    def search_product(cls, config: ConfigProducteca, params: SearchProductParams) -> SearchProductResponse:
        headers = config.headers
        url = config.get_endpoint(cls.endpoint)
        response = requests.get(url, headers=headers, params=params.dict(by_alias=True, exclude_none=True))
        return SearchProductResponse(**response.json())
