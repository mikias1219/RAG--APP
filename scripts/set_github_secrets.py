"""
Set GitHub Actions secrets for this repo using the GitHub REST API.

Why this exists:
  GitHub requires secrets be encrypted with the repo's public key (libsodium sealed box).
  This script automates that.

Requirements:
  pip install pynacl requests

Usage (PowerShell):
  $env:GITHUB_TOKEN = "ghp_..."   # PAT with repo + actions:write
  python scripts/set_github_secrets.py --repo mikias1219/RAG--APP ^
    --secret VM_HOST=ragapp624445.westeurope.cloudapp.azure.com ^
    --secret VM_USER=azureuser ^
    --secret VM_APP_DIR=/var/www/rag-portal ^
    --secret ENV_FILE="@C:\\path\\to\\prod.env" ^
    --secret VM_SSH_PRIVATE_KEY="@C:\\path\\to\\deploy_key"
"""

from __future__ import annotations

import argparse
import base64
import os
from dataclasses import dataclass

import requests
from nacl import encoding, public


@dataclass
class RepoKey:
    key_id: str
    key: str  # base64


def _require_token() -> str:
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if not token:
        raise SystemExit("Set GITHUB_TOKEN to a GitHub PAT with repo + actions:write scopes.")
    return token


def _gh_headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "rag-app-secrets-script",
    }


def get_public_key(repo: str, token: str) -> RepoKey:
    r = requests.get(
        f"https://api.github.com/repos/{repo}/actions/secrets/public-key",
        headers=_gh_headers(token),
        timeout=30,
    )
    r.raise_for_status()
    data = r.json()
    return RepoKey(key_id=data["key_id"], key=data["key"])


def encrypt_secret(public_key_b64: str, secret_value: str) -> str:
    public_key = public.PublicKey(public_key_b64.encode("utf-8"), encoding.Base64Encoder())
    sealed_box = public.SealedBox(public_key)
    encrypted = sealed_box.encrypt(secret_value.encode("utf-8"))
    return base64.b64encode(encrypted).decode("utf-8")


def put_secret(repo: str, token: str, name: str, value: str, repo_key: RepoKey) -> None:
    enc = encrypt_secret(repo_key.key, value)
    r = requests.put(
        f"https://api.github.com/repos/{repo}/actions/secrets/{name}",
        headers=_gh_headers(token),
        json={"encrypted_value": enc, "key_id": repo_key.key_id},
        timeout=30,
    )
    r.raise_for_status()


def _parse_secret_arg(s: str) -> tuple[str, str]:
    if "=" not in s:
        raise SystemExit(f"Invalid --secret {s!r}. Use NAME=value or NAME=@path.")
    name, raw = s.split("=", 1)
    name = name.strip()
    raw = raw.strip()
    if not name:
        raise SystemExit("Secret name cannot be empty.")
    if raw.startswith("@"):
        path = raw[1:]
        with open(path, "r", encoding="utf-8") as f:
            return name, f.read()
    return name, raw


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, help="owner/repo, e.g. mikias1219/RAG--APP")
    ap.add_argument(
        "--secret",
        action="append",
        default=[],
        help="Secret in NAME=value or NAME=@path form (repeatable).",
    )
    args = ap.parse_args()

    token = _require_token()
    if not args.secret:
        raise SystemExit("Provide at least one --secret.")

    pairs = [_parse_secret_arg(x) for x in args.secret]
    repo_key = get_public_key(args.repo, token)
    for name, value in pairs:
        put_secret(args.repo, token, name, value, repo_key)
        print(f"Set secret: {name}")


if __name__ == "__main__":
    main()

