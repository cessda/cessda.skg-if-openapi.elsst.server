# SKG-IF Autocomplete Service

> An API to provide SKG-IF formatted topic suggestions from an ELSST SKOS export.

This service provides a RESTful API that delivers autocomplete suggestions for social science topics based on the [European Language Social Science Thesaurus (ELSST)](https://thesauri.cessda.eu/elsst-5/en/). The responses are formatted according to the [SKG Interoperability Framework (SKG-IF)](https://w3id.org/skg-if/spec), making them suitable for integration into knowledge graph-aware applications.

## Features

-   **FastAPI Backend**: A modern, high-performance Python web framework.
-   **SKG-IF Compliant**: Returns JSON-LD formatted data following the SKG-IF `Topic` and `DataSource` schemas.
-   **Autocomplete**: Searches ELSST preferred and alternative labels to find matching concepts.
-   **Hierarchical Data**: Includes the full parent hierarchy for each matching topic, providing rich contextual information.
-   **In-Memory Cache**: Loads the ELSST data into memory on startup for fast query responses.

## Prerequisites

-   Python 3.8+
-   `pip` and `venv` (recommended)

## Installation

1.  **Clone the repository (or set up your project folder):**
    ```bash
    git clone <your-repo-url>
    cd <your-repo-folder>
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    # On Windows, use: venv\Scripts\activate
    ```

3.  **Install the required packages:**
    A `requirements.txt` file is provided for convenience.
    ```bash
    pip install -r requirements.txt
    ```

## Data Setup

This service relies on a JSON-LD export of the ELSST thesaurus.

1.  **Download the data file:**
    -   Go to the ELSST thesaurus download page: https://thesauri.cessda.eu/elsst-5/en/
    -   Under the "Downloads" section, find the **JSON-LD** format and download it.

2.  **Place and rename the file:**
    -   Save the downloaded file in the root of the project directory.
    -   Rename the file to `elsst_current.jsonld`.

The server is configured in `server.py` to look for this specific file name (`elsst_current.jsonld`).

## Running the Server

### Development Mode

For development, you can run the server using `uvicorn` with live reloading. This will automatically restart the server whenever you make changes to the code.

```bash
uvicorn server:app --reload
```

The API will be available at `http://127.0.0.1:8000`. You can also view the auto-generated documentation at `http://127.0.0.1:8000/docs`.

### Production Mode

For a production environment, it is recommended to use a production-grade ASGI server like Gunicorn with Uvicorn workers.

```bash
gunicorn -w 4 -k uvicorn.workers.UvicornWorker server:app
```

This command starts 4 worker processes to handle requests.

## API Usage

### Autocomplete Endpoint

-   **URL**: `/api/topics`
-   **Method**: `GET`
-   **Query Parameter**:
    -   `q` (string, required, min 3 characters): The search term to find matching topics.

#### Example Request

You can test the endpoint using `curl` or any API client.

```bash
curl -X GET "http://127.0.0.1:8000/api/topics?q=poverty"
```

#### Example Response

The server will return a JSON-LD object containing a `@graph` of entities. This graph includes:
-   The `DataSource` entity for ELSST.
-   All `Topic` entities that matched the query string (`poverty` in this case).
-   All parent `Topic` entities for each matched topic, up to the top of the hierarchy.

```json
{
    "@context": [
        "https://w3id.org/skg-if/context/skg-if.json",
        {
            "@base": "https://w3id.org/skg-if/sandbox/cessda-elsst/"
        }
    ],
    "@graph": [
        {
            "@id": "urn:cessda:elsst-v5",
            "@type": "DataSource",
            "local_identifier": "elsst-v5",
            "name": "European Language Social Science Thesaurus (ELSST) - Version 5",
            "url": "https://thesauri.cessda.eu/elsst-5/en/"
        },
        {
            "@id": "https://w3id.org/skg-if/sandbox/cessda-elsst/urn%3Acessda%3Aelsst-4-en%3A368",
            "@type": "Topic",
            "local_identifier": "urn:cessda:elsst-4-en:368",
            "name": "POVERTY",
            "source": { "@id": "urn:cessda:elsst-v5" },
            "alternate_name": ["destitution", "impoverishment"],
            "parent_topic": { "@type": "Topic", "local_identifier": "urn:cessda:elsst-4-en:367" }
        }
    ]
}
```