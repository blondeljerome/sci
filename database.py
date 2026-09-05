"""
Couche d'accès aux données pour l'application SCI à l'IS.
Prend en charge Turso (libsql:// ou https://) et le repli local SQLite.
"""
import os
import re
from typing import List, Dict, Any, Optional, Tuple
import pandas as pd
import libsql_client
from config import get_turso_credentials

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
        masked_token = token[:8] + "..." + token[-6:] if len(token) > 14 else "***"
    return {
        "url": url,
        "is_turso": is_turso,
        "has_token": bool(token),
        "masked_token": masked_token
    }

def init_db():
    """
    Initialise la base de données en exécutant schema.sql,
    et assure la compatibilité des colonnes pour le régime IS.
    """
    client = get_client()
    try:
        schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
        with open(schema_path, "r", encoding="utf-8") as f:
            content = f.read()

        cleaned_content = re.sub(r'--.*$', '', content, flags=re.MULTILINE)
        raw_statements = cleaned_content.split(';')

        for stmt in raw_statements:
            sql = stmt.strip()
            if sql:
                try:
                    client.execute(sql)
                except Exception:
                    pass

        # Migration dynamique pour ajouter les colonnes IS si la table existait déjà
        try:
            rs = client.execute("PRAGMA table_info(properties);")
            existing_cols = [row[1] for row in rs.rows]
            
            is_cols_to_add = [
                ("notary_fees", "REAL DEFAULT 0.0"),
                ("land_share_pct", "REAL DEFAULT 15.0"),
                ("amortization_years", "INTEGER DEFAULT 25"),
                ("furniture_value", "REAL DEFAULT 0.0"),
                ("furniture_years", "INTEGER DEFAULT 5")
            ]
            for col_name, col_type in is_cols_to_add:
                if col_name not in existing_cols:
                    client.execute(f"ALTER TABLE properties ADD COLUMN {col_name} {col_type};")
        except Exception:
            pass

        try:
            rs_sci = client.execute("PRAGMA table_info(sci_info);")
            sci_cols = [row[1] for row in rs_sci.rows]
            if "tax_regime" not in sci_cols:
                client.execute("ALTER TABLE sci_info ADD COLUMN tax_regime TEXT DEFAULT 'IS';")
        except Exception:
            pass

    finally:
        client.close()

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

def query_rows(sql: str, params: Optional[List[Any]] = None) -> List[Dict[str, Any]]:
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

def query_one(sql: str, params: Optional[List[Any]] = None) -> Optional[Dict[str, Any]]:
    """
    Exécute une requête SELECT et retourne la première ligne sous forme de dictionnaire, ou None.
    """
    rows = query_rows(sql, params)
    return rows[0] if rows else None

def execute_write(sql: str, params: Optional[List[Any]] = None) -> int:
    """
    Exécute une requête d'écriture (INSERT, UPDATE, DELETE).
    Retourne last_insert_rowid si disponible, sinon rows_affected.
    """
    client = get_client()
    try:
        rs = client.execute(sql, params or [])
        if rs.last_insert_rowid is not None:
            return rs.last_insert_rowid
        return rs.rows_affected
    finally:
        client.close()
