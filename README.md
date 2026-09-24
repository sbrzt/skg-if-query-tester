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

Providers are configured in `config.yaml`. Products are streamed from GoTriple and looked up by DOI in the other providers; a provider with `required: false` (OpenAIRE, which also resolves the grants in `funding`) enriches the records it knows without causing any record to be dropped.

To complete an existing `data.json` with the providers it is missing (e.g. after adding a new one) without harvesting new records:

```bash
uv run main.py --enrich
```

Finally, build the knowledge graph (`data.ttl`) from `data.json` with `mapping.yaml`:

```bash
uv run materialize.py
```

The same product, contributor, venue and topic coming from several providers is materialized once: works are matched by DOI, contributors by name within the same work and role, venues by ISSN, topics by term. When providers disagree on a single-valued field, OpenCitations wins over OpenAIRE, which wins over GoTriple.