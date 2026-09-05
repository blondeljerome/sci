"""
Module de configuration pour l'application SCI.
Gère les variables d'environnement, les secrets Streamlit et les identifiants Turso.
"""
import os
from typing import Tuple, Optional
import streamlit as st

def get_turso_credentials() -> Tuple[Optional[str], Optional[str], bool]:
    """
    Récupère l'URL et le Token de Turso depuis :
    1. Streamlit Secrets (st.secrets["TURSO_DATABASE_URL"] / st.secrets["TURSO_AUTH_TOKEN"])
    2. Variables d'environnement système (TURSO_DATABASE_URL / TURSO_AUTH_TOKEN)
    3. Fallback SQLite local dans 'data/sci_local.db'

    Retourne : (db_url, auth_token, is_turso)
    """
    url: Optional[str] = None
    token: Optional[str] = None

    # 1. Tentative via st.secrets
    try:
        if hasattr(st, "secrets"):
            url = st.secrets.get("TURSO_DATABASE_URL")
            token = st.secrets.get("TURSO_AUTH_TOKEN")
    except Exception:
        pass

    # 2. Tentative via os.environ
    if not url:
        url = os.environ.get("TURSO_DATABASE_URL")
    if not token:
        token = os.environ.get("TURSO_AUTH_TOKEN")

    # Si nous avons une URL Turso (libsql:// ou https://)
    if url and ("turso.io" in url or url.startswith("libsql://") or url.startswith("https://")):
        # Normalisation : libsql-client en HTTP synchrone utilise https://
        if url.startswith("libsql://"):
            url = "https://" + url[len("libsql://"):]
        return url, token, True

    # 3. Fallback local SQLite
    os.makedirs("data", exist_ok=True)
    local_db_path = os.path.abspath("data/sci_local.db")
    local_url = f"file:{local_db_path}"
    return local_url, None, False
