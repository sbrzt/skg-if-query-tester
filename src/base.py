from abc import ABC, abstractmethod
from typing import Any, Generator
import requests


class BaseSKGProvider(ABC):
    def __init__(
        self,
        name: str,
        config: dict[str, Any],
        session: requests.Session,
        timeout: int = 8,
    ):
        self.name = name
        self.config = config
        self.session = session
        self.timeout = timeout
        self.capabilities = {
            c.lower() for c in config.get("capabilities", [])
        }

    def stream_records(
        self, 
        page_size: int = 100
        ) -> Generator[dict[str, Any], None, None]:
        raise NotImplementedError()
    
    def extract_doi(
        self, 
        record: dict[str, Any]
        ) -> str | None:
        return None

    def fetch_by_doi(
        self, 
        doi: str
        ) -> dict[str, Any] | None:
        raise NotImplementedError()