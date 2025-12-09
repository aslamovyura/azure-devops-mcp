import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class AzureDevOpsConfig:
    base_url: str
    collection: Optional[str]
    default_project: Optional[str]
    api_version: str
    auth_type: str  # "pat" or "ntlm"
    pat: Optional[str]
    ntlm_username: Optional[str]
    ntlm_password: Optional[str]
    ntlm_domain: Optional[str]
    verify_ssl: bool

    @staticmethod
    def from_env() -> "AzureDevOpsConfig":
        base_url = os.environ.get("AZDO_BASE_URL", "").rstrip("/")
        if not base_url:
            raise ValueError(
                "AZDO_BASE_URL is required (e.g., https://tfs.company.local/tfs or https://devops.company.local/tfs/DefaultCollection)"
            )

        collection = os.environ.get("AZDO_COLLECTION")
        default_project = os.environ.get("AZDO_PROJECT")
        api_version = os.environ.get("AZDO_API_VERSION", "7.0")
        auth_type = os.environ.get("AZDO_AUTH_TYPE", "pat").lower()

        pat = os.environ.get("AZDO_PAT")
        ntlm_username = os.environ.get("AZDO_NTLM_USERNAME")
        ntlm_password = os.environ.get("AZDO_NTLM_PASSWORD")
        ntlm_domain = os.environ.get("AZDO_NTLM_DOMAIN")
        verify_ssl = os.environ.get("AZDO_VERIFY_SSL", "true").lower() in ("1", "true", "yes")

        if auth_type not in ("pat", "ntlm"):
            raise ValueError("AZDO_AUTH_TYPE must be 'pat' or 'ntlm'")
        if auth_type == "pat" and not pat:
            raise ValueError("AZDO_PAT is required when AZDO_AUTH_TYPE=pat")
        if auth_type == "ntlm" and not (ntlm_username and ntlm_password):
            raise ValueError("AZDO_NTLM_USERNAME and AZDO_NTLM_PASSWORD are required when AZDO_AUTH_TYPE=ntlm")

        return AzureDevOpsConfig(
            base_url=base_url,
            collection=collection,
            default_project=default_project,
            api_version=api_version,
            auth_type=auth_type,
            pat=pat,
            ntlm_username=ntlm_username,
            ntlm_password=ntlm_password,
            ntlm_domain=ntlm_domain,
            verify_ssl=verify_ssl,
        )

