# Django RAG portal (Azure OpenAI + Azure AI Search)

Server-rendered **Django** app with **Django templates** for chat and document upload. Retrieval uses **Azure OpenAI** (embeddings + chat) and **Azure AI Search** (vector index)—the standard Microsoft RAG stack on Azure.

## Prerequisites

- Python 3.11+
- Azure subscription
- **Azure OpenAI** resource with:
  - Chat deployment (e.g. `gpt-4o-mini`)
  - Embeddings deployment (e.g. `text-embedding-3-small` or `text-embedding-ada-002`)
- **Azure AI Search** service (Basic tier or higher for vector search at scale)

## Local setup

```powershell
cd c:\Users\mikiy\Documents\Azure
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
# Edit .env with your endpoints, keys, and deployment names
python manage.py migrate
python manage.py createsuperuser
python manage.py setup_search_index
python manage.py index_documents
python manage.py collectstatic --noinput
python manage.py runserver
```

Open http://127.0.0.1:8000 — use **Ask** to query indexed content and **Upload** to add `.txt` / `.md` files.

Health check (for load balancers): `GET /health/`

## Azure resources (summary)

| Service | Role |
|--------|------|
| **Azure OpenAI** | `text-embedding-*` for vectors; chat model for grounded answers |
| **Azure AI Search** | Stores chunks + vectors; hybrid keyword + vector query at question time |

Set `EMBEDDING_DIMENSIONS` to match your embedding model (typically **1536** for `text-embedding-3-small` / `ada-002`).

## Deploy on an Azure Linux VM

High-level steps:

1. **Create a VM** (e.g. Ubuntu 22.04 LTS), allow **SSH** and **HTTP (80)** in the NSG. Optionally add **HTTPS (443)** after TLS.
2. **Install stack** on the VM:

   ```bash
   sudo apt update && sudo apt install -y python3-venv python3-pip nginx git
   ```

3. **Copy the project** to e.g. `/var/www/rag-portal` (git clone or scp).
4. **Virtualenv & dependencies:**

   ```bash
   cd /var/www/rag-portal
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

5. **Environment:** create `/var/www/rag-portal/.env` from `.env.example`. Set:

   - `DJANGO_DEBUG=false`
   - `DJANGO_SECRET_KEY` to a long random string
   - `DJANGO_ALLOWED_HOSTS` to your VM public IP or DNS name
   - All `AZURE_*` variables

6. **Django:**

   ```bash
   python manage.py migrate
   python manage.py collectstatic --noinput
   python manage.py setup_search_index
   python manage.py index_documents
   ```

7. **Gunicorn systemd:** adapt `deploy/gunicorn.service.example` → `/etc/systemd/system/rag-portal.service`, then:

   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable --now rag-portal
   ```

8. **Nginx:** adapt `deploy/nginx.conf.example` under `/etc/nginx/sites-available/`, enable the site, `sudo nginx -t && sudo systemctl reload nginx`.

9. **TLS:** use `certbot` with Let’s Encrypt when you have a domain name.

### Security notes for production

- Do not commit `.env`; restrict file permissions on the VM (`chmod 600 .env`).
- Prefer **managed identity** or **Key Vault** over long-lived API keys when you evolve the app.
- Add rate limiting and authentication (e.g. Azure AD) before exposing broadly on the internet.

## Project layout

- `config/` — Django settings, URLs, WSGI
- `rag_core/` — views, templates, static files, RAG services
- `rag_core/services/` — Azure OpenAI, Azure Search, chunking, orchestration
- `documents/sample/` — sample markdown for first index run
- `documents/uploads/` — user uploads from the web UI
- `deploy/` — example **systemd** and **nginx** configs

## Commands reference

| Command | Purpose |
|--------|---------|
| `python manage.py setup_search_index` | Create/update vector index in Azure AI Search |
| `python manage.py index_documents` | Index all `.txt`/`.md` under `documents/sample` and `documents/uploads` |
| `python manage.py index_documents --path path/to/file.md` | Index one file |

## License

Use and modify for your own learning and deployment; Azure services billed per your subscription.
