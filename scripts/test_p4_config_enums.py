"""Tests unitaires pour la Phase P4 : Configuration, Enums et Sécurité.

Conforme au Google Python Style Guide.
"""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import (
    APP_ICON,
    APP_TITLE,
    DEFAULT_CURRENCY,
    IS_NORMAL_RATE,
    IS_REDUCED_RATE,
    IS_REDUCED_RATE_CEILING,
    MAX_UPLOAD_SIZE_BYTES,
    get_cloudinary_credentials,
    get_turso_credentials,
    validate_file_upload,
)
from models.enums import (
    DocumentCategory,
    PartnerAccountType,
    PropertyStatus,
    RentStatus,
)
from utils.storage import upload_file


class TestConfiguration(unittest.TestCase):
    """Vérifie l'intégrité des constantes et helpers de configuration."""

    def test_constants_presence_and_values(self) -> None:
        """Vérifie que les constantes applicatives ont des valeurs valides."""
        self.assertIsInstance(APP_TITLE, str)
        self.assertGreater(len(APP_TITLE), 0)
        self.assertIsInstance(APP_ICON, str)
        self.assertEqual(DEFAULT_CURRENCY, "€")

        # Paramètres fiscaux IS
        self.assertEqual(IS_REDUCED_RATE, 0.15)
        self.assertEqual(IS_NORMAL_RATE, 0.25)
        self.assertEqual(IS_REDUCED_RATE_CEILING, 42500.0)

    def test_turso_credentials_fallback(self) -> None:
        """Vérifie que la configuration Turso retourne un tuple valide."""
        url, token, is_turso = get_turso_credentials()
        self.assertIsNotNone(url)
        self.assertIsInstance(is_turso, bool)
        if not is_turso:
            self.assertTrue(url.startswith("file:"))

    def test_cloudinary_credentials_format(self) -> None:
        """Vérifie la forme des identifiants Cloudinary."""
        cloud_name, api_key, api_secret = get_cloudinary_credentials()
        # Peut être None dans l'environnement de test bare
        self.assertTrue(cloud_name is None or isinstance(cloud_name, str))
        self.assertTrue(api_key is None or isinstance(api_key, str))
        self.assertTrue(api_secret is None or isinstance(api_secret, str))


class TestFileUploadValidation(unittest.TestCase):
    """Vérifie les règles de validation et sécurité des fichiers téléversés."""

    def test_valid_pdf_upload(self) -> None:
        """Un fichier PDF valide doit être accepté."""
        sample_bytes = b"%PDF-1.4 sample content"
        is_valid, err = validate_file_upload("contrat_bail.pdf", sample_bytes)
        self.assertTrue(is_valid)
        self.assertIsNone(err)

    def test_valid_image_upload(self) -> None:
        """Les images autorisées (PNG, JPG) doivent être acceptées."""
        sample_bytes = b"\x89PNG\r\n\x1a\nfakeimage"
        is_valid, err = validate_file_upload("diagnostic.png", sample_bytes)
        self.assertTrue(is_valid)
        self.assertIsNone(err)

    def test_forbidden_extension_rejected(self) -> None:
        """Les fichiers exécutables ou scripts doivent être rejetés."""
        forbidden_files = ["virus.exe", "script.sh", "code.py", "archive.zip"]
        dummy_bytes = b"echo 'dangerous'"
        for fname in forbidden_files:
            is_valid, err = validate_file_upload(fname, dummy_bytes)
            self.assertFalse(is_valid)
            self.assertIsNotNone(err)
            self.assertIn("non autorisé", err)

    def test_file_size_exceeded_rejected(self) -> None:
        """Un fichier excédant la limite autorisée doit être rejeté."""
        # Limite par défaut : 15 Mo
        oversized_bytes = b"0" * (MAX_UPLOAD_SIZE_BYTES + 1024)
        is_valid, err = validate_file_upload(
            "gros_fichier.pdf", oversized_bytes
        )
        self.assertFalse(is_valid)
        self.assertIsNotNone(err)
        self.assertIn("trop volumineux", err)

    def test_empty_file_rejected(self) -> None:
        """Un fichier vide ou sans nom doit être rejeté."""
        is_valid, err = validate_file_upload("", b"data")
        self.assertFalse(is_valid)

        is_valid_bytes, _ = validate_file_upload("vide.pdf", b"")
        self.assertFalse(is_valid_bytes)

    def test_storage_upload_file_raises_on_invalid_extension(self) -> None:
        """storage.upload_file doit lever ValueError si extension invalide."""
        with self.assertRaises(ValueError):
            upload_file(b"content", "malicious_script.sh")


class TestEnumsIntegrity(unittest.TestCase):
    """Vérifie la conformité et l'exhaustivité des énumérations typées."""

    def test_property_status_values(self) -> None:
        """Vérifie les valeurs textuelles de PropertyStatus."""
        self.assertEqual(PropertyStatus.VACANT.value, "vacant")
        self.assertEqual(PropertyStatus.LOUE.value, "loue")
        self.assertEqual(PropertyStatus.EN_TRAVAUX.value, "en_travaux")

    def test_rent_status_values(self) -> None:
        """Vérifie les valeurs textuelles de RentStatus."""
        self.assertEqual(RentStatus.EN_ATTENTE.value, "en_attente")
        self.assertEqual(RentStatus.PAYE.value, "paye")
        self.assertEqual(RentStatus.PARTIEL.value, "partiel")
        self.assertEqual(RentStatus.RETARD.value, "retard")

    def test_partner_account_type_values(self) -> None:
        """Vérifie les valeurs textuelles de PartnerAccountType."""
        self.assertEqual(PartnerAccountType.APPORT.value, "apport")
        self.assertEqual(
            PartnerAccountType.REMBOURSEMENT.value, "remboursement"
        )

    def test_document_category_values(self) -> None:
        """Vérifie que DocumentCategory contient les catégories requises."""
        categories = [cat.value for cat in DocumentCategory]
        self.assertIn("Bail & État des lieux", categories)
        self.assertIn("Quittance & Reçu de paiement", categories)
        self.assertIn("Appel de loyer & Avis d'échéance", categories)
        self.assertIn("Facture / Devis de travaux", categories)


if __name__ == "__main__":
    unittest.main()
