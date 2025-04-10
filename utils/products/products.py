from dataclasses import dataclass, field
from dataclasses_json import dataclass_json, config
import requests
from ..abstract.abstract_dataclass import AbstractProductecaV1Dataclass
from ..config.config import ConfigProducteca
from typing import List


@dataclass_json
@dataclass
class Component(AbstractProductecaV1Dataclass):
    quantity: int = field(default=None, metadata=config(exclude=lambda x: not x))
    variationId: int = field(default=None, metadata=config(exclude=lambda x: not x))
    productId: int = field(default=None, metadata=config(exclude=lambda x: not x))

@dataclass_json
@dataclass
class Variation(AbstractProductecaV1Dataclass):
    variationId: int = field(default=None, metadata=config(exclude=lambda x: not x))
    components: List[Component] = field(default=None, metadata=config(exclude=lambda x: not x))
    pictures: List['Pictures'] = field(default=None, metadata=config(exclude=lambda x: not x))
    stocks: List['Stocks'] = field(default=None, metadata=config(exclude=lambda x: not x))
    attributesHash: str = field(default=None, metadata=config(exclude=lambda x: not x))
    primaryColor: str = field(default=None, metadata=config(exclude=lambda x: not x))
    thumbnail: str = field(default=None, metadata=config(exclude=lambda x: not x))
    attributes: List['Attributes'] = field(default=None, metadata=config(exclude=lambda x: not x))
    integrations: List['Integrations'] = field(default=None, metadata=config(exclude=lambda x: not x))
    id: int = field(default=None, metadata=config(exclude=lambda x: not x))
    sku: str = field(default=None, metadata=config(exclude=lambda x: not x))
    barcode: str = field(default=None, metadata=config(exclude=lambda x: not x))

@dataclass_json
@dataclass
class ResultItem(AbstractProductecaV1Dataclass):
    companyId: int = field(default=None, metadata=config(exclude=lambda x: not x))
    productId: int = field(default=None, metadata=config(exclude=lambda x: not x))
    variations: List[Variation] = field(default=None, metadata=config(exclude=lambda x: not x))
    id: str = field(default=None, metadata=config(exclude=lambda x: not x))

@dataclass_json
@dataclass
class ResultsResponse(AbstractProductecaV1Dataclass):
    results: List[ResultItem] = field(default=None, metadata=config(exclude=lambda x: not x))
    count: int = field(default=None, metadata=config(exclude=lambda x: not x))

@dataclass_json
@dataclass
class Integrations(AbstractProductecaV1Dataclass):
    app: int = field(default=None, metadata=config(exclude=lambda x: not x))
    integrationId: str = field(default=None, metadata=config(exclude=lambda x: not x))
    permalink: str = field(default=None, metadata=config(exclude=lambda x: not x))
    status: str = field(default=None, metadata=config(exclude=lambda x: not x))
    listingType: str = field(default=None, metadata=config(exclude=lambda x: not x))
    safetyStock: int = field(default=None, metadata=config(exclude=lambda x: not x))
    synchronizeStock: bool = field(default=None, metadata=config(exclude=lambda x: not x))
    isActive: bool = field(default=None, metadata=config(exclude=lambda x: not x))
    isActiveOrPaused: bool = field(default=None, metadata=config(exclude=lambda x: not x))
    id: int = field(default=None, metadata=config(exclude=lambda x: not x))
    parentIntegration: str = field(default=None, metadata=config(exclude=lambda x: not x))

@dataclass_json
@dataclass
class Stocks(AbstractProductecaV1Dataclass):
    quantity: int = field(default=None, metadata=config(exclude=lambda x: not x))
    availableQuantity: int = field(default=None, metadata=config(exclude=lambda x: not x))
    warehouse: str = ''
    warehouseId: int = field(default=None, metadata=config(exclude=lambda x: not x))
    reserved: int = field(default=None, metadata=config(exclude=lambda x: not x))
    available: int = field(default=None, metadata=config(exclude=lambda x: not x))

@dataclass_json
@dataclass
class Prices(AbstractProductecaV1Dataclass):
    amount: float = field(default=None, metadata=config(exclude=lambda x: not x))
    currency: str = ''
    priceList: str = ''
    priceListId: int = field(default=None, metadata=config(exclude=lambda x: not x))

@dataclass_json
@dataclass
class Pictures(AbstractProductecaV1Dataclass):
    url: str = ''

@dataclass_json
@dataclass
class Attributes(AbstractProductecaV1Dataclass):
    key: str = ''
    value: str = ''

@dataclass_json
@dataclass
class Tags(AbstractProductecaV1Dataclass):
    tag: str = ''

@dataclass_json
@dataclass
class Shipping(AbstractProductecaV1Dataclass):
    localPickup: bool = field(default=None, metadata=config(exclude=lambda x: not x))
    mode: str = field(default=None, metadata=config(exclude=lambda x: not x))
    freeShipping: bool = field(default=None, metadata=config(exclude=lambda x: not x))
    freeShippingCost: float = field(default=None, metadata=config(exclude=lambda x: not x))
    mandatoryFreeShipping: bool = field(default=None, metadata=config(exclude=lambda x: not x))
    freeShippingMethod: str = field(default=None, metadata=config(exclude=lambda x: not x))

@dataclass_json
@dataclass
class MShopsShipping(AbstractProductecaV1Dataclass):
    enabled: bool = field(default=None, metadata=config(exclude=lambda x: not x))

