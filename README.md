---
Title: SKG-IF Query Tester
Authors: Sebastian Barzaghi (https://orcid.org/0000-0002-0799-1527)
Release: 2026-07-17
Revision: 1.0.0
License: ISC License
---

# SKG-IF Query Tester

## Description

An ETL pipeline for building a Scholarly Knowledge Graph from data extracted from GoTriple and OpenCitations APIs.

It fetches bibliographic data from external APIs in JSON format and converts it into RDF triples using declarative mapping rules.

It generates a structured knowledge graph that models relationships between publications, datasets, authors, and identifiers using the SKG-IF model, based on standard Semantic Web ontologies (such as FABIO, DataCite, and PRO).

## How to run

First install [uv](https://docs.astral.sh/uv/):

```bash
wget -qO- https://astral.sh/uv/install.sh | sh
```

Then run the orchestrator:

```bash
uv run main.py
```