import argparse
import pathlib
import json
import requests
import yaml
from src import Harvester, build_providers


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--enrich",
        action="store_true",
        help="complete the records already in the output file with the lookup providers they are missing, instead of harvesting new ones",
    )
    args = parser.parse_args()

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

    output_path = root / config.get("execution").get("output_path")
    if args.enrich:
        with open(output_path, "r", encoding="utf-8") as f:
            results = harvester.enrich(json.load(f))
    else:
        results = harvester.run(
            target_matches=config.get("execution").get("target_matches"),
            page_size=config.get("execution").get("stream_batch_size"),
        )

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

                    
if __name__ == "__main__":
    main()