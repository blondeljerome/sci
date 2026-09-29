"""Module de configuration centralisé pour l'application SCI.

Gère les variables d'environnement, les secrets Streamlit, les identifiants
des services externes (Turso, Cloudinary, SMTP) ainsi que les constantes
globales de l'application et les paramètres de sécurité d'upload.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

import streamlit as st

logger = logging.getLogger("sci.config")

# --- Constantes Applicatives ---
APP_TITLE: str = "Gestion SCI à l'IS"
APP_ICON: str = "🏢"
DEFAULT_CURRENCY: str = "€"

# --- Paramètres Fiscaux (Régime IS) ---
IS_REDUCED_RATE: float = 0.15
IS_NORMAL_RATE: float = 0.25
IS_REDUCED_RATE_CEILING: float = 42500.0
DEFAULT_LAND_SHARE_PCT: float = 15.0
DEFAULT_BUILDING_AMORT_YEARS: int = 25
DEFAULT_FURNITURE_AMORT_YEARS: int = 5

# --- Sécurité & Téléversement de Documents (GED) ---
MAX_UPLOAD_SIZE_BYTES: int = 15 * 1024 * 1024  # 15 Mo
ALLOWED_UPLOAD_EXTENSIONS: tuple[str, ...] = (
    ".pdf",
    ".png",
    ".jpg",
    ".jpeg",
    ".docx",
    ".xlsx",
    ".txt",
)


def get_turso_credentials() -> tuple[str | None, str | None, bool]:
    """Récupère l'URL et le Token de Turso depuis secrets, env ou fallback.

    Returns:
        Un tuple (db_url, auth_token, is_turso).
    """
    url: str | None = None
    token: str | None = None

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
    if url and (
        "turso.io" in url
        or url.startswith("libsql://")
        or url.startswith("https://")
    ):
        if url.startswith("libsql://"):
            url = "https://" + url[len("libsql://") :]
        return url, token, True

    # 3. Fallback local SQLite
    data_dir = Path("data")
    data_dir.mkdir(parents=True, exist_ok=True)
    local_db_path = (data_dir / "sci_local.db").resolve()
    local_url = f"file:{local_db_path}"
    return local_url, None, False


def get_cloudinary_credentials() -> tuple[
    str | None, str | None, str | None
]:
    """Récupère les identifiants Cloudinary depuis st.secrets ou os.environ.

    Returns:
        Un tuple (cloud_name, api_key, api_secret).
    """
    cloud_name: str | None = None
    api_key: str | None = None
    api_secret: str | None = None

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
    """Initialise le SDK Cloudinary avec les identifiants disponibles.

    Returns:
        True si la configuration a réussi, False sinon.
    """
    import cloudinary

    cloud_name, api_key, api_secret = get_cloudinary_credentials()
    if cloud_name and api_key and api_secret:
        cloudinary.config(
            cloud_name=cloud_name,
            api_key=api_key,
            api_secret=api_secret,
            secure=True,
        )
        return True
    return False


def validate_file_upload(
    filename: str,
    file_bytes: bytes,
    max_size: int = MAX_UPLOAD_SIZE_BYTES,
    allowed_exts: tuple[str, ...] = ALLOWED_UPLOAD_EXTENSIONS,
) -> tuple[bool, str | None]:
    """Valide la taille et l'extension d'un document avant téléversement.

    Args:
        filename: Nom du fichier avec son extension.
        file_bytes: Contenu brut du fichier en octets.
        max_size: Taille maximale autorisée en octets.
        allowed_exts: Tuple d'extensions autorisées en minuscules.

    Returns:
        Un tuple (est_valide, message_erreur_optionnel).
    """
    clean_name = Path(filename.strip()).name if filename else ""
    if not clean_name or not file_bytes:
        return False, "Le fichier est vide ou invalide."

    ext = Path(clean_name.lower()).suffix
    if ext not in allowed_exts:
        valid_list = ", ".join(allowed_exts)
        return (
            False,
            f"Format de fichier non autorisé ({ext}). "
            f"Formats acceptés : {valid_list}.",
        )

    if len(file_bytes) > max_size:
        max_mb = max_size / (1024 * 1024)
        actual_mb = len(file_bytes) / (1024 * 1024)
        return (
            False,
            f"Fichier trop volumineux ({actual_mb:.1f} Mo). "
            f"La taille maximale autorisée est de {max_mb:.0f} Mo.",
        )

    return True, None
