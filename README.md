---
Title: SKG-IF Query Tester
Authors: Sebastian Barzaghi (https://orcid.org/0000-0002-0799-1527)
Release: 2026-07-17
Revision: 1.0.0
License: ISC License
---

# SKG-IF Query Tester

## Description

An ETL pipeline for building a scholarly knowledge graph for testing from data extracted from the GoTriple, OpenCitations and OpenAIRE SKG-IF APIs.

First, it fetches bibliographic data from external APIs in JSON format and converts it into RDF triples using declarative mapping rules.

Then, it generates a structured knowledge graph that models relationships between publications, datasets, authors, and identifiers using the SKG-IF model, based on standard Semantic Web ontologies (such as FABIO, DataCite, and PRO).

Finally, it tests the knowledge graph against a set of Competency Questions expressed as SPARQL queries.

## How to run

First install [uv](https://docs.astral.sh/uv/):

```bash
wget -qO- https://astral.sh/uv/install.sh | sh
```

Then run the orchestrator:

```bash
uv run main.py
```

Providers are configured in `config.yaml`. Products are streamed from GoTriple and looked up by DOI in the other providers; a provider with `required: false` (OpenAIRE, which also resolves the grants in `funding` and the data sources in `hosting_data_source`) enriches the records it knows without causing any record to be dropped.

To complete an existing `data.json` with the providers it is missing (e.g. after adding a new one) without harvesting new records:

```bash
uv run main.py --enrich
```

A provider with the `citations` capability (OpenCitations) also adds, for each harvested product, the products citing it and cited by it, through the SKG-IF citation filters (`citation_filters` in `config.yaml`). They are stored in `data.json` as single-source records marked with `"context": "citation"`, so that citations can be resolved (e.g. the DOIs and types of cited works) without enriching these products with the other providers. The citation searches are slow (up to minutes per product): a search that fails is not recorded as done, so running `uv run main.py --enrich` again retries it.

Finally, build the knowledge graph (`data.ttl`) from `data.json` with `mapping.yaml`:

```bash
uv run materialize.py
```

The same product, contributor, venue, data source and topic coming from several providers is materialized once: works are matched by DOI (DOIs are lowercased, as they are case-insensitive), contributors by name within the same work and role, venues by ISSN, data sources by any shared identifier (e.g. re3data, FAIRsharing DOI), topics by term. When providers disagree on a single-valued field, OpenCitations wins over OpenAIRE, which wins over GoTriple.

### Competency questions

Each competency question is a SPARQL query in its own file in `cqs/` (e.g. `cqs/CQ_001.rq`), headed by comment lines with its identifier and the question in natural language:

```sparql
# id: CQ_014
# question:
#   What are the topics and scientific domains covered in these graphs?

PREFIX ...
SELECT ...
```

To add a competency question, add a new `.rq` file. To run them all against `data.ttl`:

```bash
uv run run_cqs.py
```

Each result is printed as a table and the full results are written to `cq_results.json`, together with the status of each competency question (`answered`, `empty` or `error`). Use `--only CQ_001 CQ_014` to run some of them, `--data` to query another Turtle file, and `--strict` to exit with an error when a competency question has no results (the command always fails when a query is malformed).
