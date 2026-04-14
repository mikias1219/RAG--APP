from __future__ import annotations

def load_secret(vault_url: str, secret_name: str) -> str:
    from azure.identity import DefaultAzureCredential
    from azure.keyvault.secrets import SecretClient

    credential = DefaultAzureCredential()
    client = SecretClient(vault_url=vault_url, credential=credential)
    return client.get_secret(secret_name).value or ""
