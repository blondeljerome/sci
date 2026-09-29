"""
Couche d'accès aux données pour l'application SCI à l'IS.
Prend en charge Turso (libsql:// ou https://) et le repli local SQLite.
Fournit le support des transactions atomiques et de la journalisation.
"""

import logging
import os
import re
from typing import Any, Dict, List, Optional, Tuple, Union

import libsql_client
import pandas as pd

from config import get_turso_credentials

# Configuration du logger pour la couche base de données
logger = logging.getLogger("sci.database")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter("[%(asctime)s] [%(levelname)s] [sci.db]: %(message)s")
    )
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


def get_client() -> libsql_client.Client:
    """
    Crée et retourne une instance de client libsql synchronisé.
    """
    url, token, is_turso = get_turso_credentials()
    if is_turso:
        return libsql_client.create_client_sync(url, auth_token=token)
    else:
        return libsql_client.create_client_sync(url)


def get_connection_info() -> Dict[str, Any]:
    """
    Retourne des informations sur la connexion courante.
    """
    url, token, is_turso = get_turso_credentials()
    masked_token = None
    if token:
        masked_token = (
            token[:8] + "..." + token[-6:] if len(token) > 14 else "***"
        )
    return {
        "url": url,
        "is_turso": is_turso,
        "has_token": bool(token),
        "masked_token": masked_token,
    }


