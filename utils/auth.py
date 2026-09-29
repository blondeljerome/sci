"""Module d'authentification et de gestion de la sécurité pour la SCI.

Utilise PBKDF2-HMAC-SHA256 (bibliothèque standard) pour un hachage
cryptographique robuste.
"""

import hashlib
import hmac
import secrets
from typing import Any

from database import execute_write, query_one, query_rows

ITERATIONS = 100_000
HASH_NAME = "sha256"


def hash_password(password: str) -> str:
    """Génère un hachage sécurisé PBKDF2-HMAC-SHA256.

    Format retourné : pbkdf2_sha256$<iterations>$<salt>$<hash>

    Args:
        password: Mot de passe en clair.

    Returns:
        Chaîne de hachage encodée avec sel.
    """
    salt = secrets.token_hex(16)
    pw_hash = hashlib.pbkdf2_hmac(
        HASH_NAME, password.encode("utf-8"), salt.encode("utf-8"), ITERATIONS
    ).hex()
    return f"pbkdf2_{HASH_NAME}${ITERATIONS}${salt}${pw_hash}"


def verify_password(password: str, hashed: str) -> bool:
    """Vérifie si le mot de passe correspond au hachage stocké.

    Utilise hmac.compare_digest pour prévenir les attaques temporelles.

    Args:
        password: Mot de passe saisi en clair.
        hashed: Hachage stocké en base de données.

    Returns:
        True si valide, False sinon.
    """
    if not hashed or not password:
        return False

    parts = hashed.split("$")
    if len(parts) != 4:
        return False

    algo, iters_str, salt, expected_hash = parts
    if not algo.endswith(HASH_NAME):
        return False

    try:
        iterations = int(iters_str)
    except ValueError:
        return False

    computed_hash = hashlib.pbkdf2_hmac(
        HASH_NAME, password.encode("utf-8"), salt.encode("utf-8"), iterations
    ).hex()

    return hmac.compare_digest(computed_hash, expected_hash)


def authenticate(username: str, password: str) -> dict[str, Any] | None:
    """Authentifie un utilisateur par son identifiant et mot de passe.

    Met à jour la date de dernière connexion si succès.

    Args:
        username: Identifiant de connexion.
        password: Mot de passe en clair.

    Returns:
        Dictionnaire utilisateur (sans le hash) ou None si échec.
    """
    if not username or not password:
        return None

    clean_username = username.strip().lower()
    user = query_one(
        "SELECT id, username, password_hash, full_name, email, role, is_active "
        "FROM users WHERE LOWER(username) = ?;",
        [clean_username],
    )

    if not user:
        return None

    if not user.get("is_active", 1):
        return None

    if not verify_password(password, user.get("password_hash", "")):
        return None

    # Mise à jour de la date de dernière connexion
    try:
        execute_write(
            "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?;",
            [user["id"]],
        )
    except Exception:
        pass

    # Ne pas exposer le hash dans la session
    user_copy = dict(user)
    user_copy.pop("password_hash", None)
    return user_copy


def change_password(
    user_id: int, current_password: str, new_password: str
) -> tuple[bool, str]:
    """Modifie le mot de passe d'un utilisateur après vérification de l'ancien.

    Args:
        user_id: Identifiant de l'utilisateur.
        current_password: Mot de passe actuel.
        new_password: Nouveau mot de passe souhaité.

    Returns:
        Tuple (succès: bool, message: str).
    """
    if not new_password or len(new_password) < 6:
        return (
            False,
            "Le nouveau mot de passe doit comporter au moins 6 caractères.",
        )

    user = query_one(
        "SELECT password_hash FROM users WHERE id = ?;", [user_id]
    )
    if not user:
        return False, "Utilisateur introuvable."

    if not verify_password(current_password, user.get("password_hash", "")):
        return False, "Le mot de passe actuel est incorrect."

    new_hash = hash_password(new_password)
    try:
        execute_write(
            "UPDATE users SET password_hash = ? WHERE id = ?;",
            [new_hash, user_id],
        )
        return True, "Mot de passe modifié avec succès !"
    except Exception as e:
        return False, f"Erreur lors de la mise à jour : {e}"


def update_user_profile(
    user_id: int, full_name: str, email: str
) -> tuple[bool, str]:
    """Met à jour les informations de profil (nom complet, email).

    Args:
        user_id: Identifiant de l'utilisateur.
        full_name: Nom complet de l'associé.
        email: Adresse email de contact.

    Returns:
        Tuple (succès: bool, message: str).
    """
    if not full_name or not full_name.strip():
        return False, "Le nom complet est obligatoire."

    try:
        execute_write(
            "UPDATE users SET full_name = ?, email = ? WHERE id = ?;",
            [full_name.strip(), email.strip(), user_id],
        )
        return True, "Profil mis à jour avec succès !"
    except Exception as e:
        return False, f"Erreur lors de la mise à jour : {e}"


def get_all_users() -> list[dict[str, Any]]:
    """Retourne la liste des utilisateurs enregistrés (sans mot de passe).

    Returns:
        Liste de dictionnaires représentant les utilisateurs.
    """
    return query_rows(
        "SELECT id, username, full_name, email, role, is_active, "
        "last_login, created_at FROM users ORDER BY id ASC;"
    )


def init_default_users() -> None:
    """Initialise les 2 utilisateurs par défaut s'ils n'existent pas encore.

    1. jerome (Jérôme Blondel)
    2. claire (Claire Ané)
    Mot de passe initial par défaut : sci2026!
    """
    default_users = [
        {
            "username": "jerome",
            "full_name": "Jérôme Blondel",
            "email": "",
            "role": "admin",
            "default_password": "sci2026!",
        },
        {
            "username": "claire",
            "full_name": "Claire Ané",
            "email": "",
            "role": "admin",
            "default_password": "sci2026!",
        },
    ]

    for u in default_users:
        existing = query_one(
            "SELECT id FROM users WHERE LOWER(username) = ?;", [u["username"]]
        )
        if not existing:
            hashed = hash_password(u["default_password"])
            try:
                execute_write(
                    """
                    INSERT INTO users (username, password_hash, full_name,
                                       email, role, is_active)
                    VALUES (?, ?, ?, ?, ?, 1);
                    """,
                    [
                        u["username"],
                        hashed,
                        u["full_name"],
                        u["email"],
                        u["role"],
                    ],
                )
            except Exception:
                pass
