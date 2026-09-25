import threading
from typing import Any
import requests
from src.base import BaseSKGProvider


class OpenAIREProvider(BaseSKGProvider):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._grants: dict[str, dict[str, Any] | None] = {}
        self._datasources: dict[str, dict[str, Any] | None] = {}
        self._lock = threading.Lock()

    def fetch_by_doi(
        self,
        doi: str
        ) -> dict[str, Any] | None:

        url = self.config.get("base_url") + self.config.get("endpoints").get("search")
        params = {"filter": f"identifiers.id:{doi},identifiers.scheme:doi", "page_size": 5}
        try:
            res = self.session.get(url, params=params, timeout=self.timeout)
            if res.status_code != 200:
                return None
            graph = res.json().get("@graph", [])
        except (requests.RequestException, ValueError):
            return None

        record = next(
            (p for p in graph
             if any(i.get("scheme") == "doi" and i.get("value", "").lower() == doi.lower()
                    for i in p.get("identifiers") or [])),
            None,
        )
        if not record:
            return None

        product_id = record.get("local_identifier", "").rstrip("/").rsplit("/", 1)[-1]
        self._scope_otf_identifiers(record, product_id)

        if record.get("funding"):
            record["funding"] = [self._fetch_grant(g) or g for g in record["funding"]]

        for manifestation in record.get("manifestations") or []:
            biblio = manifestation.get("biblio") or {}
            if isinstance(biblio.get("hosting_data_source"), dict):
                biblio["hosting_data_source"] = self._fetch_datasource(biblio["hosting_data_source"]) or biblio["hosting_data_source"]
        return record

    def _scope_otf_identifiers(self, node: Any, product_id: str) -> None:
        if isinstance(node, dict):
            lid = node.get("local_identifier")
            if isinstance(lid, str) and lid.startswith("otf___"):
                node["local_identifier"] = f"{product_id}::{lid.rsplit('___', 1)[-1]}"
            for value in node.values():
                self._scope_otf_identifiers(value, product_id)
        elif isinstance(node, list):
            for value in node:
                self._scope_otf_identifiers(value, product_id)

    def _fetch_grant(
        self,
        grant: dict[str, Any]
        ) -> dict[str, Any] | None:

        return self._fetch_entity(grant, "grant", self._grants)

    def _fetch_datasource(
        self,
        datasource: dict[str, Any]
        ) -> dict[str, Any] | None:

        return self._fetch_entity(datasource, "datasource", self._datasources)

    def _fetch_entity(
        self,
        entity: dict[str, Any],
        endpoint: str,
        cache: dict[str, dict[str, Any] | None]
        ) -> dict[str, Any] | None:

        lid = entity.get("local_identifier", "")
        if not lid:
            return None
        entity_id = lid.rstrip("/").rsplit("/", 1)[-1]
        with self._lock:
            if entity_id in cache:
                return cache[entity_id]

        url = self.config.get("base_url") + self.config.get("endpoints").get(endpoint).format(local_id=entity_id)
        full = None
        try:
            res = self.session.get(url, timeout=self.timeout)
            if res.status_code == 200:
                graph = res.json().get("@graph", [])
                full = graph[0] if graph else None
        except (requests.RequestException, ValueError):
            full = None
        if full:
            self._scope_otf_identifiers(full, entity_id)
        with self._lock:
            cache[entity_id] = full
        return full
