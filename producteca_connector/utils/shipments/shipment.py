from typing import List, Optional
from pydantic import BaseModel
import requests
from ..config.config import ConfigProducteca


class ShipmentProduct(BaseModel):
    product: int
    variation: Optional[int] = None
    quantity: int


class ShipmentMethod(BaseModel):
    trackingNumber: Optional[str] = None
    trackingUrl: Optional[str] = None
    courier: str
    mode: Optional[str] = None
    cost: float
    type: Optional[str] = None
    eta: Optional[str] = None
    status: str


class ShipmentIntegration(BaseModel):
    id: Optional[int] = None
    integrationId: Optional[str] = None
    app: Optional[int] = None
    status: str


class Shipment(BaseModel):
    date: str
    products: List[ShipmentProduct]
    method: ShipmentMethod
    integration: Optional[ShipmentIntegration] = None

    @classmethod
    def create(cls, config: ConfigProducteca, sale_order_id: int, payload: "Shipment") -> "Shipment":
        url = config.get_endpoint(f"salesorders/{sale_order_id}/shipments")
        res = requests.post(url, data=payload.model_dump_json(exclude_none=True), headers=config.headers)
        return cls(**res.json())

    @classmethod
    def update(cls, config: ConfigProducteca, sale_order_id: int, shipment_id: str, payload: "Shipment") -> "Shipment":
        url = config.get_endpoint(f"salesorders/{sale_order_id}/shipments/{shipment_id}")
        res = requests.put(url, data=payload.model_dump_json(exclude_none=True), headers=config.headers)
        return cls(**res.json())