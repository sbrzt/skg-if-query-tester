from typing import Any, Generator
import requests
from src.base import BaseSKGProvider


class GoTripleProvider(BaseSKGProvider):

    def stream_records(
        self, 
        page_size: int = 100
        ) -> Generator[dict[str, Any], None, None]:
        
        url = self.config.get("base_url") + self.config.get("endpoints").get("stream")
        page = 1
        while True:
            params = {"size": page_size, "page": page}
            try:
                res = self.session.get(url, params=params, timeout=self.timeout)
                if res.status_code != 200:
                    break
                results = res.json().get("results", [])
                if not results:
                    break
                for rec in results:
                    yield rec
                page += 1
            except requests.RequestException:
                break

    def extract_doi(
        self, 
        record: dict[str, Any]
        ) -> str | None:
        for ident in record.get("identifiers", []):
            scheme = ident.get("scheme", "").lower()
            val = ident.get("value", "").strip()
            if scheme == "doi":
                return val
        return None