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
        # only required providers decide whether a record is kept
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
        """Complete already harvested records with the lookup providers they are missing."""
        with ThreadPoolExecutor(max_workers=self.workers) as executor:
            return list(tqdm(executor.map(self._lookup_missing, bundles), total=len(bundles)))

    def run(
        self,
        target_matches: int = 50,
        page_size: int = 100
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