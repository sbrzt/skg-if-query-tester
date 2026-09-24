import re
from typing import Any
import requests
from src.base import BaseSKGProvider


class OpenCitationsProvider(BaseSKGProvider):
    
    def fetch_by_doi(
        self, 
        doi: str
        ) -> dict[str, Any] | None:
        
        resolver = self.config.get("base_url") + self.config.get("endpoints").get("resolver")
        resolver_url = resolver.format(doi=doi)

        try:
            res_meta = self.session.get(resolver_url, timeout=self.timeout)
            if res_meta.status_code != 200 or not res_meta.json():
                return None
            match = re.search(r"omid:(\S+)", res_meta.json()[0].get("id", ""))
            if not match:
                return None
            local_id = match.group(1)
            record = self.config.get("base_url") + self.config.get("endpoints").get("record")
            record_url = record.format(local_id=local_id)
            res_skg = self.session.get(record_url, timeout=self.timeout)
            if res_skg.status_code != 200:
                return None
            graph = res_skg.json().get("@graph", [])
            return graph[0] if graph else None
        except requests.RequestException:
            return None