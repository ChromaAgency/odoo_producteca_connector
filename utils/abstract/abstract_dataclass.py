from pydantic import BaseModel, PrivateAttr
from abc import ABC, abstractmethod
from ..config.config import ConfigProducteca, APIConfig


class AbstractProductecaModel(BaseModel, ABC):
    _config: APIConfig = PrivateAttr()

    @property
    @abstractmethod
    def endpoint(self) -> str:
        pass

    def dict(self, *args, **kwargs):
        return super().dict(*args, exclude_none=True, **kwargs)


class AbstractProductecaV1Model(AbstractProductecaModel):
    _config: ConfigProducteca = PrivateAttr()

    @property
    def endpoint_url(self) -> str:
        return self._config.get_endpoint(self.endpoint)
