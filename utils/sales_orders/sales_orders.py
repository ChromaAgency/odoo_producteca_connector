from pydantic import BaseModel, Field
from typing import List, Optional
import requests
from ..config.config import ConfigProducteca

# (Tu MOCK_DATA queda tal cual como lo pasaste.)
MOCK_DATA = {
    "tags": [],
    "integrations": [
        {
            "alternateId": None,
            "integrationId": "0009922465656",
            "app": 2
        }
    ],
    "invoiceIntegration": {
        "id": 56211159,
        "integrationId": "150564521",
        "app": 30,
        "createdAt": "2025-01-30T20:23:33.749",
        "documentUrl": None,
        "xmlUrl": None,
        "decreaseStock": False
    },
    "channel": "2",
    "piiExpired": True,
    "contact": {
        "name": "ELGRILLO",
        "contactPerson": "Pepito Grillo",
        "mail": "ELGRILLO-noreply@mercadolibre.com",
        "phoneNumber": "XXXXXXX",
        "taxId": "30999099132",
        "location": {
            "streetName": "Pinocho",
            "streetNumber": "9209",
            "addressNotes": "Referencia: Casa Con Rejas Negras, Vereda De Lajas Y Un Pino En El Frente. Es La Calle Paralela A La Ruta 188 Entre: juan manuel de rosas y juarez celman",
            "state": "Buenos Aires",
            "city": "campos salles",
            "neighborhood": None,
            "zipCode": "2903"
        },
        "notes": None,
        "type": "Customer",
        "priceList": None,
        "priceListId": None,
        "profile": {
            "app": 2,
            "integrationId": "98432881",
            "nickname": None
        },
        "billingInfo": {
            "docType": "CUIT",
            "docNumber": "20380054605",
            "streetName": "rivadavia",
            "streetNumber": "51",
            "comment": "",
            "zipCode": "2900",
            "city": "buenos aires",
            "state": "Buenos Aires",
            "businessName": "Ferreteria y accesorios Gepeto",
            "stateRegistration": "000000000",
            "taxPayerType": "IVA Exento",
            "firstName": "",
            "lastName": ""
        },
        "id": 182511808
    },
    "lines": [
        {
            "price": 14830,
            "originalPrice": None,
            "transactionFee": 4098.65,
            "product": {
                "name": "Producto pa probar ventas 185051",
                "code": "",
                "brand": None,
                "id": 194731005
            },
            "variation": {
                "supplierCode": None,
                "pictures": [
                    {
                        "url": "https://assets.pokemon.com/assets/cms2/img/pokedex/full/006.png",
                        "id": 1893784098
                    }
                ],
                "stocks": [
                    {
                        "warehouseId": None,
                        "warehouse": "Default",
                        "quantity": -1,
                        "reserved": 0,
                        "lastModified": None,
                        "available": -1
                    }
                ],
                "integrationId": 0,
                "attributesHash": None,
                "primaryColor": None,
                "secondaryColor": None,
                "size": None,
                "thumbnail": None,
                "attributes": [],
                "integrations": [],
                "id": 357265018,
                "sku": "185051",
                "barcode": None
            },
            "orderVariationIntegrationId": None,
            "quantity": 1,
            "conversation": {
                "questions": []
            },
            "reserved": 0,
            "id": 157892082
        }
    ],
    "warehouse": "Default",
    "warehouseId": 461979,
    "warehouseIntegration": None,
    "pickUpStore": None,
    "payments": [
        {
            "date": "2024-11-22T16:18:44",
            "amount": 20514.99,
            "couponAmount": 0,
            "status": "Approved",
            "method": "CreditCard",
            "integration": {
                "integrationId": "83283040",
                "app": 2
            },
            "transactionFee": 0,
            "installments": 1,
            "card": {
                "paymentNetwork": "visa",
                "firstSixDigits": 0,
                "lastFourDigits": 0,
                "cardholderIdentificationNumber": None,
                "cardholderIdentificationType": None,
                "cardholderName": None
            },
            "notes": None,
            "authorizationCode": "008866",
            "hasCancelableStatus": False,
            "id": 111913219
        }
    ],
    "shipments": [
        {
            "date": "2024-11-22T16:18:44.053",
            "products": [
                {
                    "product": 194731005,
                    "variation": 357265018,
                    "quantity": 1
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
                "status": "Done"
            },
            "integration": {
                "app": 2,
                "integrationId": "441211136950",
                "status": "ReadyToPrint",
                "id": 76264337
            },
            "receiver": None,
            "id": 89462972
        }
    ],
    "amount": 20514.989999999998,
    "shippingCost": 5684.99,
    "financialCost": 0,
    "paidApproved": 20514.99,
    "paymentStatus": "Approved",
    "deliveryStatus": "Done",
    "paymentFulfillmentStatus": "Done",
    "deliveryFulfillmentStatus": "Done",
    "deliveryMethod": "Ship",
    "paymentTerm": "Advance",
    "currency": "Local",
    "customId": None,
    "isOpen": False,
    "isCanceled": False,
    "cartId": None,
    "draft": False,
    "promiseDeliveryDate": None,
    "promiseDispatchDate": None,
    "hasAnyShipments": True,
    "hasAnyPayments": True,
    "date": "2024-11-25T14:09:06",
    "notes": None,
    "id": 150564521
}


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
    date: str
    amount: float
    couponAmount: Optional[float] = None
    status: str
    method: str
    integration: SaleOrderPaymentIntegration
    transactionFee: Optional[float] = None
    installments: int
    card: Optional[SaleOrderCard] = None
    notes: Optional[str] = None
    authorizationCode: Optional[str] = None
    hasCancelableStatus: Optional[bool] = None
    id: int

class SaleOrderShipmentMethod(BaseModel):
    trackingNumber: str
    trackingUrl: str
    courier: str
    mode: str
    cost: float
    type: str
    eta: Optional[int] = None
    status: str

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
    method: SaleOrderShipmentMethod
    integration: SaleOrderShipmentIntegration
    receiver: Optional[str] = None
    id: int

class SaleOrderInvoiceIntegration(BaseModel):
    id: int
    integrationId: str
    app: int
    createdAt: str
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
        return cls(**MOCK_DATA)
        #return cls(**response.json())

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
