from pydantic import BaseModel
from typing import Optional
import requests
from ..config.config import ConfigProducteca


class PaymentCard(BaseModel):
    paymentNetwork: str
    firstSixDigits: int
    lastFourDigits: int
    cardholderIdentificationNumber: str
    cardholderIdentificationType: str
    cardholderName: str


class PaymentIntegration(BaseModel):
    integrationId: str
    app: int


class Payment(BaseModel):
    date: str
    amount: float
    couponAmount: float
    status: str
    method: str
    integration: PaymentIntegration
    transactionFee: float
    installments: int
    card: Optional[PaymentCard] = None
    notes: Optional[str] = None
    hasCancelableStatus: bool
    id: int

    @classmethod
    def create(cls, config: ConfigProducteca, sale_order_id: int, payload: "Payment") -> "Payment":
        url = config.get_endpoint(f"salesorders/{sale_order_id}/payments")
        res = requests.post(url, data=payload.model_dump_json(exclude_none=True), headers=config.headers)
        return cls(**res.json())

    @classmethod
    def update(cls, config: ConfigProducteca, sale_order_id: int, payment_id: int, payload: "Payment") -> "Payment":
        url = config.get_endpoint(f"salesorders/{sale_order_id}/payments/{payment_id}")
        res = requests.put(url, data=payload.model_dump_json(exclude_none=True), headers=config.headers)
        return cls(**res.json())
