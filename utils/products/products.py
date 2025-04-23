from typing import List, Optional, Union
from pydantic import BaseModel, Field
import requests
from ..config.config import ConfigProducteca
import logging

_logger = logging.getLogger(__name__)

# Models for nested structures

class Attribute(BaseModel):
    key: str
    value: str

class Tag(BaseModel):
    tag: str

class Dimensions(BaseModel):
    weight: Optional[float] = None
    width: Optional[float] = None
    height: Optional[float] = None
    length: Optional[float] = None
    pieces: Optional[int] = None

class Deal(BaseModel):
    campaign: str
    regular_price: Optional[float] = Field(default=None, alias='regularPrice')
    deal_price: Optional[float] = Field(default=None, alias='dealPrice')

class Stock(BaseModel):
    quantity: Optional[int] = None
    available_quantity: Optional[int] = Field(default=None, alias='availableQuantity')
    warehouse: Optional[str] = None
    warehouse_id: Optional[int] = Field(default=None, alias='warehouseId')
    reserved: Optional[int] = None
    available: Optional[int] = None

class Price(BaseModel):
    amount: Optional[float] = None
    currency: str
    price_list: str = Field(alias='priceList')
    price_list_id: Optional[int] = Field(default=None, alias='priceListId')

class Picture(BaseModel):
    url: str

class Integration(BaseModel):
    app: Optional[int] = None
    integration_id: Optional[str] = Field(default=None, alias='integrationId')
    permalink: Optional[str] = None
    status: Optional[str] = None
    listing_type: Optional[str] = Field(default=None, alias='listingType')
    safety_stock: Optional[int] = Field(default=None, alias='safetyStock')
    synchronize_stock: Optional[bool] = Field(default=None, alias='synchronizeStock')
    is_active: Optional[bool] = Field(default=None, alias='isActive')
    is_active_or_paused: Optional[bool] = Field(default=None, alias='isActiveOrPaused')
    id: Optional[int] = None
    parent_integration: Optional[str] = Field(default=None, alias='parentIntegration')

class Variation(BaseModel):
    variation_id: Optional[int] = Field(default=None, alias='variationId')
    components: Optional[List] = None
    pictures: Optional[List[Picture]] = None
    stocks: Optional[List[Stock]] = None
    attributes_hash: Optional[str] = Field(default=None, alias='attributesHash')
    primary_color: Optional[str] = Field(default=None, alias='primaryColor')
    thumbnail: Optional[str] = None
    attributes: Optional[List[Attribute]] = None
    integrations: Optional[List[Integration]] = None
    id: Optional[int] = None
    sku: Optional[str] = None
    barcode: Optional[str] = None

