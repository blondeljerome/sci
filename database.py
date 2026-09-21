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
    et assure la compatibilité des colonnes pour l'IS, les emprunts, l'IRL, les docs et le SMTP.
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

        # 1. Migration properties (colonnes IS)
        try:
            rs = client.execute("PRAGMA table_info(properties);")
            existing_cols = [row[1] for row in rs.rows]
            for col_name, col_type in [
                ("notary_fees", "REAL DEFAULT 0.0"),
                ("land_share_pct", "REAL DEFAULT 15.0"),
                ("amortization_years", "INTEGER DEFAULT 25"),
                ("furniture_value", "REAL DEFAULT 0.0"),
                ("furniture_years", "INTEGER DEFAULT 5")
            ]:
                if col_name not in existing_cols:
                    client.execute(f"ALTER TABLE properties ADD COLUMN {col_name} {col_type};")
        except Exception:
            pass

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
                ("smtp_sender_email", "TEXT DEFAULT ''")
            ]:
                if col_name not in sci_cols:
                    client.execute(f"ALTER TABLE sci_info ADD COLUMN {col_name} {col_type};")
        except Exception:
            pass

        # 3. Migration tenants (IRL)
        try:
            rs_t = client.execute("PRAGMA table_info(tenants);")
            tenant_cols = [row[1] for row in rs_t.rows]
            for col_name, col_type in [
                ("irl_reference_quarter", "TEXT DEFAULT 'T3 2024'"),
                ("irl_reference_value", "REAL DEFAULT 144.51"),
                ("last_revision_date", "TEXT DEFAULT ''")
            ]:
                if col_name not in tenant_cols:
                    client.execute(f"ALTER TABLE tenants ADD COLUMN {col_name} {col_type};")
        except Exception:
            pass

        # 4. Migration documents (Cloudinary, property_id, tenant_id)
        try:
            rs_d = client.execute("PRAGMA table_info(documents);")
            doc_cols = [row[1] for row in rs_d.rows]
            if "cloudinary_public_id" not in doc_cols:
                client.execute("ALTER TABLE documents ADD COLUMN cloudinary_public_id TEXT DEFAULT '';")
            if "property_id" not in doc_cols:
                client.execute("ALTER TABLE documents ADD COLUMN property_id INTEGER;")
            if "tenant_id" not in doc_cols:
                client.execute("ALTER TABLE documents ADD COLUMN tenant_id INTEGER;")
        except Exception:
            pass

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
                SELECT DISTINCT partner_name FROM partner_accounts WHERE partner_name != '';
            """)
        except Exception:
            pass

    finally:
        client.close()

    # 5. Initialisation des 2 utilisateurs par défaut
    try:
        from utils.auth import init_default_users
        init_default_users()
    except Exception:
        pass

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
