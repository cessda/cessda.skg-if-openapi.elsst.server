# API Server

This project provides a simple API server to query topics data.

## Requirements

- Python 3.9+
- An ASGI server like Uvicorn or Gunicorn.
- An ELSST SKOS export in JSON-LD format (e.g., `elsst_current.jsonld`) placed in the `data/` directory.

## Running the Server for Development
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Start the server:
   ```bash
   python server.py
   ```
   Or using Uvicorn directly for more options (like auto-reload):
   ```bash
   uvicorn server:app --reload
   ```
3. The server will run at:
   ```
   http://localhost:8000
   ```

## Production Deployment (with Apache)

For production, it's recommended to run the application using a production-grade ASGI server like Gunicorn behind a reverse proxy like Apache or Nginx.

1.  **Run with Gunicorn:**
    ```bash
    gunicorn -w 4 -k uvicorn.workers.UvicornWorker server:app
    ```
    This command starts Gunicorn with 4 worker processes.

2.  **Configure Apache as a Reverse Proxy:**
    Below is an example Apache VirtualHost configuration to proxy requests to the running application. This setup also handles SSL termination.

    Make sure `mod_proxy` and `mod_proxy_http` are enabled in Apache.

    ```apache
    <VirtualHost *:443>
        ServerName skg-if-openapi.cessda.eu

        # SSL Configuration
        SSLEngine on
        SSLCertificateFile /etc/letsencrypt/live/skg-if-openapi.cessda.eu/fullchain.pem
        SSLCertificateKeyFile /etc/letsencrypt/live/skg-if-openapi.cessda.eu/privkey.pem

        # This is important to allow encoded slashes in topic IDs (URIs)
        AllowEncodedSlashes NoDecode

        # Proxy settings
        ProxyRequests Off
        ProxyPass /api/ http://localhost:8000/api/ nocanon
        ProxyPassReverse /api/ http://localhost:8000/api/

        # Logging
        ErrorLog ${APACHE_LOG_DIR}/skg-if-openapi_error.log
        CustomLog ${APACHE_LOG_DIR}/skg-if-openapi_access.log combined
    </VirtualHost>
    ```

## Example Queries

### Get a topic by ID
```bash
curl https://skg-if-openapi.cessda.eu/api/topics/https%3A%2F%2Felsst.cessda.eu%2Fid%2F5%2Fdab48525-c485-459b-bb41-730756f1dd65
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