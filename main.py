import requests
import time
import json
from tqdm import tqdm


def main(target_size=500):
    gotriple_api = "https://api.gotriple.eu/api/research-products?q=open%20science&size=100&resource_type=document"
    gotriple_data = requests.get(gotriple_api).json()
    gotriple_records = gotriple_data.get("data", [])
    merged_dataset = []
    unique_author_ids = set()
    for record in tqdm(gotriple_records):
        if len(merged_dataset) >= target_size:
            break
        doi_list = record.get("doi", [])
        if not doi_list:
            continue
        doi = doi_list[0]
        opencitations_api = f"https://api.opencitations.net/meta/v1/metadata/doi:{doi}"
        opencitations_data = requests.get(opencitations_api)
        if opencitations_data.status_code == 200:
            opencitations_record = opencitations_data.json()
            if len(opencitations_record) > 0:
                merged_item = {
                    "doi": doi,
                    "gotriple_meta": record,
                    "opencitations_meta": opencitations_record[0]
                }
                merged_dataset.append(merged_item)
                for author in record.get("author", []):
                    author_id = author.get("id")
                    if author_id:
                        unique_author_ids.add(author_id)
        time.sleep(0.1)
    with open("dataset.json", "w") as f:
        json.dump(merged_dataset, f, indent=2)
    
    authors_dataset = {}
    for author_id in unique_author_ids:
        author_api = f"https://api.gotriple.eu/api/authors/{author_id}"
        try:
            author_resp = requests.get(author_api)
            if author_resp.status_code == 200:
                authors_dataset[author_id] = author_resp.json()
        except Exception as e:
            print("error")
        time.sleep(0.1)
    with open("authors.json", "w") as f:
        json.dump(authors_dataset, f, indent=2)

if __name__ == "__main__":
    main()
