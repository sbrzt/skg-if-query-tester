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

    def extract_doi(
        self,
        record: dict[str, Any]
        ) -> str | None:
        for ident in record.get("identifiers") or []:
            if ident.get("scheme", "").lower() == "doi" and ident.get("value"):
                return ident["value"].strip()
        return None

    def fetch_citations(
        self,
        record: dict[str, Any]
        ) -> list[dict[str, Any]] | None:

        local_id = record.get("local_identifier")
        if not local_id:
            return []
        url = self.config.get("base_url") + self.config.get("endpoints").get("search")
        page_size = self.config.get("citations_page_size", 100)
        products = []
        for filter_template in self.config.get("citation_filters", {}).values():
            page = 1
            while True:
                params = {"filter": filter_template.format(local_id=local_id), "page_size": page_size, "page": page}
                body = self._get_json(url, params)
                if body is None:
                    return None
                graph = body.get("@graph", [])
                products.extend(graph)
                if len(graph) < page_size or not (body.get("meta") or {}).get("next_page"):
                    break
                page += 1
        return products

    def _get_json(
        self,
        url: str,
        params: dict[str, Any]
        ) -> dict[str, Any] | None:
        # the citation searches sometimes fail on the server side (e.g. 504): retry them
        for _ in range(1 + self.config.get("retries", 2)):
            try:
                res = self.session.get(url, params=params, timeout=self.timeout)
                if res.status_code == 200:
                    return res.json()
                if res.status_code < 500:
                    return None
            except (requests.RequestException, ValueError):
                pass
        return None
