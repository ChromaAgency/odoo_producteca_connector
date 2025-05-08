from pydantic import BaseModel, PrivateAttr
from abc import ABC, abstractmethod


class APIConfig(BaseModel, ABC):
    base_url: str = 'https://api-external.producteca.com'

    @property
    @abstractmethod
    def headers(self) -> dict:
        pass

    def get_endpoint(self, endpoint: str) -> str:
        return f'{self.base_url}/{endpoint}'


class ConfigProducteca(APIConfig):
    token: str
    api_key: str

    @property
    def headers(self) -> dict:
        return {
            "Content-Type": "application/json",
            "authorization": f"Bearer {self.token}",
            "x-api-key": self.api_key,
            "Accept": "*/*"
        }
