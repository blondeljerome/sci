#!/usr/bin/env python3
"""
Script d'exécution autonome pour la sauvegarde hebdomadaire de la base de données.
Sauvegarde la base Turso / SQLite vers Cloudinary et purge les archives > 30 jours (1 mois).
Peut être appelé manuellement, via un cron système ou via un workflow GitHub Actions.
"""
import sys
import os
import argparse
from datetime import datetime

# Ajouter la racine du projet au PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils.backup import create_backup, list_backups, purge_expired_backups, BACKUP_FOLDER, DEFAULT_RETENTION_DAYS
from database import get_connection_info


def main():
    parser = argparse.ArgumentParser(description="Sauvegarde de la base de données SCI vers Cloudinary avec rétention.")
    parser.add_argument("--retention", type=int, default=DEFAULT_RETENTION_DAYS, help="Durée de rétention en jours (défaut: 30)")
    parser.add_argument("--folder", type=str, default=BACKUP_FOLDER, help="Dossier Cloudinary (défaut: sci-backups)")
    parser.add_argument("--list", action="store_true", help="Lister uniquement les sauvegardes existantes sans en créer de nouvelle")
    parser.add_argument("--purge-only", action="store_true", help="Purger uniquement les sauvegardes expirées sans en créer de nouvelle")

    args = parser.parse_args()

    print("=" * 65)
    print(f"🚀 SCI - Sauvegarde Base de Données -> Cloudinary")
    print(f"⏰ Date d'exécution : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    conn_info = get_connection_info()
    print(f"💾 Source DB : {'Turso Cloud (libSQL)' if conn_info['is_turso'] else 'SQLite Local'}")
    print(f"📁 Dossier Cloudinary : {args.folder}")
    print(f"⏳ Rétention : {args.retention} jours (~1 mois)")
    print("=" * 65)

    try:
        if args.list:
            print("\n📋 Récupération de la liste des sauvegardes...")
            backups = list_backups(folder=args.folder)
            if not backups:
                print("Aucune sauvegarde trouvée.")
            else:
                print(f"Total trouvé : {len(backups)} sauvegarde(s)\n")
                for b in backups:
                    size_kb = b['bytes'] / 1024
                    date_str = b['created_at'].strftime('%Y-%m-%d %H:%M:%S') if b['created_at'] else b['created_at_str']
                    print(f" - [{date_str}] {b['filename']} ({size_kb:.1f} Ko) -> {b['secure_url']}")
            return

        if args.purge_only:
            print(f"\n🧹 Purge des sauvegardes de plus de {args.retention} jours...")
            purged = purge_expired_backups(retention_days=args.retention, folder=args.folder)
            print(f"✅ {purged} sauvegarde(s) purgée(s).")
            return

        print("\n📦 1/3 - Génération du dump SQL complet...")
        res = create_backup(retention_days=args.retention, folder=args.folder)

        size_kb = res['size_bytes'] / 1024
        print(f"✅ Dump SQL généré : {size_kb:.1f} Ko")
        print("\n☁️  2/3 - Upload vers Cloudinary...")
        print(f"✅ Fichier : {res['filename']}")
        print(f"✅ URL sécurisée : {res['secure_url']}")

        print(f"\n🧹 3/3 - Application de la rétention ({args.retention} jours)...")
        print(f"✅ {res['purged_count']} ancienne(s) sauvegarde(s) expirée(s) supprimée(s).")

        print("\n" + "=" * 65)
        print("🎉 Opération de sauvegarde terminée avec succès !")
        print("=" * 65)

    except Exception as e:
        print(f"\n❌ ERREUR lors de la sauvegarde : {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
