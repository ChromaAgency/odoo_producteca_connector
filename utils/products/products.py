from dataclasses import dataclass, field
from dataclasses_json import dataclass_json, config
@dataclass_json
@dataclass
class Deals:
    campaign: str = ''
    regularPrice: float = None
    dealPrice: float = None

@dataclass_json
@dataclass
class Stocks:
    quantity: int = None
    availableQuantity: int = None
    warehouse: str = ''

@dataclass_json
@dataclass
class Prices:
    amount: float = None
    currency: str = ''
    priceList: str = ''

@dataclass_json
@dataclass
class Pictures:
    url: str = ''

@dataclass_json
@dataclass
class Attributes:
    key: str = ''
    value: str = ''

@dataclass_json
@dataclass
class Tags:
    tag: str = ''

@dataclass_json
@dataclass
class Products:
    create_if_not_exist: bool = False
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



# from dataclasses import asdict, dataclass, field
# from typing import List
# import json

# from simpliroute.abstract.abstract_dataclass import  AbstractSimplirouteV1Dataclass
# from simpliroute.config.config import ConfigV1   
# import requests
# from dataclasses_json import dataclass_json, config
# from simpliroute.items.item import Item
# from simpliroute.properties.properties import Property

# @dataclass_json
# @dataclass
# class Visit(AbstractSimplirouteV1Dataclass):
#     title: str
#     address: str
#     reference: str
#     window_start: None
#     window_end: None
#     load: float
#     duration: str
#     contact_name: str
#     contact_phone: str
#     notes: str
#     planned_date: str
#     properties: Property = None
    
#     id: int = None
#     on_its_way: None = None
#     items:List[Item] = field(default_factory=list) 
#     endpoint:str = field(default='routes/visits', metadata=config(exclude=lambda x: True))
#     order: None = None
#     tracking_id: str = ''
#     status: str = field(default='', metadata=config(exclude=lambda x: not x))
#     latitude: str = field(default='', metadata=config(exclude=lambda x: not x))
#     longitude: str = field(default='', metadata=config(exclude=lambda x: not x))
#     load_2: float = field(default=None, metadata=config(exclude=lambda x: not x))
#     load_3: float = field(default=None, metadata=config(exclude=lambda x: not x))
#     window_start_2: None = None
#     window_end_2: None = None
#     contact_email: None = None
#     skills_required: list = field(default_factory=list)
#     skills_optional: list = field(default_factory=list)
#     tags: list = field(default_factory=list)
#     programmed_date: None = None
#     route: None = None
#     estimated_time_arrival: None = None
#     estimated_time_departure: None = None
#     checkin_time: None = None
#     checkout_time: None = None
#     checkout_latitude: None = None
#     checkout_longitude: None = None
#     checkout_comment: str = ''
#     checkout_observation: None = None
#     signature: None = None
#     pictures: list = field(default_factory=list)
#     created: str = ''
#     modified: str = ''
#     eta_predicted: str = ''
#     eta_current: str = ''
#     priority: bool = False
#     has_alert: bool = False
#     priority_level: None = None
#     extra_field_values: None = field(default=None, metadata=config(exclude=lambda x: not x))
#     geocode_alert: None = None
#     visit_type: None = 'E'
#     current_eta: None = None
#     fleet: None = None

    
#     def create(self):
#         response = requests.post(f'{self.endpoint_url}/', data=self.to_json(), headers=self.config.headers)
#         # if not response.ok:
#         #     raise Exception(f'Response fail: {response.text}')
#         # self.id = response.json()['id']
#         return response
        
    
#     @classmethod    
#     def update(cls, config:ConfigV1, visit_id:str, update_data:dict):
#         update_url = config.get_endpoint(f"{cls.endpoint}/{visit_id}/")
#         response = requests.put(update_url,json=update_data, headers=config.headers)
#         return response

#     @classmethod
#     def delete(cls, config:ConfigV1, visit_id:str):
#         delete_url = config.get_endpoint(f"{cls.endpoint}/{visit_id}/")
#         response = requests.delete(delete_url, headers=config.headers)
#         return response
    
#     @classmethod
#     def get(cls, config:ConfigV1, visit_id:str) -> 'Visit':
#         response = requests.get(config.get_endpoint(f"{cls.endpoint}/{visit_id}"), headers=config.headers)        
#         return cls.from_dict({"config":config, **response.json()})
    
#     @classmethod    
#     def update_items(cls, config:ConfigV1, visit_id:str, items:Item):
#         update_url = config.get_endpoint(f"{cls.endpoint}/{visit_id}/items")
#         response = requests.put(update_url,json=items, headers=config.headers)
#         return response