from pydantic import BaseModel, Field
from typing import List, Optional
import requests
from ..config.config import ConfigProducteca


class SaleOrderLocation(BaseModel):
    street_name: Optional[str] = None
    street_number: Optional[str] = None
    address_notes: Optional[str] = None
    state: Optional[str] = None
    city: Optional[str] = None
    zip_code: Optional[str] = None


class SaleOrderBillingInfo(BaseModel):
    doc_type: Optional[str] = None
    doc_number: Optional[str] = None
    street_name: Optional[str] = None
    street_number: Optional[str] = None
    comment: Optional[str] = None
    zip_code: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    state_registration: Optional[str] = None
    tax_payer_type: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    business_name: Optional[str] = None


class SaleOrderContact(BaseModel):
    id: int
    name: str
    contact_person: Optional[str] = None
    mail: Optional[str] = None
    phone_number: Optional[str] = None
    tax_id: Optional[str] = None
    location: Optional[SaleOrderLocation] = None
    type: Optional[str] = None
    profile: Optional[int] = None
    billing_info: Optional[SaleOrderBillingInfo] = None


class SaleOrderIntegrationId(BaseModel):
    integration_id: str
    app: int


class SaleOrderVariationPicture(BaseModel):
    url: str


class SaleOrderVariationStock(BaseModel):
    warehouse_id: int
    warehouse: str
    quantity: int
    reserved: int
    available: int


class SaleOrderVariationAttribute(BaseModel):
    key: str
    value: str


class SaleOrderVariation(BaseModel):
    pictures: Optional[List[SaleOrderVariationPicture]] = None
    stocks: Optional[List[SaleOrderVariationStock]] = None
    integration_id: Optional[int] = None
    attributes: Optional[List[SaleOrderVariationAttribute]] = None
    integrations: Optional[List[SaleOrderIntegrationId]] = None
    id: int
    sku: str


class SaleOrderProduct(BaseModel):
    name: str
    code: str
    brand: str
    id: int


class SaleOrderConversation(BaseModel):
    questions: Optional[List[str]] = None


class SaleOrderLine(BaseModel):
    price: float
    product: SaleOrderProduct
    variation: SaleOrderVariation
    quantity: int
    conversation: Optional[SaleOrderConversation] = None
    reserved: Optional[int] = None


class SaleOrderCard(BaseModel):
    payment_network: str
    first_six_digits: int
    last_four_digits: int
    cardholder_identification_number: str
    cardholder_identification_type: str
    cardholder_name: str


class SaleOrderPaymentIntegration(BaseModel):
    integration_id: str
    app: int


class SaleOrderPayment(BaseModel):
    date: str
    amount: float
    coupon_amount: float
    status: str
    method: str
    integration: SaleOrderPaymentIntegration
    transaction_fee: float
    installments: int
    card: Optional[SaleOrderCard] = None
    notes: Optional[str] = None
    has_cancelable_status: bool
    id: int


class SaleOrderShipmentMethod(BaseModel):
    tracking_number: str
    tracking_url: str
    courier: str
    mode: str
    cost: float
    type: str
    eta: str
    status: str


class SaleOrderShipmentProduct(BaseModel):
    product: int
    variation: int
    quantity: int


class SaleOrderShipmentIntegration(BaseModel):
    id: int
    integration_id: str
    app: int
    status: str


class SaleOrderShipment(BaseModel):
    date: str
    products: List[SaleOrderShipmentProduct]
    method: SaleOrderShipmentMethod
    integration: SaleOrderShipmentIntegration


class SaleOrderInvoiceIntegration(BaseModel):
    integration_id: str
    app: int
    created_at: str
    document_url: str
    xml_url: str
    decrease_stock: bool


class SaleOrder(BaseModel):
    tags: Optional[List[str]] = None
    integrations: Optional[List[int]] = None
    invoice_integration: Optional[SaleOrderInvoiceIntegration] = None
    channel: Optional[int] = None
    contact: Optional[SaleOrderContact] = None
    lines: Optional[List[SaleOrderLine]] = None
    warehouse: Optional[str] = None
    warehouse_id: Optional[int] = None
    payments: Optional[List[SaleOrderPayment]] = None
    shipments: Optional[List[SaleOrderShipment]] = None
    amount: Optional[float] = None
    shipping_cost: Optional[float] = None
    financial_cost: Optional[float] = None
    paid_approved: Optional[float] = None
    payment_status: Optional[str] = None
    delivery_status: Optional[str] = None
    payment_fulfillment_status: Optional[str] = None
    delivery_fulfillment_status: Optional[str] = None
    delivery_method: Optional[str] = None
    payment_term: Optional[str] = None
    currency: Optional[str] = None
    custom_id: Optional[str] = None
    is_open: Optional[bool] = None
    is_canceled: Optional[bool] = None
    has_any_shipments: Optional[bool] = None
    has_any_payments: Optional[bool] = None
    date: Optional[str] = None
    id: int

    @classmethod
    def get(cls, config: ConfigProducteca, sale_order_id: int) -> "SaleOrder":
        endpoint = f'salesorders/{sale_order_id}'
        url = config.get_endpoint(endpoint)
        response = requests.get(url, headers=config.headers)
        return cls(**response.json())

    @classmethod
    def get_shipping_labels(cls, config: ConfigProducteca, sale_order_id: int):
        endpoint = f'salesorders/{sale_order_id}/labels'
        url = config.get_endpoint(endpoint)
        response = requests.get(url, headers=config.headers)
        return response.json()

    @classmethod
    def close(cls, config: ConfigProducteca, sale_order_id: int):
        endpoint = f'salesorders/{sale_order_id}/close'
        url = config.get_endpoint(endpoint)
        response = requests.post(url, headers=config.headers)
        return response.status_code, response.json()

    @classmethod
    def cancel(cls, config: ConfigProducteca, sale_order_id: int):
        endpoint = f'salesorders/{sale_order_id}/cancel'
        url = config.get_endpoint(endpoint)
        response = requests.post(url, headers=config.headers)
        return response.status_code, response.json()

    @classmethod
    def synchronize(cls, config: ConfigProducteca, payload: "SaleOrder") -> "SaleOrder":
        endpoint = 'salesorders/synchronize'
        url = config.get_endpoint(endpoint)
        response = requests.post(url, data=payload.model_dump_json(exclude_none=True), headers=config.headers)
        return cls(**response.json())