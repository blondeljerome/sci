"""
Script autonome de synchronisation automatique des indices IRL INSEE.
Récupère les derniers indices publiés sur Service-Public.fr et l'ANIL et les enregistre dans irl_indices.
"""
from utils.irl import sync_irl_indices_to_db

if __name__ == "__main__":
    print("Récupération des indices IRL en ligne...")
    res = sync_irl_indices_to_db()
    if res["success"]:
        print(f"✅ Succès : {res['count']} indices synchronisés.")
        print(f"Dernier indice officiel : {res['latest_quarter']} = {res['latest_value']} (JO : {res['latest_date']})")
    else:
        print(f"❌ Erreur : {res['message']}")
