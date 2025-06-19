from typing import List, Optional
from pydantic import BaseModel, Field
import requests
from ..config.config import ConfigProducteca
import logging

_logger = logging.getLogger(__name__)


class SalesOrderProduct(BaseModel):
    id: int
    name: str
    code: str
    brand: str


class SalesOrderVariationAttribute(BaseModel):
    key: str
    value: str


class SalesOrderVariation(BaseModel):
    id: int
    attributes: List[SalesOrderVariationAttribute]
    sku: str
    thumbnail: str


class SalesOrderLine(BaseModel):
    product: SalesOrderProduct
    variation: SalesOrderVariation
    quantity: int
    price: float


class SalesOrderCard(BaseModel):
    payment_network: str
    first_six_digits: int
    last_four_digits: int
    cardholder_identification_number: str
    cardholder_identification_type: str
    cardholder_name: str


class SalesOrderPaymentIntegration(BaseModel):
    integration_id: str
    app: int


class SalesOrderPayment(BaseModel):
    date: str
    amount: float
    coupon_amount: float
    status: str
    method: str
    integration: SalesOrderPaymentIntegration
    transaction_fee: float
    installments: int
    card: SalesOrderCard
    notes: str
    has_cancelable_status: bool
    id: int


class SalesOrderIntegration(BaseModel):
    alternate_id: str
    integration_id: int
    app: int


class SalesOrderShipmentProduct(BaseModel):
    product: int
    variation: int
    quantity: int


class SalesOrderShipmentMethod(BaseModel):
    tracking_number: str
    tracking_url: str
    courier: str
    mode: str
    cost: float
    type: str
    eta: str
    status: str


class SalesOrderShipmentIntegration(BaseModel):
    id: int
    integration_id: str
    app: int
    status: str


class SalesOrderShipment(BaseModel):
    date: str
    products: List[SalesOrderShipmentProduct]
    method: SalesOrderShipmentMethod
    integration: SalesOrderShipmentIntegration


class SalesOrderResultItem(BaseModel):
    codes: List[str]
    contact_id: int
    currency: str
    date: str
    delivery_method: str
    delivery_status: str
    id: str
    integration_ids: List[str]
    integrations: List[SalesOrderIntegration]
    invoice_integration_app: int
    invoice_integration_id: str
    lines: List[SalesOrderLine]
    payments: List[SalesOrderPayment]
    payment_status: str
    payment_term: str
    product_names: List[str]
    reserving_product_ids: str
    sales_channel: int
    shipments: List[SalesOrderShipment]
    tracking_number: str
    skus: List[str]
    status: str
    tags: List[str]
    warehouse: str
    company_id: int
    shipping_cost: float
    contact_phone: str
    brands: List[str]
    courier: str
    order_id: int
    updated_at: str
    invoice_integration_created_at: str
    invoice_integration_document_url: str
    has_document_url: bool
    integration_alternate_ids: str
    cart_id: str
    amount: float
    has_any_shipments: bool


class SearchSalesOrderResponse(BaseModel):
    count: int
    results: List[SalesOrderResultItem]


class SearchSalesOrderParams(BaseModel):
    top: Optional[int]
    skip: Optional[int]
    filter: Optional[str] = Field(default=None, alias="$filter")
    class Config:
        validate_by_name = True

class SearchSalesOrder:
    endpoint: str = "search/salesorders"


    @classmethod
    def search_saleorder(cls, config: ConfigProducteca, params: SearchSalesOrderParams):
        headers = config.headers
        url = config.get_endpoint(cls.endpoint)
        new_url = f"{url}?$filter={params.filter}&top={params.top}&skip={params.skip}"
        response = requests.get(
            new_url,
            headers=headers,
        )
        return response.json(), response.status_code


