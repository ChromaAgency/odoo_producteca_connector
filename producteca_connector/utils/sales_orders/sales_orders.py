from pydantic import BaseModel, Field
from typing import List, Optional
import requests
from ..config.config import ConfigProducteca
import logging
_logger = logging.getLogger(__name__)

class SaleOrderLocation(BaseModel):
    streetName: Optional[str] = None
    streetNumber: Optional[str] = None
    addressNotes: Optional[str] = None
    state: Optional[str] = None
    city: Optional[str] = None
    neighborhood: Optional[str] = None
    zipCode: Optional[str] = None

class SaleOrderBillingInfo(BaseModel):
    docType: Optional[str] = None
    docNumber: Optional[str] = None
    streetName: Optional[str] = None
    streetNumber: Optional[str] = None
    comment: Optional[str] = None
    zipCode: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    stateRegistration: Optional[str] = None
    taxPayerType: Optional[str] = None
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    businessName: Optional[str] = None

class SaleOrderProfile(BaseModel):
    app: int
    integrationId: str
    nickname: Optional[str] = None

class SaleOrderContact(BaseModel):
    id: int
    name: str
    contactPerson: Optional[str] = None
    mail: Optional[str] = None
    phoneNumber: Optional[str] = None
    taxId: Optional[str] = None
    location: Optional[SaleOrderLocation] = None
    notes: Optional[str] = None
    type: Optional[str] = None
    priceList: Optional[str] = None
    priceListId: Optional[str] = None
    profile: Optional[SaleOrderProfile] = None
    billingInfo: Optional[SaleOrderBillingInfo] = None

class SaleOrderIntegrationId(BaseModel):
    alternateId: Optional[str] = None
    integrationId: str
    app: int

class SaleOrderVariationPicture(BaseModel):
    url: str
    id: Optional[int] = None

class SaleOrderVariationStock(BaseModel):
    warehouseId: Optional[int] = None
    warehouse: str
    quantity: int
    reserved: int
    lastModified: Optional[str] = None
    available: int

class SaleOrderVariationAttribute(BaseModel):
    key: str
    value: str

class SaleOrderVariation(BaseModel):
    supplierCode: Optional[str] = None
    pictures: Optional[List[SaleOrderVariationPicture]] = None
    stocks: Optional[List[SaleOrderVariationStock]] = None
    integrationId: Optional[int] = None
    attributesHash: Optional[str] = None
    primaryColor: Optional[str] = None
    secondaryColor: Optional[str] = None
    size: Optional[str] = None
    thumbnail: Optional[str] = None
    attributes: Optional[List[SaleOrderVariationAttribute]] = None
    integrations: Optional[List[SaleOrderIntegrationId]] = None
    id: int
    sku: str
    barcode: Optional[str] = None

class SaleOrderProduct(BaseModel):
    name: str
    code: str
    brand: Optional[str] = None
    id: int

class SaleOrderConversation(BaseModel):
    questions: Optional[List[str]] = None

class SaleOrderLine(BaseModel):
    price: float
    originalPrice: Optional[float] = None
    transactionFee: Optional[float] = None
    product: SaleOrderProduct
    variation: SaleOrderVariation
    orderVariationIntegrationId: Optional[str] = None
    quantity: int
    conversation: Optional[SaleOrderConversation] = None
    reserved: Optional[int] = None
    id: int

class SaleOrderCard(BaseModel):
    paymentNetwork: Optional[str] = None
    firstSixDigits: Optional[int] = None
    lastFourDigits: Optional[int] = None
    cardholderIdentificationNumber: Optional[str] = None
    cardholderIdentificationType: Optional[str] = None
    cardholderName: Optional[str] = None

class SaleOrderPaymentIntegration(BaseModel):
    integrationId: str
    app: int

