"""
Module de sauvegarde et de rétention de la base de données (Turso / SQLite).
Génère un dump SQL complet, le compresse au format gzip et le sauvegarde dans un dossier dédié Cloudinary.
Gère la rétention automatique (ex: 30 jours / 1 mois).
"""
import io
import gzip
import datetime
from typing import Dict, Any, List, Tuple, Optional
import cloudinary
import cloudinary.uploader
import cloudinary.api
from config import configure_cloudinary
from database import query_rows, query_one, get_connection_info

BACKUP_FOLDER = "sci-backups"
BACKUP_TAG = "sci_database_backup"
DEFAULT_RETENTION_DAYS = 30


def _ensure_cloudinary():
    """Vérifie et configure Cloudinary."""
    if not cloudinary.config().cloud_name:
        ok = configure_cloudinary()
        if not ok:
            raise RuntimeError(
                "Cloudinary n'est pas configuré. Veuillez définir CLOUDINARY_CLOUD_NAME, "
                "CLOUDINARY_API_KEY et CLOUDINARY_API_SECRET."
            )


def _sql_escape_val(val: Any) -> str:
    """Échappe et formate une valeur pour l'insertion SQL."""
    if val is None:
        return "NULL"
    elif isinstance(val, (int, float)):
        return str(val)
    elif isinstance(val, bytes):
        return f"X'{val.hex()}'"
    else:
        escaped = str(val).replace("'", "''")
        return f"'{escaped}'"


def generate_sql_dump() -> str:
    """
    Génère un script SQL complet contenant :
    1. Schéma de toutes les tables existantes
    2. Toutes les données via INSERT INTO
    3. Tous les index personnalisés
    Le tout enveloppé dans une transaction atomique.
    """
    conn_info = get_connection_info()
    now_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    
    # Infos sur la SCI
    sci = query_one("SELECT name, siren, tax_regime FROM sci_info WHERE id = 1;") or {}
    sci_name = sci.get("name", "SCI Immobilière")

    lines = [
        "-- ========================================================",
        f"-- SAUVEGARDE BASE DE DONNEES : {sci_name}",
        f"-- Date d'export : {now_str}",
        f"-- Mode : {'Turso Cloud (libSQL)' if conn_info['is_turso'] else 'SQLite Local'}",
        "-- ========================================================",
        "",
        "PRAGMA foreign_keys=OFF;",
        "BEGIN TRANSACTION;",
        ""
    ]

    # Récupérer les tables
    table_meta = query_rows(
        "SELECT name, sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name ASC;"
    )

    for tm in table_meta:
        table_name = tm["name"]
        create_sql = tm["sql"].strip() if tm["sql"] else ""
        if not create_sql:
            continue

        # S'assurer que CREATE TABLE est sous forme IF NOT EXISTS
        if not create_sql.upper().startswith("CREATE TABLE IF NOT EXISTS"):
            create_sql = create_sql.replace("CREATE TABLE", "CREATE TABLE IF NOT EXISTS", 1)

        lines.append(f"-- Table : {table_name}")
        lines.append(f"{create_sql};")

        # Exporter les données
        rows = query_rows(f"SELECT * FROM \"{table_name}\";")
        if rows:
            cols = list(rows[0].keys())
            cols_formatted = ", ".join([f"\"{c}\"" for c in cols])

            for r in rows:
                vals_formatted = ", ".join([_sql_escape_val(r[c]) for c in cols])
                lines.append(f"INSERT INTO \"{table_name}\" ({cols_formatted}) VALUES ({vals_formatted});")

        lines.append("")

    # Récupérer les index personnalisés
    index_meta = query_rows(
        "SELECT name, sql FROM sqlite_master WHERE type='index' AND sql IS NOT NULL AND name NOT LIKE 'sqlite_%' ORDER BY name ASC;"
    )

    if index_meta:
        lines.append("-- Index")
        for im in index_meta:
            idx_sql = im["sql"].strip()
            if not idx_sql.upper().startswith("CREATE INDEX IF NOT EXISTS") and not idx_sql.upper().startswith("CREATE UNIQUE INDEX IF NOT EXISTS"):
                idx_sql = idx_sql.replace("CREATE UNIQUE INDEX", "CREATE UNIQUE INDEX IF NOT EXISTS", 1)
                idx_sql = idx_sql.replace("CREATE INDEX", "CREATE INDEX IF NOT EXISTS", 1)
            lines.append(f"{idx_sql};")
        lines.append("")

    lines.append("COMMIT;")
    lines.append("-- FIN DE LA SAUVEGARDE")
    
    return "\n".join(lines)


