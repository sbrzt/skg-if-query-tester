import morph_kgc
from rdflib import Namespace

CONFIG = """
[Data]
mappings: mapping.yaml
"""

graph = morph_kgc.materialize(CONFIG)
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
    "frapo": "http://purl.org/cerif/frapo/",
    "prism": "http://prismstandard.org/namespaces/basic/2.0/",
    "co": "http://purl.org/co/",
    "ti": "http://www.ontologydesignpatterns.org/cp/owl/timeinterval.owl#",
}

for prefix, uri in prefixes.items():
    graph.bind(prefix, Namespace(uri), override=True)
graph.serialize(destination="data.ttl", format="turtle")