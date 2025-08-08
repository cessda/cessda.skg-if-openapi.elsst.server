import json
from fastapi import FastAPI, HTTPException, Query, Path
import re
import random
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
SKG_IF_CONTEXT_URL = "https://w3id.org/skg-if/context/1.0.1/skg-if.json"
ELSST_DATASOURCE_ID = "urn:cessda:elsst-v5"
ELSST_SCHEME_NAME = "CESSDA ELSST v5"
ELSST_SCHEME_URL = "https://thesauri.cessda.eu/elsst-5"
DATA_FILE_PATH = "data/elsst_current.jsonld"

# --- Data Loading and Processing ---

# Constants for SKOS URIs
SKOS_CONCEPT = "http://www.w3.org/2004/02/skos/core#Concept"
SKOS_PREF_LABEL = "http://www.w3.org/2004/02/skos/core#prefLabel"
SKOS_ALT_LABEL = "http://www.w3.org/2004/02/skos/core#altLabel"
SKOS_BROADER = "http://www.w3.org/2004/02/skos/core#broader"


def load_elsst_data(filepath: str) -> dict:
    """
    Loads and processes an ELSST JSON-LD export file into a multilingual dictionary.

    Args:
        filepath: The path to the .jsonld file.

    Returns:
        A dictionary where keys are concept URIs and values are dicts
        with multilingual 'prefLabels', 'altLabels', and 'broader' keys.
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

        # Get all prefLabels, keyed by language
        pref_labels = {}
        for label in concept.get(SKOS_PREF_LABEL, []):
            lang = label.get('@language')
            value = label.get('@value')
            if lang and value:
                pref_labels[lang] = value

        # Get all altLabels, keyed by language and grouped in a list
        alt_labels = {}
        for label in concept.get(SKOS_ALT_LABEL, []):
            lang = label.get('@language')
            value = label.get('@value')
            if lang and value:
                alt_labels.setdefault(lang, []).append(value)

        # Get broader concept
        broader = concept.get(SKOS_BROADER, [])
        if isinstance(broader, dict):
            broader = [broader]
        broader_id = broader[0].get('@id') if broader else None

        processed_data[concept_id] = {
            '@id': concept_id,
            'prefLabels': pref_labels,
            'altLabels': alt_labels,
            'broader': broader_id
        }

    print(f"Loaded {len(processed_data)} concepts with multilingual labels")
    return processed_data


def build_search_index(processed_data: dict) -> dict:
    """
    Builds a search index from the processed ELSST data for faster lookups.

    Args:
        processed_data: The dictionary of concepts from load_elsst_data.

    Returns:
        A dictionary where keys are language codes (e.g., 'en') and values are
        lists of tuples, with each tuple containing a lowercase label and the
        corresponding concept URI. e.g., {'en': [('poverty', 'uri:1'), ...]}
    """
    search_index = {}
    print("Building search index...")
    for concept_id, data in processed_data.items():
        # Index preferred labels
        for lang, label in data.get('prefLabels', {}).items():
            search_index.setdefault(lang, []).append((label.lower(), concept_id))

        # Index alternative labels
        for lang, labels in data.get('altLabels', {}).items():
            for label in labels:
                search_index.setdefault(lang, []).append((label.lower(), concept_id))

    for lang, items in search_index.items():
        print(f"  - Indexed {len(items)} labels for language '{lang}'")

    print("Search index built.")
    return search_index


# --- In-memory Data Store ---
# The data is loaded once when the application starts.
print("Loading ELSST data from file...")
ELSST_DATA = load_elsst_data(DATA_FILE_PATH)
SEARCH_INDEX = build_search_index(ELSST_DATA)


# --- Helper Functions ---

def format_topic_for_response(concept_data: dict) -> dict:
    """Transforms a single ELSST concept into the API's response format."""
    return {
        "local_identifier": concept_data.get('@id'),
        "identifiers": [],  # ELSST data does not contain external identifiers like wikidata
        "entity_type": "topic",
        "labels": concept_data.get("prefLabels", {})
    }

# --- Debugging Endpoint ---

@app.get('/show_index_data', summary="Show a sample of the in-memory data", include_in_schema=False)
async def show_index_data():
    """
    Provides a sample of the loaded ELSST data and the constructed search index
    for debugging purposes. Shows up to 10 random items from the main data store
    and up to 10 random items from the search index for each language.
    """
    # Sample from ELSST_DATA
    elsst_keys = list(ELSST_DATA.keys())
    sample_size_elsst = min(10, len(elsst_keys))
    # Ensure we don't try to sample from an empty list if data loading failed
    random_elsst_keys = random.sample(elsst_keys, sample_size_elsst) if elsst_keys else []
    elsst_sample = {key: ELSST_DATA[key] for key in random_elsst_keys}

    # Sample from SEARCH_INDEX for each language
    search_index_sample = {}
    for lang, items in SEARCH_INDEX.items():
        sample_size_index = min(10, len(items))
        search_index_sample[lang] = random.sample(items, sample_size_index)

    return {
        "elsst_data_sample": elsst_sample,
        "search_index_sample": search_index_sample
    }


