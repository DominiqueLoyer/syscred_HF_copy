#!/usr/bin/env python3
"""
Import Turtle RDF data into Supabase
"""
import os
import sys
import requests
from rdflib import Graph, Literal, URIRef, Namespace
from pathlib import Path

# Load .env file (if python-dotenv is installed)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not installed — rely on system env vars

# === SECURE: Load credentials from environment variables ===
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://zmluirvqfkmfazqitqgi.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_SECRET_KEY") or os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

if not SUPABASE_KEY:
    print("❌ ERREUR: SUPABASE_SECRET_KEY non défini!")
    print("   Créez un fichier .env avec: SUPABASE_SECRET_KEY=votre_clé")
    print("   Ou exportez: export SUPABASE_SECRET_KEY=votre_clé")
    sys.exit(1)

headers = {
    'apikey': SUPABASE_KEY,
    'Authorization': f'Bearer {SUPABASE_KEY}',
    'Content-Type': 'application/json',
    'Prefer': 'resolution=merge-duplicates'
}

# Namespace mapping - old github to new syscred.uqam.ca
OLD_NS = "https://github.com/DominiqueLoyer/systemFactChecking#"
NEW_NS = "https://syscred.uqam.ca/ontology#"

def transform_uri(uri):
    """Transform old github namespace to new syscred namespace"""
    uri = str(uri)
    if OLD_NS in uri:
        return uri.replace(OLD_NS, NEW_NS)
    return uri

# Parse Turtle files
print("=== Parsing Turtle files ===")
g = Graph()

# Parse base ontology
base_file = Path("ontology/sysCRED_onto26avrtil.ttl")
if base_file.exists():
    print(f"Loading: {base_file}")
    g.parse(str(base_file), format='turtle')

# Parse data ontology
data_file = Path("ontology/sysCRED_data.ttl")
if data_file.exists():
    print(f"Loading: {data_file}")
    g.parse(str(data_file), format='turtle')

print(f"Total triples parsed: {len(g)}")

# Transform and insert
print("\n=== Inserting into Supabase (rdf_triples table) ===")

batch = []
batch_size = 100
total_inserted = 0

for i, (s, p, o) in enumerate(g):
    # Transform URIs
    subject = transform_uri(s)
    predicate = transform_uri(p)
    obj_value = transform_uri(o) if isinstance(o, URIRef) else str(o)
    obj_type = 'literal' if isinstance(o, Literal) else 'uri'
    graph_name = 'base' if OLD_NS in str(s) or 'Expert' in str(s) else 'data'
    
    batch.append({
        'subject': subject[:500],
        'predicate': predicate[:500],
        'object': obj_value,
        'object_type': obj_type,
        'graph_name': graph_name
    })
    
    # Insert in batches
    if len(batch) >= batch_size:
        response = requests.post(
            f"{SUPABASE_URL}/rest/v1/rdf_triples",
            headers=headers,
            json=batch
        )
        if response.status_code in [200, 201]:
            total_inserted += len(batch)
            print(f"  Inserted batch {total_inserted//batch_size}: {len(batch)} triples")
        else:
            print(f"  Error: {response.status_code} - {response.text[:100]}")
        batch = []

# Insert remaining
if batch:
    response = requests.post(
        f"{SUPABASE_URL}/rest/v1/rdf_triples",
        headers=headers,
        json=batch
    )
    if response.status_code in [200, 201]:
        total_inserted += len(batch)
        print(f"  Inserted final batch: {len(batch)} triples")
    else:
        print(f"  Error: {response.status_code}")

print(f"\n✓ Total inserted: {total_inserted}")

# Verify
print("\n=== Verifying ===")
response = requests.get(
    f"{SUPABASE_URL}/rest/v1/rdf_triples?select=id",
    headers={'apikey': SUPABASE_KEY, 'Authorization': f'Bearer {SUPABASE_KEY}'}
)
if response.status_code == 200:
    print(f"Total in rdf_triples: {len(response.json())}")
