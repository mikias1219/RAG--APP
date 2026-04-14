# Knowledge Hub — multi-tenant Django RAG (Azure OpenAI + Azure AI Search)

Server-rendered **Django** app with **login/registration**, **organization tenants + RBAC**, workspace collections, and a modernized chat/admin UI. Queries are scoped by tenant/workspace in Azure AI Search (`organizationId` + `collectionId` filters). Retrieval uses **Azure OpenAI** (embeddings + chat) and **Azure AI Search** (vector index + lexical fallback).

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
python manage.py createsuperuser   # optional; users can also register at /register/
python manage.py setup_search_index
python manage.py collectstatic --noinput
python manage.py runserver
```

1. Open **http://127.0.0.1:8000** — register (you get a **General** workspace) or sign in.
2. Open **Workspaces** → upload `.txt`, `.md`, `.pdf`, or `.docx` into a workspace.
3. Use **Chat** — scope **all workspaces** or one workspace via the sidebar.

After upgrading, run **`python manage.py setup_search_index` again** so the index includes tenant-aware fields (`organizationId`, `collectionId`, `documentUid`).

**CLI indexing** (optional): `python manage.py index_documents --username YOU --collection-id 1 --path path/to/file.pdf`

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
   ```

7. **Gunicorn systemd:** adapt `deploy/gunicorn.service.example` → `/etc/systemd/system/rag-portal.service`, then:

   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable --now rag-portal
   ```

8. **Nginx:** adapt `deploy/nginx.conf.example` under `/etc/nginx/sites-available/`, enable the site, `sudo nginx -t && sudo systemctl reload nginx`.

9. **TLS:** use `certbot` with Let’s Encrypt when you have a domain name.

## CI/CD (GitHub Actions → Azure VM)

This repo includes:
- `.github/workflows/ci.yml` for lint/type/security/deploy checks
- `.github/workflows/deploy-staging.yml` for staging releases
- `.github/workflows/deploy-production.yml` for production releases after CI success

### Required GitHub Secrets

Create these in **GitHub → Settings → Secrets and variables → Actions → New repository secret**:

- **`VM_HOST`**: VM public IP or DNS name (example: `203.0.113.10`)
- **`VM_USER`**: SSH username (example: `azureuser`)
- **`VM_SSH_PRIVATE_KEY`**: private key for SSH auth (PEM/OpenSSH format)
- **`VM_APP_DIR`**: deployment folder on VM (example: `/var/www/rag-portal`)
- **`ENV_FILE`**: full contents of your production `.env` (multi-line)

The workflow rsyncs the repo to `VM_APP_DIR`, writes `.env`, then runs `deploy/deploy_vm.sh` which installs dependencies, runs migrations, collects static files, updates the Azure Search index schema, and restarts `rag-portal` (if installed as a systemd service).


### Security notes for production

- Do not commit `.env`; restrict file permissions on the VM (`chmod 600 .env`).
- Prefer **managed identity** or **Key Vault** over long-lived API keys when you evolve the app.
- Prefer OIDC (Microsoft Entra ID) and Key Vault + managed identity for enterprise deployments.

## Project layout

- `config/` — Django settings, URLs, WSGI
- `rag_core/` — views, templates, static files, RAG services
- `rag_core/services/` — Azure OpenAI, Azure Search, chunking, orchestration
- `documents/sample/` — optional sample files for CLI indexing only
- `documents/uploads/<user_id>/<collection_id>/` — files uploaded via the web UI
- `deploy/` — example **systemd** and **nginx** configs

## Commands reference

| Command | Purpose |
|--------|---------|
| `python manage.py setup_search_index` | Create/update vector index in Azure AI Search |
| `python manage.py index_documents --username U --collection-id N --path FILE` | Index one file into that user’s collection |
| `python manage.py index_documents --username U --collection-id N --folder DIR` | Index a folder (same extensions as the web UI) |

## License

Use and modify for your own learning and deployment; Azure services billed per your subscription.