def create_backup(retention_days: int = DEFAULT_RETENTION_DAYS, folder: str = BACKUP_FOLDER) -> Dict[str, Any]:
    """
    Génère le dump SQL complet, l'uploade vers Cloudinary dans le dossier dédié,
    et applique la politique de rétention (suppression des backups > retention_days).

    Retourne un dictionnaire avec les détails de la sauvegarde créée et le compte des sauvegardes purgées.
    """
    _ensure_cloudinary()

    # 1. Génération du dump SQL
    sql_text = generate_sql_dump()
    sql_bytes = sql_text.encode("utf-8")
    file_size = len(sql_bytes)

    # 2. Nom de fichier horodaté .sql
    ts = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
    filename = f"backup_sci_{ts}.sql"

    # 3. Upload Cloudinary en resource_type="raw"
    upload_result = cloudinary.uploader.upload(
        sql_bytes,
        folder=folder,
        public_id=filename,
        resource_type="raw",
        tags=[BACKUP_TAG, "database_backup"],
        overwrite=True
    )

    public_id = upload_result.get("public_id")
    secure_url = upload_result.get("secure_url")

    # 4. Purge des sauvegardes expirées selon la règle de rétention
    purged_count = 0
    try:
        purged_count = purge_expired_backups(retention_days=retention_days, folder=folder)
    except Exception as e:
        print(f"Avertissement lors de la purge de rétention : {e}")

    return {
        "filename": filename,
        "public_id": public_id,
        "secure_url": secure_url,
        "size_bytes": file_size,
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "purged_count": purged_count
    }


def list_backups(folder: str = BACKUP_FOLDER) -> List[Dict[str, Any]]:
    """
    Liste toutes les sauvegardes existantes dans le dossier Cloudinary spécifié.
    Retourne la liste triée par date décroissante (plus récente en premier).
    """
    _ensure_cloudinary()

    try:
        res = cloudinary.api.resources(
            type="upload",
            prefix=f"{folder}/",
            resource_type="raw",
            max_results=100
        )
        resources = res.get("resources", [])
    except Exception:
        # Fallback via tags si prefix n'est pas supporté sur certains types de comptes
        try:
            res = cloudinary.api.resources_by_tag(
                BACKUP_TAG,
                resource_type="raw",
                max_results=100
            )
            resources = res.get("resources", [])
        except Exception:
            resources = []

    backups = []
    for r in resources:
        pid = r.get("public_id", "")
        # Extraire le nom de fichier propre
        filename = pid.split("/")[-1] if "/" in pid else pid
        
        created_at_str = r.get("created_at", "")
        # Parser la date Cloudinary (ex: "2026-09-11T08:50:00Z")
        dt_created = None
        if created_at_str:
            try:
                dt_created = datetime.datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
            except Exception:
                pass

        backups.append({
            "public_id": pid,
            "filename": filename,
            "secure_url": r.get("secure_url", ""),
            "bytes": r.get("bytes", 0),
            "created_at": dt_created,
            "created_at_str": created_at_str
        })

    # Trier de la plus récente à la plus ancienne
    backups.sort(key=lambda b: b["created_at"] or datetime.datetime.min.replace(tzinfo=datetime.timezone.utc), reverse=True)
    return backups


def delete_backup(public_id: str) -> bool:
    """
    Supprime un backup spécifique sur Cloudinary via son public_id.
    """
    if not public_id:
        return False
    _ensure_cloudinary()

    try:
        res = cloudinary.uploader.destroy(public_id, resource_type="raw")
        return res.get("result") in ("ok", "not found")
    except Exception as e:
        print(f"Erreur suppression backup {public_id}: {e}")
        return False


def purge_expired_backups(retention_days: int = DEFAULT_RETENTION_DAYS, folder: str = BACKUP_FOLDER) -> int:
    """
    Supprime toutes les sauvegardes plus vieilles que retention_days (ex: 30 jours / 1 mois).
    Retourne le nombre de fichiers supprimés.
    """
    backups = list_backups(folder=folder)
    now = datetime.datetime.now(datetime.timezone.utc)
    cutoff = now - datetime.timedelta(days=retention_days)

    deleted_count = 0
    for b in backups:
        dt = b.get("created_at")
        if dt and dt < cutoff:
            ok = delete_backup(b["public_id"])
            if ok:
                deleted_count += 1

    return deleted_count
