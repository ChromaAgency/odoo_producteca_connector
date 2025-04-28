from typing import List, Optional
from pydantic import BaseModel, Field
import requests
from ..config.config import ConfigProducteca
import logging

_logger = logging.getLogger(__name__)

MOCKDATA = {
            "count": 15,
            "results": [
                {
                    "@search.score": 1,
                    "codes": [],
                    "contactId": 182511808,
                    "contactName": None,
                    "contactPerson": None,
                    "currency": "Local",
                    "date": "2024-11-25T14:09:06Z",
                    "deliveryMethod": "Ship",
                    "deliveryStatus": "Done",
                    "id": "150561122",
                    "integrationIds": ["0009922465656"],
                    "integrations": [
                        {
                            "alternateId": None,
                            "integrationId": "0009922465656",
                            "app": 2,
                        }
                    ],
                    "invoiceIntegrationApp": 30,
                    "invoiceIntegrationId": "150564521",
                    "lines": [
                        {
                            "product": {
                                "name": "Producto pa probar ventas 185051",
                                "code": "",
                                "brand": None,
                                "id": 194731005,
                            },
                            "variation": {
                                "id": 357265018,
                                "attributes": [],
                                "sku": "185051",
                                "thumbnail": "https://assets.pokemon.com/assets/cms2/img/pokedex/full/006.png",
                            },
                            "quantity": 1,
                            "price": 14830,
                        }
                    ],
                    "payments": [
                        {
                            "date": "2024-11-22T16:18:44",
                            "amount": 20514.99,
                            "couponAmount": 0,
                            "status": "Approved",
                            "method": "CreditCard",
                            "integration": {"integrationId": "83283040", "app": 2},
                            "transactionFee": 0,
                            "installments": 1,
                            "notes": None,
                            "authorizationCode": "008866",
                            "hasCancelableStatus": False,
                            "id": 111913219,
                        }
                    ],
                    "paymentStatus": "Approved",
                    "paymentTerm": "Advance",
                    "productNames": ["Producto pa probar ventas 185051"],
                    "reservingProductIds": [],
                    "reservingVariationIds": [],
                    "salesChannel": 2,
                    "shipments": [
                        {
                            "date": "2024-11-22T16:18:44.053",
                            "products": [
                                {
                                    "product": 194731005,
                                    "variation": 357265018,
                                    "quantity": 1,
                                }
                            ],
                            "method": {
                                "trackingNumber": "0",
                                "trackingUrl": "https://myaccount.mercadolibre.com.ar/purchases/2000009922465656/shipments/44121113695/detail",
                                "courier": "Flex",
                                "mode": "Prioritario a domicilio",
                                "cost": 0,
                                "type": "Ship",
                                "eta": 0,
                                "status": "Done",
                            },
                            "integration": {
                                "app": 2,
                                "integrationId": "441211136950",
                                "status": "ReadyToPrint",
                                "id": 76264337,
                            },
                            "id": 89462972,
                        }
                    ],
                    "trackingNumber": "0",
                    "shippingAddress": None,
                    "skus": ["185051"],
                    "status": "Closed",
                    "tags": [],
                    "warehouse": "Default",
                    "companyId": 246807,
                    "shippingCost": 5684.99,
                    "contactPhone": None,
                    "brands": [],
                    "courier": "Flex",
                    "orderId": 150564521,
                    "updatedAt": "2025-03-20T18:27:16.3Z",
                    "invoiceIntegrationCreatedAt": "2025-01-30T20:23:33.749Z",
                    "invoiceIntegrationDocumentUrl": None,
                    "hasDocumentUrl": False,
                    "invoiceIntegrationXmlUrl": None,
                    "hasXmlUrl": False,
                    "integrationAlternateIds": [],
                    "cartId": None,
                    "draft": False,
                    "pickUpStoreName": None,
                    "promiseDeliveryDate": None,
                    "amount": 20514.99,
                    "hasAnyShipments": True,
                }
            ],
        }
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


class SearchSalesOrder:
    endpoint: str = "search/saleorders"

    @classmethod
    def search_saleorder(cls, config: ConfigProducteca, params: SearchSalesOrderParams):
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"apiKey={config.api_key}&token={config.token}",
            "Accept": "*/*",
        }
        url = config.get_endpoint(cls.endpoint)
        response = requests.get(
            url,
            headers=headers,
            params=params.model_dump(by_alias=True, exclude_none=True),
        )
        # return response.json(), response.status_code
        return MOCKDATA, 200


