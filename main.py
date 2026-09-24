import pathlib
import json
import requests
import yaml
from src import Harvester, build_providers


def main():

    root = pathlib.Path(__file__).parent
    with open(root / "config.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    
    session = requests.Session()
    session.headers.update(config.get("http").get("headers"))

    providers = build_providers(
        providers_config=config.get("providers"),
        session=session,
        timeout=config.get("execution").get("timeout")
    )
    
    harvester = Harvester(
        providers=providers,
        policy_config=config.get("matching_policy"),
        workers=config.get("execution").get("workers")
    )

    results = harvester.run(
        target_matches=config.get("execution").get("target_matches"),
        page_size=config.get("execution").get("stream_batch_size"),
    )

    output_path = root / config.get("execution").get("output_path")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

                    
if __name__ == "__main__":
    main()