"""
Module de stockage centralisé pour la GED (Gestion Électronique des Documents).
Utilise Cloudinary comme backend de stockage cloud persistant.
"""
from __future__ import annotations
from typing import Tuple, Optional
import cloudinary
import cloudinary.uploader
import cloudinary.api
from config import configure_cloudinary

# Dossier Cloudinary où seront rangés tous les documents GED
CLOUDINARY_FOLDER = "sci-ged"


def _ensure_configured() -> None:
    """Configure Cloudinary si ce n'est pas encore fait."""
    if not cloudinary.config().cloud_name:
        ok = configure_cloudinary()
        if not ok:
            raise RuntimeError(
                "Cloudinary n'est pas configuré. "
                "Veuillez définir CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY "
                "et CLOUDINARY_API_SECRET dans vos secrets ou variables d'environnement."
            )


def upload_file(
    file_bytes: bytes,
    original_filename: str,
    folder: str = CLOUDINARY_FOLDER,
) -> Tuple[str, str, int]:
    """
    Upload un fichier vers Cloudinary.

    Args:
        file_bytes: Contenu brut du fichier.
        original_filename: Nom original du fichier (utilisé pour le public_id et le resource_type).
        folder: Dossier Cloudinary de destination.

    Returns:
        (public_id, secure_url, file_size_bytes)
    """
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
                return True
        except Exception:
            pass

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
    return cloudinary.CloudinaryImage(public_id).build_url(secure=True, resource_type=resource_type)
