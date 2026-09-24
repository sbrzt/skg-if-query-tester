from typing import Any
from tqdm import tqdm
import requests
from src.base import BaseSKGProvider
from src.providers import GoTripleProvider, OpenCitationsProvider

REGISTRY: dict[str, type[BaseSKGProvider]] = {
    "gotriple": GoTripleProvider,
    "opencitations": OpenCitationsProvider,
}


def build_providers(
    providers_config: list[dict[str, Any]],
    session: requests.Session,
    timeout: int = 8
    ) -> list[BaseSKGProvider]:

    instances = []
    for provider in tqdm(providers_config):
        if not provider.get("enabled", True):
            continue
        provider_name = provider.get("name").lower()
        provider_cls = REGISTRY.get(provider_name)
        if not provider_cls:
            raise ValueError(
                f"Provider {provider_name} unknown"
            )
        instances.append(provider_cls(name=provider_name, config=provider, session=session, timeout=timeout))
    return instances
