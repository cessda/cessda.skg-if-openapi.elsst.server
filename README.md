# API Server

This project provides a simple API server to query topics data.

## Requirements

- Python 3.9+
- Docker (optional, for containerized deployment)

## Running the Server

### Option 1 – Local (Python)
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Start the server:
   ```bash
   python server.py
   ```
3. The server will run at:
   ```
   http://localhost:8000
   ```

### Option 2 – Docker
1. Build the image:
   ```bash
   docker build -t api-server .
   ```
2. Run the container:
   ```bash
   docker run -p 8000:8000 api-server
   ```

## Example Queries

### Get a topic by ID
```bash
curl http://localhost:8000/api/topics/https://elsst.cessda.eu/id/5/dab48525-c485-459b-bb41-730756f1dd65
```

### Search topics by label and language
```bash
curl "http://localhost:8000/api/topics?filter=cf.search.labels:barn,cf.search.language:no"
```

## Response Format
Responses are returned in JSON format.

**Example:**
```json
{
  "id": "https://elsst.cessda.eu/id/5/dab48525-c485-459b-bb41-730756f1dd65",
  "label": "Barn",
  "language": "no",
  "description": "Example topic description."
}
```

---
**Tip:** Wrap query URLs in quotes to avoid shell interpretation issues.