# Model base para los productos
class Product(BaseModel):
    config: Optional[ConfigProducteca] = Field(default=None, exclude=True)
    endpoint: str = Field(default='products', exclude=True)
    create_if_it_doesnt_exist: bool = Field(default=False, exclude=True)
    sku: Optional[str] = None
    variation_id: Optional[int] = None
    code: Optional[str] = None
    name: Optional[str] = None
    barcode: Optional[str] = None
    attributes: Optional[List[Attribute]] = None
    tags: Optional[List[str]] = None
    buying_price: Optional[float] = None
    dimensions: Optional[Dimensions] = None
    category: Optional[Union[str, dict]] = None  # Puede ser string en POST o dict en GET Meli
    brand: Optional[str] = None
    notes: Optional[str] = None
    deals: Optional[List[Deal]] = None
    stocks: Optional[List[Stock]] = None
    prices: Optional[List[Price]] = None
    pictures: Optional[List[Picture]] = None


    def create(self):
        endpoint_url = self.config.get_endpoint(f'{self.endpoint}/synchronize')
        headers = self.config.headers.copy()
        headers.update({"createifitdoesntexist": str(self.create_if_it_doesnt_exist).lower()})
        data = self.model_dump_json(by_alias=True, exclude_none=True)
        response = requests.post(endpoint_url, data=data, headers=headers)
        if response.status_code == 204:
            final_response = {"Message":"Product does not exist and the request cant create if it does not exist"}
        else:
            final_response = response.json()
        return final_response, response.status_code

    def update(self):
        endpoint_url = self.config.get_endpoint(f'{self.endpoint}/synchronize')
        headers = self.config.headers.copy()
        data = self.model_dump_json(by_alias=True, exclude_none=True)
        if not self.code and not self.sku:
            return {"Message":"Sku or code should be provided to update the product"}, 204
        response = requests.post(endpoint_url, data=data, headers=headers)
        if response.status_code == 204:
            final_response = {"Message":"Product does not exist and the request cant create if it does not exist"}
        else:
            final_response = response.json()
        return final_response, response.status_code

    @classmethod
    def get(cls, config: ConfigProducteca, product_id: int):
        endpoint_url = config.get_endpoint(f'{cls().endpoint}/{product_id}')
        headers = config.headers
        response = requests.get(endpoint_url, headers=headers)
        response_data = response.json()
        return response_data, response.status_code

    @classmethod
    def get_bundle(cls, config: ConfigProducteca, product_id: int):
        endpoint_url = config.get_endpoint(f'{cls().endpoint}/{product_id}/bundles')
        headers = config.headers
        response = requests.get(endpoint_url, headers=headers)
        return cls(config=config, **response.json()), response.status_code

    @classmethod
    def get_ml_integration(cls, config: ConfigProducteca, product_id: int):
        endpoint_url = config.get_endpoint(f'{cls().endpoint}/{product_id}/listintegration')
        headers = config.headers
        response = requests.get(endpoint_url, headers=headers)
        return cls(config=config, **response.json()), response.status_code

# Modelo con campos extra de la vista Meli
class MeliCategory(BaseModel):
    meli_id: Optional[str] = Field(default=None, alias='meliId')
    accepts_mercadoenvios: Optional[bool] = Field(default=None, alias='acceptsMercadoenvios')
    suggest: Optional[bool] = None
    fixed: Optional[bool] = None

class Shipping(BaseModel):
    local_pickup: Optional[bool] = Field(default=None, alias='localPickup')
    mode: Optional[str] = None
    free_shipping: Optional[bool] = Field(default=None, alias='freeShipping')
    free_shipping_cost: Optional[float] = Field(default=None, alias='freeShippingCost')
    mandatory_free_shipping: Optional[bool] = Field(default=None, alias='mandatoryFreeShipping')
    free_shipping_method: Optional[str] = Field(default=None, alias='freeShippingMethod')

class MShopsShipping(BaseModel):
    enabled: Optional[bool] = None

class AttributeCompletion(BaseModel):
    product_identifier_status: Optional[str] = Field(default=None, alias='productIdentifierStatus')
    data_sheet_status: Optional[str] = Field(default=None, alias='dataSheetStatus')
    status: Optional[str] = None
    count: Optional[int] = None
    total: Optional[int] = None

class MeliProduct(Product):
    product_id: Optional[int] = Field(default=None, alias='productId')
    has_custom_shipping_costs: Optional[bool] = Field(default=None, alias='hasCustomShippingCosts')
    shipping: Optional[Shipping] = None
    mshops_shipping: Optional[MShopsShipping] = Field(default=None, alias='mShopsShipping')
    add_free_shipping_cost_to_price: Optional[bool] = Field(default=None, alias='addFreeShippingCostToPrice')
    category: Optional[MeliCategory] = None
    attribute_completion: Optional[AttributeCompletion] = Field(default=None, alias='attributeCompletion')
    catalog_products: Optional[List[str]] = Field(default=None, alias='catalogProducts')
    warranty: Optional[str] = None
    domain: Optional[str] = None
    listing_type_id: Optional[str] = Field(default=None, alias='listingTypeId')
    catalog_products_status: Optional[str] = Field(default=None, alias='catalogProductsStatus')

