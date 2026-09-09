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


def get_cloudinary_credentials() -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Récupère les identifiants Cloudinary depuis :
    1. Streamlit Secrets (CLOUDINARY_CLOUD_NAME / CLOUDINARY_API_KEY / CLOUDINARY_API_SECRET)
    2. Variables d'environnement système

    Retourne : (cloud_name, api_key, api_secret)
    """
    cloud_name: Optional[str] = None
    api_key: Optional[str] = None
    api_secret: Optional[str] = None

    # 1. Tentative via st.secrets
    try:
        if hasattr(st, "secrets"):
            cloud_name = st.secrets.get("CLOUDINARY_CLOUD_NAME")
            api_key = st.secrets.get("CLOUDINARY_API_KEY")
            api_secret = st.secrets.get("CLOUDINARY_API_SECRET")
    except Exception:
        pass

    # 2. Tentative via os.environ
    if not cloud_name:
        cloud_name = os.environ.get("CLOUDINARY_CLOUD_NAME")
    if not api_key:
        api_key = os.environ.get("CLOUDINARY_API_KEY")
    if not api_secret:
        api_secret = os.environ.get("CLOUDINARY_API_SECRET")

    return cloud_name, api_key, api_secret


def configure_cloudinary() -> bool:
    """
    Initialise le SDK Cloudinary avec les credentials disponibles.
    Retourne True si la configuration a réussi, False sinon.
    """
    import cloudinary
    cloud_name, api_key, api_secret = get_cloudinary_credentials()
    if cloud_name and api_key and api_secret:
        cloudinary.config(
            cloud_name=cloud_name,
            api_key=api_key,
            api_secret=api_secret,
            secure=True
        )
        return True
    return False