@dataclass_json
@dataclass
class Category(AbstractProductecaV1Dataclass):
    meliId: str = field(default=None, metadata=config(exclude=lambda x: not x))
    acceptsMercadoenvios: bool = field(default=None, metadata=config(exclude=lambda x: not x))
    suggest: bool = field(default=None, metadata=config(exclude=lambda x: not x))
    fixed: bool = field(default=None, metadata=config(exclude=lambda x: not x))

@dataclass_json
@dataclass
class AttributeCompletion(AbstractProductecaV1Dataclass):
    productIdentifierStatus: str = field(default=None, metadata=config(exclude=lambda x: not x))
    dataSheetStatus: str = field(default=None, metadata=config(exclude=lambda x: not x))
    status: str = field(default=None, metadata=config(exclude=lambda x: not x))
    count: int = field(default=None, metadata=config(exclude=lambda x: not x))
    total: int = field(default=None, metadata=config(exclude=lambda x: not x))

@dataclass_json
@dataclass
class Deals(AbstractProductecaV1Dataclass):
    campaign: str = ''
    regularPrice: float = None
    dealPrice: float = None

@dataclass_json
@dataclass
class Products(AbstractProductecaV1Dataclass):
    create_if_not_exist: bool = False
    product_id: int = None
    sku: str = ''
    variationId: int = None
    code: str = ''
    name: str = ''
    barcode: str = ''
    attributes: List[Attributes] = field(default_factory=list)
    tags: List[Tags] = field(default_factory=list)
    buyingPrice: float = None
    dimensions: dict = None
    category: Category = field(default=None, metadata=config(exclude=lambda x: not x))
    brand: str = ''
    notes: str = ''
    deals: List[Deals] = field(default_factory=list)
    stocks: List[Stocks] = field(default_factory=list)
    prices: List[Prices] = field(default_factory=list)
    pictures: List[Pictures] = field(default_factory=list)
    endpoint: str = field(default='products', metadata=config(exclude=lambda x: True))
    

    integrations: List[Integrations] = field(default=None, metadata=config(exclude=lambda x: not x))
    variations: List[Variation] = field(default=None, metadata=config(exclude=lambda x: not x))
    isSimple: bool = field(default=None, metadata=config(exclude=lambda x: not x))
    hasVariations: bool = field(default=None, metadata=config(exclude=lambda x: not x))
    thumbnail: str = field(default=None, metadata=config(exclude=lambda x: not x))
    isArchived: bool = field(default=None, metadata=config(exclude=lambda x: not x))
    metadata: List[str] = field(default=None, metadata=config(exclude=lambda x: not x))
    isOriginal: bool = field(default=None, metadata=config(exclude=lambda x: not x))
    id: int = field(default=None, metadata=config(exclude=lambda x: not x))
    attributesHash: str = field(default=None, metadata=config(exclude=lambda x: not x))
    primaryColor: str = field(default=None, metadata=config(exclude=lambda x: not x))
    hasCustomShippingCosts: bool = field(default=None, metadata=config(exclude=lambda x: not x))
    productId: int = field(default=None, metadata=config(exclude=lambda x: not x))
    shipping: Shipping = field(default=None, metadata=config(exclude=lambda x: not x))
    mShopsShipping: MShopsShipping = field(default=None, metadata=config(exclude=lambda x: not x))
    addFreeShippingCostToPrice: bool = field(default=None, metadata=config(exclude=lambda x: not x))
    attributeCompletion: AttributeCompletion = field(default=None, metadata=config(exclude=lambda x: not x))
    catalogProducts: List[str] = field(default=None, metadata=config(exclude=lambda x: not x))
    warranty: str = field(default=None, metadata=config(exclude=lambda x: not x))
    domain: str = field(default=None, metadata=config(exclude=lambda x: not x))
    listingTypeId: str = field(default=None, metadata=config(exclude=lambda x: not x))
    catalogProductsStatus: str = field(default=None, metadata=config(exclude=lambda x: not x))
    tags_list: List[str] = field(default=None, metadata=config(exclude=lambda x: not x))

    def create(self):
        endpoint_url = self.config.get_endpoint(f'{self.endpoint}/synchronize')
        headers = self.config.headers.update({"createifitdoesntexist": self.create_if_not_exist})
        response = requests.post(endpoint_url, data=self.to_json(), headers=headers)
        return response
        
    @classmethod
    def get(cls, config:ConfigProducteca, product_id:int):
        endpoint_url = config.get_endpoint(f'{cls.endpoint}/{str(product_id)}')
        headers = config.headers
        response = requests.get(endpoint_url, headers=headers)
        return cls.from_dict({"config":config, **response.json()})
        
    @classmethod
    def get_bundle(cls, config:ConfigProducteca, product_id:int):
        endpoint_url = config.get_endpoint(f'{cls.endpoint}/{str(product_id)}/bundles')
        headers = config.headers
        response = requests.get(endpoint_url, headers=headers)
        return cls.from_dict({"config":config, **response.json()})

    @classmethod
    def get_ml_integration(cls, config:ConfigProducteca, product_id:int):
        endpoint_url = config.get_endpoint(f'{cls.endpoint}/{str(product_id)}/listintegration')
        headers = config.headers
        response = requests.get(endpoint_url, headers=headers)
        return cls.from_dict({"config":config, **response.json()})
        
