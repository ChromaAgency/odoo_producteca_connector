from dataclasses import dataclass, field
from dataclasses_json import dataclass_json, config
import requests
from ..abstract.abstract_dataclass import AbstractProductecaV1Dataclass
@dataclass_json
@dataclass
class Deals(AbstractProductecaV1Dataclass):
    campaign: str = ''
    regularPrice: float = None
    dealPrice: float = None

@dataclass_json
@dataclass
class Stocks(AbstractProductecaV1Dataclass):
    quantity: int = None
    availableQuantity: int = None
    warehouse: str = ''

@dataclass_json
@dataclass
class Prices(AbstractProductecaV1Dataclass):
    amount: float = None
    currency: str = ''
    priceList: str = ''

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
class Products(AbstractProductecaV1Dataclass):
    create_if_not_exist: bool = False
    product_id: int = None
    sku: str = ''
    variationId: int = None
    code: str = ''
    name: str = ''
    barcode: str = ''
    attributes: list[Attributes] = field(default_factory=list)
    tags: list[Tags] = field(default_factory=list)
    buyingPrice: float = None
    dimensions: dict = None
    category: str = ''
    brand: str = ''
    notes: str = ''
    deals: list[Deals] = field(default_factory=list)
    stocks: list[Stocks] = field(default_factory=list)
    prices: list[Prices] = field(default_factory=list)
    pictures: list[Pictures] = field(default_factory=list)
    endpoint:str = field(default='products/', metadata=config(exclude=lambda x: True))

    def create(self):
        endpoint_url = f'{self.endpoint}/{str(self.product_id)}'
        headers = self.config.headers.copy()
        headers.update({"createifitdoesntexist": self.create_if_not_exist})
        response = requests.post(endpoint_url, data=self.to_json(), headers=headers)
        return response
        
