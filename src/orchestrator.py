from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
from typing import Any
from src.base import BaseSKGProvider


class Harvester:
    
    def __init__(
        self,
        providers: list[BaseSKGProvider],
        policy_config: dict[str, Any],
        workers: int = 20,
        ):
        self.providers = providers
        self.policy_config = policy_config
        self.workers = workers
        self.streamers = [p for p in self.providers if "stream" in p.capabilities]
        self.lookups = [p for p in self.providers if "lookup" in p.capabilities]
        self.citers = [p for p in self.providers if "citations" in p.capabilities]
        if not self.streamers:
            raise ValueError(
                "No stream provider"
            )

    def _lookup_missing(
        self,
        bundle: dict[str, Any]
        ) -> dict[str, Any]:
        for p in self.lookups:
            if p.name in bundle["sources"]:
                continue
            data = p.fetch_by_doi(bundle["doi"])
            if data:
                bundle["sources"][p.name] = data
        return bundle

    def _enrich_single_doi(
        self,
        doi: str,
        initial_source: str,
        initial_data: dict[str, Any]
        ) -> dict[str, Any] | None:
        bundle = self._lookup_missing({
            "doi": doi,
            "sources": {
                initial_source: initial_data
            }
        })
        required = {l.name for l in self.lookups if l.required} | {initial_source}
        matched = required & bundle["sources"].keys()
        mode = self.policy_config.get("mode", "all")
        if mode == "all" and matched == required:
            return bundle
        if mode == "any" and len(matched) > 1:
            return bundle
        return None

    def enrich(
        self,
        bundles: list[dict[str, Any]]
        ) -> list[dict[str, Any]]:
        main = [b for b in bundles if not b.get("context")]
        with ThreadPoolExecutor(max_workers=self.workers) as executor:
            list(tqdm(executor.map(self._lookup_missing, main), total=len(main)))
        return self.add_citations(bundles)

    def _fetch_citations(
        self,
        bundle: dict[str, Any]
        ) -> list[tuple[BaseSKGProvider, dict[str, Any]]]:
        found = []
        for p in self.citers:
            record = bundle["sources"].get(p.name)
            if record and p.name not in bundle.get("citations_from", []):
                products = p.fetch_citations(record)
                if products is None:  # failed: retried by the next run
                    continue
                found.extend((p, product) for product in products)
                bundle.setdefault("citations_from", []).append(p.name)
        return found

    def add_citations(
        self,
        bundles: list[dict[str, Any]]
        ) -> list[dict[str, Any]]:
        if not self.citers:
            return bundles
        known = {
            record.get("local_identifier")
            for b in bundles for record in b["sources"].values()
        }
        main = [b for b in bundles if not b.get("context")]
        with ThreadPoolExecutor(max_workers=self.workers) as executor:
            found = list(tqdm(executor.map(self._fetch_citations, main), total=len(main)))
        for provider, product in (pair for pairs in found for pair in pairs):
            if product.get("local_identifier") in known:
                continue
            known.add(product.get("local_identifier"))
            bundles.append({
                "doi": provider.extract_doi(product),
                "context": "citation",
                "sources": {provider.name: product},
            })
        return bundles

    def run(
        self,
        target_matches: int = 50,
        page_size: int = 100
        ) -> list[dict[str, Any]]:
        return self.add_citations(self._harvest(target_matches, page_size))

    def _harvest(
        self,
        target_matches: int,
        page_size: int
        ) -> list[dict[str, Any]]:
        materialized: list[dict[str, Any]] = []
        seen_dois: set[str] = set()

        with ThreadPoolExecutor(max_workers=self.workers) as executor:
            for streamer in tqdm(self.streamers):
                for record in tqdm(streamer.stream_records(page_size=page_size)):
                    doi = streamer.extract_doi(record)
                    if not doi or doi in seen_dois:
                        continue
                    seen_dois.add(doi)

                    future = executor.submit(
                        self._enrich_single_doi, doi, streamer.name, record
                    )
                    res = future.result()
                    if res:
                        materialized.append(res)
                        if len(materialized) >= target_matches:
                            return materialized
        return materialized