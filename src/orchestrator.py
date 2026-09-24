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

    def _enrich_single_doi(
        self,
        doi: str,
        initial_source: str,
        initial_data: dict[str, Any]
        ) -> dict[str, Any] | None:
        bundle: dict[str, Any] = {
            "doi": doi,
            "sources": {
                initial_source: initial_data
            }
        }
        for p in tqdm(self.lookups):
            if p.name == initial_source:
                continue
            data = p.fetch_by_doi(doi)
            if data:
                bundle["sources"][p.name] = data
        mode = self.policy_config.get("mode", "all")
        matched_count = len(bundle["sources"])
        required_count = len(self.lookups) + (
            1 if initial_source not in [l.name for l in self.lookups] else 0
        )
        if mode == "all" and matched_count >= required_count:
            return bundle
        if mode == "any" and matched_count > 1:
            return bundle
        return None

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