import json
from fastapi import FastAPI, Request, HTTPException, Query
from urllib.parse import quote
import uvicorn

# --- Application Setup ---
app = FastAPI(
    title="SKG-IF Autocomplete Service",
    description="An API to provide SKG-IF formatted topic suggestions from an ELSST SKOS export.",
    version="1.0.0"
)

# --- Configuration ---
# In a real application, these would come from a config file or environment variables.
SKG_IF_BASE_URL = "https://w3id.org/skg-if/sandbox/cessda-elsst/"
ELSST_DATASOURCE_ID = "urn:cessda:elsst-v5"
DATA_FILE_PATH = "data/elsst_current.jsonld"

# --- Data Loading and Processing ---

# Constants for SKOS URIs
SKOS_CONCEPT = "http://www.w3.org/2004/02/skos/core#Concept"
SKOS_PREF_LABEL = "http://www.w3.org/2004/02/skos/core#prefLabel"
SKOS_ALT_LABEL = "http://www.w3.org/2004/02/skos/core#altLabel"
SKOS_BROADER = "http://www.w3.org/2004/02/skos/core#broader"


def load_elsst_data(filepath: str) -> dict:
    """
    Loads and processes a Skosmos JSON-LD export file into a simple dictionary.

    Args:
        filepath: The path to the .jsonld file exported from Skosmos.

    Returns:
        A dictionary where keys are concept URIs and values are dicts
        with 'prefLabel', 'altLabel', and 'broader' keys.
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"ERROR: Data file not found at '{filepath}'.")
        print("Please download the ELSST JSON-LD export and place it in the correct path.")
        # Return a minimal dataset to allow the server to start, but it will be empty.
        return {}
    except json.JSONDecodeError:
        print(f"ERROR: Could not decode JSON from '{filepath}'. The file might be corrupt.")
        return {}

    # Navigate into the graph
    graph = []
    if isinstance(data, dict) and '@graph' in data:
        graph = data['@graph']
    elif isinstance(data, list):
        # Some JSON-LD files wrap data in a list
        for item in data:
            if '@graph' in item:
                graph.extend(item['@graph'])
    else:
        print("No @graph found in JSON-LD")
        return {}

    processed_data = {}

    for concept in graph:
        if not isinstance(concept, dict) or '@id' not in concept:
            continue

        types = concept.get('@type', [])
        if isinstance(types, str):
            types = [types]

        if SKOS_CONCEPT not in types:
            continue  # Skip non-Concept items

        concept_id = concept['@id']

        # Get English prefLabel
        pref_label = ""
        labels = concept.get(SKOS_PREF_LABEL, [])
        for label in labels:
            if label.get('@language') == 'en':
                pref_label = label.get('@value', '')
                break

        # Get all altLabels
        alt_labels = []
        for label in concept.get(SKOS_ALT_LABEL, []):
            val = label.get('@value')
            if val:
                alt_labels.append(val)

        # Get broader concept
        broader = concept.get(SKOS_BROADER, [])
        if isinstance(broader, dict):
            broader = [broader]
        broader_id = broader[0].get('@id') if broader else None

        processed_data[concept_id] = {
            '@id': concept_id,
            'prefLabel': pref_label,
            'altLabel': alt_labels,
            'broader': broader_id
        }

    print(f"Loaded {len(processed_data)} concepts")
    return processed_data

   

# --- In-memory Data Store ---
# The data is loaded once when the application starts.
# To use this server, you must first download the JSON-LD export from:
# https://thesauri.cessda.eu/elsst-5/en/
# And save it as 'skosmos_export.jsonld.txt' in the same directory as this script.
print("Loading ELSST data from file...")
ELSST_DATA = load_elsst_data(DATA_FILE_PATH)
print(f"Successfully loaded {len(ELSST_DATA)} concepts.")


# --- Helper Functions ---

def get_concept_by_id(concept_id):
    """Retrieves a concept from the in-memory data store."""
    return ELSST_DATA.get(concept_id)

def get_parent_hierarchy(concept_id):
    """Recursively fetches all parent concepts for a given concept ID."""
    hierarchy = set()
    current_id = concept_id
    # Limit recursion to prevent infinite loops in case of cyclic data
    for _ in range(20): 
        if not current_id:
            break
        concept = get_concept_by_id(current_id)
        if concept:
            hierarchy.add(current_id)
            current_id = concept.get("broader")
        else:
            break
    return hierarchy

def to_skgif_topic(concept_data):
    """Transforms a single ELSST concept into an SKG-IF Topic entity."""
    local_id = concept_data['@id']
    topic = {
        "@id": f"{SKG_IF_BASE_URL}{quote(local_id)}",
        "@type": "Topic",
        "local_identifier": local_id,
        "name": concept_data.get("prefLabel"),
        "source": {"@id": ELSST_DATASOURCE_ID}
    }
    if concept_data.get("altLabel"):
        topic["alternate_name"] = concept_data["altLabel"]
    if concept_data.get("broader"):
        topic["parent_topic"] = {
            "@type": "Topic",
            "local_identifier": concept_data["broader"]
        }
    return topic

def get_data_source():
    """Creates the SKG-IF DataSource entity for ELSST."""
    return {
        "@id": ELSST_DATASOURCE_ID,
        "@type": "DataSource",
        "local_identifier": "elsst-v5",
        "name": "European Language Social Science Thesaurus (ELSST) - Version 5",
        "url": "https://thesauri.cessda.eu/elsst-5/en/"
    }

# --- API Endpoint ---

@app.get('/api/topics', summary="Get SKG-IF topic suggestions", response_model=dict)
async def autocomplete(q: str = Query(..., min_length=3, description="The search query string (at least 3 characters).")):
    """
    Provides autocomplete suggestions for social science topics.

    - Searches for concepts in the ELSST thesaurus matching the query `q`.
    - Returns a JSON-LD object compliant with the SKG Interoperability Framework.
    - The response includes the matching topics and their full parent hierarchies.
    """
    query = q.lower()

    # Find concepts that match the query
    matching_concept_ids = set()
    for concept_id, data in ELSST_DATA.items():
        # Check preferred label
        if query in data.get('prefLabel', '').lower():
            matching_concept_ids.add(concept_id)
        # Check alternative labels
        for alt_label in data.get('altLabel', []):
            if query in alt_label.lower():
                matching_concept_ids.add(concept_id)
                break

    # For each match, get its full parent hierarchy
    all_related_ids = set()
    for concept_id in matching_concept_ids:
        all_related_ids.update(get_parent_hierarchy(concept_id))

    # Build the SKG-IF graph
    graph_entities = [get_data_source()]
    for concept_id in all_related_ids:
        concept_data = get_concept_by_id(concept_id)
        if concept_data:
            graph_entities.append(to_skgif_topic(concept_data))

    # Construct the final JSON-LD response
    response = {
        "@context": [
            "https://w3id.org/skg-if/context/skg-if.json",
            {
                "@base": SKG_IF_BASE_URL
            }
        ],
        "@graph": graph_entities
    }

    return response

# --- Main execution ---
if __name__ == '__main__':
    # This allows running the server directly for development.
    # For production, you would use a production-grade ASGI server like Gunicorn.
    # Example: uvicorn server:app --host 0.0.0.0 --port 8000
    print("Starting FastAPI server...")
    uvicorn.run(app, host="0.0.0.0", port=8000)