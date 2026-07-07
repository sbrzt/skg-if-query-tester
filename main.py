import requests
import time
import json
import morph_kgc
import re
from tqdm import tqdm
from rdflib import Namespace

config = """
[Data]
mappings: mapping.yaml
"""


def extract_doi(id_string):
    if not id_string:
        return None
    m = re.search(r'doi:(\S+)', id_string)
    return m.group(1) if m else None


def extract_topics(record, doi):
    keywords = record.get("keywords")
    if keywords:
        topics = [
            {
                "label": keyword.get("text", "").lower(),
                "slug": re.sub(r"[^\w\s]", "", keyword.get("text", "").lower()).replace(" ", "-"),
                "related_doi": doi
            }
            for keyword in keywords
        ]
        return topics
    return None


def extract_authors(oc_meta, doi):
    if oc_meta:
        authors = oc_meta.get("author")
        if authors:
            split_authors = authors.split(";")
            authors_data = []
            for author in split_authors:
                author_orcid = re.search(r'orcid:(\S+)', author)
                author_full_name = author.split(" [")[0]
                if author_orcid:
                    author_data = {
                        "orcid": author_orcid.group(1),
                        "full_name": author_full_name,
                        "related_doi": doi
                    }
                    authors_data.append(author_data)
            return authors_data
        return None
    return None
    

def extract_citing_cited(opencitations_index, doi):
    citing_list = opencitations_index.get("citing", []) or []
    cited_list = opencitations_index.get("cited", []) or []
    citing_dois = [
        {"doi": d, "related_doi": doi} for c in citing_list
        if (d := extract_doi(c.get("citing")))
    ]
    cited_dois = [
        {"doi": d, "related_doi": doi} for c in cited_list
        if (d := extract_doi(c.get("cited")))
    ]
    return citing_dois, cited_dois


def main(target_size=500):
    gotriple_api_docs = "https://api.gotriple.eu/api/research-products?q=open%20science&size=1000&resource_type=document"
    gotriple_api_datasets = "https://api.gotriple.eu/api/research-products?q=open%20science&size=1000&resource_type=dataset"
    docs_data = requests.get(gotriple_api_docs).json().get("data", [])
    datasets_data = requests.get(gotriple_api_datasets).json().get("data", [])
    gotriple_records = docs_data + datasets_data
    merged_dataset = []
    for record in tqdm(gotriple_records):
        if len(merged_dataset) >= target_size:
            break
        resource_type = record.get("resource_type")
        doi_list = record.get("doi", [])
        if not doi_list:
            continue
        doi = doi_list[0]
        headline = record.get("headline") or []
        title = [t.get("text") for t in headline][0]
        date_issued = record.get("date_published", "")
        access = record.get("conditions_of_access")
        is_open_access = True if "acr_open-access" in access else False
        topics = extract_topics(record, doi)
        if "dataset" in resource_type:
            opencitations_index = {"citing": [], "cited": []}
            citing_dois, cited_dois = extract_citing_cited(opencitations_index, doi)
            merged_dataset.append({
                "doi": doi,
                "title": title,
                "date_issued": date_issued,
                "record_type": "dataset",
                "gotriple_meta": record,
                "opencitations_meta": {},
                "opencitations_index": opencitations_index,
                "citing_dois": citing_dois,
                "cited_dois": cited_dois,
                "authors": [],
                "topics": topics,
                "is_open_access": is_open_access
            })
            continue
        if not doi:
            continue
        oc_meta_api = f"https://api.opencitations.net/meta/v1/metadata/doi:{doi}"
        oc_meta_data = requests.get(oc_meta_api)
        if oc_meta_data.status_code == 200:
            opencitations_record = oc_meta_data.json()
            if len(opencitations_record) > 0:
                oc_index_api_citing = f"https://api.opencitations.net/index/v2/citations/doi:{doi}"
                oc_index_api_cited = f"https://api.opencitations.net/index/v2/references/doi:{doi}"
                resp_citing = requests.get(oc_index_api_citing)
                try:
                    oc_index_data_citing = resp_citing.json()
                except requests.exceptions.JSONDecodeError:
                    oc_index_data_citing = {}
                resp_cited = requests.get(oc_index_api_cited)
                try:
                    oc_index_data_cited = resp_cited.json()
                except requests.exceptions.JSONDecodeError:
                    oc_index_data_cited = {}
                opencitations_index = {
                    "citing": oc_index_data_citing,
                    "cited": oc_index_data_cited
                }
                citing_dois, cited_dois = extract_citing_cited(opencitations_index, doi)
                authors = extract_authors(opencitations_record[0], doi)
                merged_item = {
                    "doi": doi,
                    "title": title,
                    "date_issued": date_issued,
                    "record_type": "document",
                    "gotriple_meta": record,
                    "opencitations_meta": opencitations_record[0],
                    "opencitations_index": opencitations_index,
                    "citing_dois": citing_dois,
                    "cited_dois": cited_dois,
                    "authors": authors,
                    "topics": topics,
                    "is_open_access": is_open_access
                }
                merged_dataset.append(merged_item)
            
        time.sleep(0.1)
    with open("dataset.json", "w") as f:
        json.dump(merged_dataset, f, indent=2)

    graph = morph_kgc.materialize(config)
    prefixes = {
    "bido": "http://purl.org/spar/bido/",
    "fabio": "http://purl.org/spar/fabio/",
    "datacite": "http://purl.org/spar/datacite/",
    "dcterms": "http://purl.org/dc/terms/",
    "literal": "http://www.essepuntato.it/2010/06/literalreification/",
    "cito": "http://purl.org/spar/cito/",
    "foaf": "http://xmlns.com/foaf/0.1/",
    "frbr": "http://purl.org/vocab/frbr/core#",
    "pro": "http://purl.org/spar/pro/",
    "pso": "http://purl.org/spar/pso/",
    "skos": "http://www.w3.org/2004/02/skos/core#",
    }

    for prefix, uri in prefixes.items():
        graph.bind(prefix, Namespace(uri), override=True)
    graph.serialize(destination="dataset.ttl", format="turtle")

if __name__ == "__main__":
    main()