class SaleOrderPayment(BaseModel):
    date: Optional[str] = None
    amount: float
    couponAmount: Optional[float] = None
    status: Optional[str] = None
    method: Optional[str] = None
    integration: Optional[SaleOrderPaymentIntegration] = None
    transactionFee: Optional[float] = None
    installments: Optional[int] = None
    card: Optional[SaleOrderCard] = None
    notes: Optional[str] = None
    authorizationCode: Optional[str] = None
    hasCancelableStatus: Optional[bool] = None
    id: Optional[int] = None

class SaleOrderShipmentMethod(BaseModel):
    trackingNumber: Optional[str] = None
    trackingUrl: Optional[str] = None
    courier: Optional[str] = None
    mode: Optional[str] = None
    cost: Optional[float] = None
    type: Optional[str] = None
    eta: Optional[int] = None
    status: Optional[str] = None

class SaleOrderShipmentProduct(BaseModel):
    product: int
    variation: int
    quantity: int

class SaleOrderShipmentIntegration(BaseModel):
    app: int
    integrationId: str
    status: str
    id: int

class SaleOrderShipment(BaseModel):
    date: str
    products: List[SaleOrderShipmentProduct]
    method: Optional[SaleOrderShipmentMethod] = None
    integration: Optional[SaleOrderShipmentIntegration] = None
    receiver: Optional[dict] = None
    id: int

class SaleOrderInvoiceIntegration(BaseModel):
    id: Optional[int] = None
    integrationId: Optional[str] = None
    app: Optional[int] = None
    createdAt: Optional[str] = None
    documentUrl: Optional[str] = None
    xmlUrl: Optional[str] = None
    decreaseStock: Optional[bool] = None

class SaleOrder(BaseModel):
    tags: Optional[List[str]] = None
    integrations: Optional[List[SaleOrderIntegrationId]] = None
    invoiceIntegration: Optional[SaleOrderInvoiceIntegration] = None
    channel: Optional[str] = None
    piiExpired: Optional[bool] = None
    contact: Optional[SaleOrderContact] = None
    lines: Optional[List[SaleOrderLine]] = None
    warehouse: Optional[str] = None
    warehouseId: Optional[int] = None
    warehouseIntegration: Optional[str] = None
    pickUpStore: Optional[str] = None
    payments: Optional[List[SaleOrderPayment]] = None
    shipments: Optional[List[SaleOrderShipment]] = None
    amount: Optional[float] = None
    shippingCost: Optional[float] = None
    financialCost: Optional[float] = None
    paidApproved: Optional[float] = None
    paymentStatus: Optional[str] = None
    deliveryStatus: Optional[str] = None
    paymentFulfillmentStatus: Optional[str] = None
    deliveryFulfillmentStatus: Optional[str] = None
    deliveryMethod: Optional[str] = None
    paymentTerm: Optional[str] = None
    currency: Optional[str] = None
    customId: Optional[str] = None
    isOpen: Optional[bool] = None
    isCanceled: Optional[bool] = None
    cartId: Optional[str] = None
    draft: Optional[bool] = None
    promiseDeliveryDate: Optional[str] = None
    promiseDispatchDate: Optional[str] = None
    hasAnyShipments: Optional[bool] = None
    hasAnyPayments: Optional[bool] = None
    date: Optional[str] = None
    notes: Optional[str] = None
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
    def synchronize(cls, config: ConfigProducteca, payload: "SaleOrder") -> tuple[int, "SaleOrder"]:
        endpoint = 'salesorders/synchronize'
        url = config.get_endpoint(endpoint)
        response = requests.post(url, data=payload.model_dump_json(exclude_none=True), headers=config.headers)
        return response.status_code, cls(**response.json())

    @classmethod
    def invoice_integration(cls, config: ConfigProducteca, sale_order_id: int, payload: "SaleOrder"):
        endpoint = f'salesorders/{sale_order_id}/invoiceIntegration'
        url = config.get_endpoint(endpoint)
        response = requests.put(url, headers=config.headers, data=payload.model_dump_json(exclude_none=True))
        if response.status_code == 200:
            return response.status_code, {}
        return response.status_code, response.json()