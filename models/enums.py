"""Définitions d'énumérations fortement typées pour le domaine métier SCI.

Conforme au Google Python Style Guide et utilisant StrEnum pour la
compatibilité avec les chaînes enregistrées en base SQLite/Turso.
"""

from enum import StrEnum


class PropertyStatus(StrEnum):
    """Statuts d'occupation d'un bien immobilier."""
    VACANT = "vacant"
    LOUE = "loue"
    EN_TRAVAUX = "en_travaux"


class PropertyType(StrEnum):
    """Typologies de biens gérés au patrimoine."""
    APPARTEMENT = "Appartement"
    MAISON = "Maison"
    PARKING = "Parking / Garage"
    LOCAL_COMMERCIAL = "Local Commercial"
    IMMEUBLE = "Immeuble de rapport"
    CAVE = "Cave / Box"
    AUTRE = "Autre"


class RentStatus(StrEnum):
    """Statuts d'une échéance de loyer."""
    EN_ATTENTE = "en_attente"
    PARTIEL = "partiel"
    PAYE = "paye"
    RETARD = "retard"
    ANNULE = "annule"


class PartnerAccountType(StrEnum):
    """Type d'opération sur un compte courant d'associé (CCA)."""
    APPORT = "apport"
    REMBOURSEMENT = "remboursement"


class EntityType(StrEnum):
    """Type d'entité rattachée à un document GED."""
    SCI = "sci"
    PROPERTY = "property"
    TENANT = "tenant"
    LOAN = "loan"


class DocumentCategory(StrEnum):
    """Catégories de classement pour la GED et le coffre-fort numérique."""
    BAIL_ETAT_DES_LIEUX = "Bail & État des lieux"
    ASSURANCE = "Attestation d'assurance habitation"
    DIAGNOSTIC = "Diagnostic technique (DPE, plomb, élec...)"
    FACTURE_TRAVAUX = "Facture / Devis de travaux"
    TAXE_FONCIERE = "Taxe foncière / Avis d'imposition"
    COPROPRIETE = "Appel de fonds de copropriété"
    STATUTS_KBIS = "Statuts, Kbis & Documents SCI"
    OFFRE_PRET = "Offre de prêt & Contrat de crédit"
    QUITTANCE = "Quittance & Reçu de paiement"
    APPEL_LOYER = "Appel de loyer & Avis d'échéance"
    AUTRE = "Autre pièce justificative"


class UserRole(StrEnum):
    """Rôles applicatifs des utilisateurs."""
    ADMIN = "admin"
    GESTIONNAIRE = "gestionnaire"
