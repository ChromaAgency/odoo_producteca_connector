from typing import List
from pydantic import BaseModel
import requests
from ..config.config import ConfigProducteca


class ShipmentProduct(BaseModel):
    product: int
    variation: int
    quantity: int


class ShipmentMethod(BaseModel):
    trackingNumber: str
    trackingUrl: str
    courier: str
    mode: str
    cost: float
    type: str
    eta: str
    status: str


class ShipmentIntegration(BaseModel):
    id: int
    integrationId: str
    app: int
    status: str


class Shipment(BaseModel):
    date: str
    products: List[ShipmentProduct]
    method: ShipmentMethod
    integration: ShipmentIntegration

    @classmethod
    def create(cls, config: ConfigProducteca, sale_order_id: int, payload: "Shipment") -> "Shipment":
        url = config.get_endpoint(f"salesorders/{sale_order_id}/shipments")
        res = requests.post(url, data=payload.model_dump_json(exclude_none=True), headers=config.headers)
        return cls(**res.json())

    @classmethod
    def update(cls, config: ConfigProducteca, sale_order_id: int, shipment_id: int, payload: "Shipment") -> "Shipment":
        url = config.get_endpoint(f"salesorders/{sale_order_id}/shipments/{shipment_id}")
        res = requests.put(url, data=payload.model_dump_json(exclude_none=True), headers=config.headers)
        return cls(**res.json())