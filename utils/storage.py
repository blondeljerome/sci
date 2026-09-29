"""Module de stockage centralisé pour la GED.

Utilise Cloudinary comme backend de stockage cloud persistant.
"""

from __future__ import annotations

import logging
import os
from typing import Optional, Tuple

import cloudinary
import cloudinary.api
import cloudinary.uploader

from config import configure_cloudinary, validate_file_upload

logger = logging.getLogger("sci.storage")

# Dossier Cloudinary où seront rangés tous les documents GED
CLOUDINARY_FOLDER = "sci-ged"


def _ensure_configured() -> None:
    """Configure Cloudinary si ce n'est pas encore fait."""
    if not cloudinary.config().cloud_name:
        ok = configure_cloudinary()
        if not ok:
            raise RuntimeError(
                "Cloudinary n'est pas configuré. Veuillez définir "
                "CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY et "
                "CLOUDINARY_API_SECRET dans vos secrets ou variables "
                "d'environnement."
            )


def upload_file(
    file_bytes: bytes,
    original_filename: str,
    folder: str = CLOUDINARY_FOLDER,
) -> Tuple[str, str, int]:
    """Upload un fichier vers Cloudinary après validation de conformité.

    Args:
        file_bytes: Contenu brut du fichier.
        original_filename: Nom original du fichier.
        folder: Dossier Cloudinary de destination.

    Returns:
        (public_id, secure_url, file_size_bytes)

    Raises:
        ValueError: Si le fichier ne respecte pas les critères de format.
        RuntimeError: Si Cloudinary n'est pas configuré.
    """
    clean_filename = os.path.basename(original_filename.strip())
    is_valid, err_msg = validate_file_upload(clean_filename, file_bytes)
    if not is_valid:
        raise ValueError(err_msg or "Fichier invalide pour téléversement.")

    _ensure_configured()

    # Cloudinary gère nativement PDF, images, etc. via resource_type="auto"
    result = cloudinary.uploader.upload(
        file_bytes,
        folder=folder,
        use_filename=True,
        unique_filename=True,
        overwrite=False,
        resource_type="auto",
    )

    public_id: str = result["public_id"]
    secure_url: str = result["secure_url"]
    file_size: int = result.get("bytes", len(file_bytes))

    return public_id, secure_url, file_size


def delete_file(public_id: str) -> bool:
    """
    Supprime un fichier depuis Cloudinary.
    Tente successivement les resource_types "raw", "image" et "video"
    car l'API delete ne supporte pas resource_type="auto".

    Args:
        public_id: L'identifiant Cloudinary du fichier.

    Returns:
        True si la suppression a réussi, False sinon.
    """
    if not public_id:
        return False

    _ensure_configured()

    for rt in ("raw", "image", "video"):
        try:
            res = cloudinary.uploader.destroy(public_id, resource_type=rt)
            if res.get("result") == "ok":
                logger.info(
                    "Fichier Cloudinary supprimé avec succès: %s (type: %s)",
                    public_id,
                    rt,
                )
                return True
        except Exception as err:
            logger.debug(
                "Tentative suppression Cloudinary (%s) échouée: %s", rt, err
            )

    logger.warning(
        "Échec de la suppression Cloudinary pour public_id=%s", public_id
    )
    return False


def get_file_url(public_id: str, resource_type: str = "raw") -> Optional[str]:
    """
    Retourne l'URL publique sécurisée (HTTPS) d'un fichier Cloudinary.

    Args:
        public_id: L'identifiant Cloudinary du fichier.
        resource_type: "image", "video" ou "raw".

    Returns:
        URL HTTPS ou None si public_id est vide.
    """
    if not public_id:
        return None

    _ensure_configured()
    import cloudinary.utils

    url, _ = cloudinary.utils.cloudinary_url(
        public_id,
        resource_type=resource_type,
        secure=True,
    )
    return url


def get_preview_url(public_id: str, original_url: str = "") -> str:
    """Retourne une URL Cloudinary optimisée pour la prévisualisation.

    Pour les PDF, génère une URL PNG (page 1) pour affichage direct
    sans blocage ACL / 401 CDN.

    Args:
        public_id: L'identifiant Cloudinary du fichier.
        original_url: URL de fallback en cas d'erreur.

    Returns:
        URL HTTPS de prévisualisation ou l'originale si échec.
    """
    if not public_id:
        return original_url or ""

    _ensure_configured()
    import cloudinary.utils

    try:
        # Conversion instantanée sur Cloudinary vers PNG (page 1)
        preview_url, _ = cloudinary.utils.cloudinary_url(
            public_id, resource_type="image", format="png", secure=True
        )
        return preview_url
    except Exception:
        return original_url or ""


def download_file_bytes(
    public_id: str, resource_type: str = "image"
) -> Optional[bytes]:
    """Télécharge le contenu binaire brut d'un document Cloudinary.

    Contourne toute restriction CDN publique via l'API signée.

    Args:
        public_id: L'identifiant Cloudinary du fichier.
        resource_type: Type de ressource ("image", "raw", etc.).

    Returns:
        Contenu brut du fichier sous forme de bytes, ou None.
    """
    if not public_id:
        return None

    _ensure_configured()
    import io
    import urllib.request
    import zipfile

    import cloudinary.utils

    for rt in (resource_type, "image", "raw"):
        try:
            zip_url = cloudinary.utils.download_zip_url(
                public_ids=[public_id], resource_type=rt
            )
            req = urllib.request.Request(
                zip_url, headers={"User-Agent": "Mozilla/5.0"}
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = resp.read()
                z = zipfile.ZipFile(io.BytesIO(data))
                names = z.namelist()
                if names:
                    return z.read(names[0])
        except Exception:
            continue

    return None