def init_db() -> None:
    """Initialise la base de données en exécutant schema.sql.

    Assure la compatibilité des colonnes pour l'IS, les emprunts,
    l'IRL, les docs et le SMTP.
    """
    logger.info("Initialisation de la base de données...")
    client = get_client()
    try:
        schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
        with open(schema_path, "r", encoding="utf-8") as f:
            content = f.read()

        cleaned_content = re.sub(r"--.*$", "", content, flags=re.MULTILINE)
        raw_statements = cleaned_content.split(";")

        for stmt in raw_statements:
            sql = stmt.strip()
            if sql:
                try:
                    client.execute(sql)
                except Exception as err:
                    logger.debug(
                        "Statement initial ignoré ou déjà appliqué: %s (%s)",
                        sql[:40],
                        err,
                    )

        # 1. Migration properties (colonnes IS)
        try:
            rs = client.execute("PRAGMA table_info(properties);")
            existing_cols = [row[1] for row in rs.rows]
            for col_name, col_type in [
                ("notary_fees", "REAL DEFAULT 0.0"),
                ("land_share_pct", "REAL DEFAULT 15.0"),
                ("amortization_years", "INTEGER DEFAULT 25"),
                ("furniture_value", "REAL DEFAULT 0.0"),
                ("furniture_years", "INTEGER DEFAULT 5"),
            ]:
                if col_name not in existing_cols:
                    client.execute(
                        f"ALTER TABLE properties "
                        f"ADD COLUMN {col_name} {col_type};"
                    )
                    logger.info(
                        "Colonne properties.%s ajoutée avec succès.", col_name
                    )
        except Exception as err:
            logger.warning("Erreur vérification migration properties: %s", err)

        # 2. Migration sci_info (SMTP + régime fiscal + capital social)
        try:
            rs_sci = client.execute("PRAGMA table_info(sci_info);")
            sci_cols = [row[1] for row in rs_sci.rows]
            for col_name, col_type in [
                ("tax_regime", "TEXT DEFAULT 'IS'"),
                ("share_capital", "REAL DEFAULT 1000.0"),
                ("smtp_server", "TEXT DEFAULT ''"),
                ("smtp_port", "INTEGER DEFAULT 587"),
                ("smtp_username", "TEXT DEFAULT ''"),
                ("smtp_password", "TEXT DEFAULT ''"),
                ("smtp_use_tls", "INTEGER DEFAULT 1"),
                ("smtp_sender_email", "TEXT DEFAULT ''"),
            ]:
                if col_name not in sci_cols:
                    client.execute(
                        f"ALTER TABLE sci_info "
                        f"ADD COLUMN {col_name} {col_type};"
                    )
                    logger.info(
                        "Colonne sci_info.%s ajoutée avec succès.", col_name
                    )
        except Exception as err:
            logger.warning("Erreur vérification migration sci_info: %s", err)

        # 3. Migration tenants (IRL)
        try:
            rs_t = client.execute("PRAGMA table_info(tenants);")
            tenant_cols = [row[1] for row in rs_t.rows]
            for col_name, col_type in [
                ("irl_reference_quarter", "TEXT DEFAULT 'T3 2024'"),
                ("irl_reference_value", "REAL DEFAULT 144.51"),
                ("last_revision_date", "TEXT DEFAULT ''"),
            ]:
                if col_name not in tenant_cols:
                    client.execute(
                        f"ALTER TABLE tenants "
                        f"ADD COLUMN {col_name} {col_type};"
                    )
                    logger.info(
                        "Colonne tenants.%s ajoutée avec succès.", col_name
                    )
        except Exception as err:
            logger.warning("Erreur vérification migration tenants: %s", err)

        # 4. Migration documents (Cloudinary, property_id, tenant_id)
        try:
            rs_d = client.execute("PRAGMA table_info(documents);")
            doc_cols = [row[1] for row in rs_d.rows]
            if "cloudinary_public_id" not in doc_cols:
                client.execute(
                    "ALTER TABLE documents "
                    "ADD COLUMN cloudinary_public_id TEXT DEFAULT '';"
                )
                logger.info("Colonne documents.cloudinary_public_id ajoutée.")
            if "property_id" not in doc_cols:
                client.execute(
                    "ALTER TABLE documents ADD COLUMN property_id INTEGER;"
                )
                logger.info("Colonne documents.property_id ajoutée.")
            if "tenant_id" not in doc_cols:
                client.execute(
                    "ALTER TABLE documents ADD COLUMN tenant_id INTEGER;"
                )
                logger.info("Colonne documents.tenant_id ajoutée.")
        except Exception as err:
            logger.warning("Erreur vérification migration documents: %s", err)

        # 5. Migration table partners
        try:
            client.execute("""
                CREATE TABLE IF NOT EXISTS partners (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    email TEXT DEFAULT '',
                    phone TEXT DEFAULT '',
                    shares INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            client.execute("""
                INSERT OR IGNORE INTO partners (name)
                SELECT DISTINCT partner_name
                FROM partner_accounts
                WHERE partner_name != '';
            """)
        except Exception as err:
            logger.warning("Erreur vérification migration partners: %s", err)

        # 6. Migration rent_payments (document_id et notice_document_id)
        try:
            rs_r = client.execute("PRAGMA table_info(rent_payments);")
            rent_cols = [row[1] for row in rs_r.rows]
            if "document_id" not in rent_cols:
                client.execute(
                    "ALTER TABLE rent_payments ADD COLUMN document_id INTEGER;"
                )
                logger.info("Colonne rent_payments.document_id ajoutée.")
            if "notice_document_id" not in rent_cols:
                client.execute(
                    "ALTER TABLE rent_payments "
                    "ADD COLUMN notice_document_id INTEGER;"
                )
                logger.info("Colonne rent_payments.notice_document_id ajoutée.")
        except Exception as err:
            logger.warning(
                "Erreur vérification migration rent_payments: %s", err
            )

    finally:
        client.close()

    # Initialisation des 2 utilisateurs par défaut
    try:
        from utils.auth import init_default_users

        init_default_users()
    except Exception as err:
        logger.warning(
            "Erreur lors de l'initialisation des utilisateurs par défaut: %s",
            err,
        )


def query_df(sql: str, params: Optional[List[Any]] = None) -> pd.DataFrame:
    """
    Exécute une requête SELECT et retourne un DataFrame Pandas.
    """
    client = get_client()
    try:
        rs = client.execute(sql, params or [])
        columns = list(rs.columns)
        rows = [list(row) for row in rs.rows]
        return pd.DataFrame(rows, columns=columns)
    finally:
        client.close()


def query_rows(
    sql: str, params: Optional[List[Any]] = None
) -> List[Dict[str, Any]]:
    """
    Exécute une requête SELECT et retourne une liste de dictionnaires.
    """
    client = get_client()
    try:
        rs = client.execute(sql, params or [])
        columns = list(rs.columns)
        result = []
        for row in rs.rows:
            result.append(dict(zip(columns, row)))
        return result
    finally:
        client.close()


def query_one(
    sql: str, params: Optional[List[Any]] = None
) -> Optional[Dict[str, Any]]:
    """Exécute une requête SELECT et retourne la première ligne.

    Args:
        sql: Requête SQL à exécuter.
        params: Paramètres de la requête.

    Returns:
        Dictionnaire représentant la ligne, ou None si aucun résultat.
    """
    rows = query_rows(sql, params)
    return rows[0] if rows else None


def execute_write(sql: str, params: Optional[List[Any]] = None) -> int:
    """Exécute une requête d'écriture unique (INSERT, UPDATE, DELETE).

    Args:
        sql: Requête SQL d'écriture.
        params: Paramètres de la requête.

    Returns:
        last_insert_rowid si disponible, sinon rows_affected.
    """
    client = get_client()
    try:
        rs = client.execute(sql, params or [])
        if rs.last_insert_rowid is not None:
            return rs.last_insert_rowid
        return rs.rows_affected
    finally:
        client.close()


def execute_batch(
    statements: List[Union[str, Tuple[str, List[Any]]]],
) -> List[Any]:
    """Exécute une liste d'instructions SQL dans une transaction atomique.

    Si l'une des instructions échoue, toutes les modifications sont
    automatiquement annulées (Rollback).

    Args:
        statements: Liste de requêtes SQL (chaînes de caractères ou tuples
            (sql, [paramètres])).

    Returns:
        Liste des résultats ResultSet retournés par le client libsql.

    Raises:
        Exception: Relance toute erreur survenue pendant l'exécution du lot.
    """
    if not statements:
        return []

    client = get_client()
    try:
        logger.debug(
            "Exécution d'un lot atomique de %d requêtes SQL...", len(statements)
        )
        results = client.batch(statements)
        return results
    except Exception as err:
        logger.error(
            "Échec de la transaction atomique (rollback automatique): %s", err
        )
        raise
    finally:
        client.close()