# --- API Endpoint ---

@app.get('/api/topics/{topic_id:path}', summary="Get a single topic by its identifier", response_model=dict)
async def topic_single(
    topic_id: str = Path(..., description="The persistent identifier (URI) of the topic. Must be URL-encoded.")
):
    """
    Retrieves a single topic by its persistent identifier (URI).

    - The `topic_id` path parameter is the full, URL-encoded URI of the topic.
    - Example: `/api/topics/http%3A%2F%2Fpurl.org%2Felsst%2F4%2Fes%2F368`
    """
    # FastAPI automatically URL-decodes path parameters.
    # The topic_id is the key in our ELSST_DATA dictionary.
    concept_data = ELSST_DATA.get(topic_id)

    if not concept_data:
        raise HTTPException(
            status_code=404,
            detail=f"Topic with ID '{topic_id}' not found."
        )

    # Format the single topic into the SKG-IF JSON-LD structure.
    topic_graph_item = {
        "local_identifier": concept_data.get('@id'),
        #"identifiers": [
        #    {
        #        "scheme": ELSST_SCHEME_NAME,
        #        "value": ELSST_SCHEME_URL
        #    }
        #,
        "entity_type": "topic",
        "labels": concept_data.get("prefLabels", {})
    }

    # Construct the final JSON-LD response
    return {
        "@context": [
            SKG_IF_CONTEXT_URL,
            {
                "@base": SKG_IF_BASE_URL
            }
        ],
        "@graph": [topic_graph_item]
    }


@app.get('/api/topics', summary="Get topic suggestions", response_model=dict)
async def topic_result(
    filter: str = Query(
        ...,
        min_length=19, # e.g., "cf.search.labels:abc"
        description="Filter for topics. Format: `cf.search.labels:<term>,cf.search.language:<lang>`"
    )
):
    """
    Provides autocomplete suggestions for social science topics.

    - The `filter` query parameter accepts a comma-separated string of key:value pairs.
    - `cf.search.labels` (required): The term to search for (min 3 characters).
    - `cf.search.language` (optional): The 2-letter language code (defaults to 'en').
    - Example: `?filter=cf.search.labels:poverty,cf.search.language:de`
    """
    # Parse the complex 'filter' parameter which can contain multiple key:value pairs.
    filter_params = {}
    try:
        for part in filter.split(','):
            key, value = part.split(':', 1)
            filter_params[key.strip()] = value.strip()
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail=[{
                "loc": ["query", "filter"],
                "msg": "Filter parameter is malformed. Expected format: 'key1:value1,key2:value2'.",
                "type": "value_error.format"
            }]
        )

    # Extract and validate search term from the parsed filter
    search_term = filter_params.get("cf.search.labels")
    if not search_term or len(search_term) < 3:
        raise HTTPException(
            status_code=422,
            detail=[{
                "loc": ["query", "filter"],
                "msg": "A 'cf.search.labels' key with a value of at least 3 characters must be provided in the filter.",
                "type": "value_error.missing"
            }]
        )

    # Extract and validate language code, defaulting to 'en'
    language_code = filter_params.get("cf.search.language", "en")
    if not re.match("^[a-z]{2}$", language_code):
        raise HTTPException(
            status_code=422,
            detail=[{
                "loc": ["query", "filter"],
                "msg": "If provided, the value for 'cf.search.language' must be a 2-letter ISO 639-1 code.",
                "type": "value_error.pattern"
            }]
        )

    search_lang = language_code
    query = search_term.lower()

    # Find concepts that match the query in the specified language using the search index
    matching_concept_ids = set()

    # Get all searchable labels for the given language
    labels_for_lang = SEARCH_INDEX.get(search_lang, [])

    for label, concept_id in labels_for_lang:
        if query in label:
            matching_concept_ids.add(concept_id)

    # Build the results list, sorting for consistent output
    results = []
    for concept_id in sorted(list(matching_concept_ids)):
        concept_data = ELSST_DATA.get(concept_id)
        if concept_data:
            results.append(format_topic_for_response(concept_data))

    # Construct the final JSON-LD response
    response = {
        "meta": {
            "count": len(results),
            "page": 0,
            "page_size": 0
        },
        "results": results
    }

    return response

# --- Main execution ---
if __name__ == '__main__':
    # This allows running the server directly for development.
    # For production, you would use a production-grade ASGI server like Gunicorn.
    # Example: uvicorn server:app --host 0.0.0.0 --port 8000
    print("Starting FastAPI server...")
    uvicorn.run(app, host="0.0.0.0", port=8000)