"""
Vue Paramètres de la SCI et Diagnostic de la Base de Données Turso.
"""
import streamlit as st
from database import query_one, execute_write, get_connection_info, get_client, init_db

def render_settings():
    st.markdown("## ⚙️ Paramètres & Configuration")
    st.caption("Gérez l'identité juridique de votre SCI et surveillez la connexion à votre base de données Turso.")

    tab_sci, tab_db = st.tabs(["🏢 Identité de la SCI", "☁️ Base de Données & Turso"])

    # 1. IDENTITE DE LA SCI
    with tab_sci:
        sci = query_one("SELECT * FROM sci_info WHERE id = 1;") or {}

        with st.form("form_sci_info"):
            st.markdown("#### Informations Légales")
            col1, col2 = st.columns(2)
            with col1:
                sci_name = st.text_input("Dénomination sociale (Nom de la SCI) *", value=sci.get("name", "Ma SCI Immobilière"))
                tax_regime = st.selectbox("Régime fiscal de la société", ["IS (Impôt sur les Sociétés)", "IR (Impôt sur le Revenu - 2072)"], index=0)
                siren = st.text_input("Numéro SIREN", value=sci.get("siren", ""), placeholder="ex: 123 456 789")
                address = st.text_input("Adresse du siège social", value=sci.get("address", ""))
                postal_code = st.text_input("Code postal", value=sci.get("postal_code", ""))
                city = st.text_input("Ville", value=sci.get("city", ""))
            with col2:
                manager_name = st.text_input("Nom & Prénom du Gérant", value=sci.get("manager_name", ""))
                manager_email = st.text_input("Email de contact de la SCI", value=sci.get("manager_email", ""))
                manager_phone = st.text_input("Téléphone du gérant", value=sci.get("manager_phone", ""))

            st.markdown("#### Coordonnées Bancaires (pour les avis d'échéance)")
            col_b1, col_b2 = st.columns(2)
            with col_b1:
                iban = st.text_input("IBAN de la SCI", value=sci.get("iban", ""), placeholder="FR76 ...")
            with col_b2:
                bic = st.text_input("BIC / SWIFT", value=sci.get("bic", ""))

            submitted = st.form_submit_button("💾 Sauvegarder les coordonnées", type="primary")
            if submitted:
                regime_clean = "IS" if "IS" in tax_regime else "IR"
                execute_write("""
                    UPDATE sci_info
                    SET name=?, tax_regime=?, siren=?, address=?, postal_code=?, city=?, manager_name=?, manager_email=?, manager_phone=?, iban=?, bic=?, updated_at=CURRENT_TIMESTAMP
                    WHERE id = 1;
                """, [sci_name, regime_clean, siren, address, postal_code, city, manager_name, manager_email, manager_phone, iban, bic])
                st.success("Informations de la SCI mises à jour avec succès !")
                st.rerun()

    # 2. BASE DE DONNEES & TURSO
    with tab_db:
        st.markdown("#### Diagnostic de la Connexion")
        info = get_connection_info()

        is_turso = info["is_turso"]
        if is_turso:
            st.success("🟢 **Connecté à Turso Cloud (libSQL)**")
            st.write(f"**URL de la base :** `{info['url']}`")
            st.write(f"**Token d'authentification :** `{info['masked_token']}`")
        else:
            st.warning("🟠 **Mode local SQLite (Fallback)**")
            st.write(f"**Chemin du fichier :** `{info['url']}`")
            st.caption("Pour basculer sur Turso Cloud, renseignez vos tokens dans `.streamlit/secrets.toml` ou dans les secrets de Streamlit Cloud.")

        col_t1, col_t2 = st.columns(2)
        with col_t1:
            if st.button("🔄 Tester la connexion en direct"):
                try:
                    client = get_client()
                    rs = client.execute("SELECT datetime('now') as server_time, sqlite_version() as version;")
                    client.close()
                    st.success(f"Connexion réussie ! Version SQLite : {rs.rows[0][1]} — Heure serveur : {rs.rows[0][0]}")
                except Exception as e:
                    st.error(f"Erreur de connexion : {e}")

        with col_t2:
            if st.button("⚡ Réinitialiser / Vérifier les Tables (schema.sql)"):
                try:
                    init_db()
                    st.success("Toutes les tables et index ont été vérifiés ou créés avec succès !")
                except Exception as e:
                    st.error(f"Erreur lors de l'initialisation : {e}")

        st.markdown("---")
        st.markdown("#### Configuration des identifiants Turso")
        st.markdown("""
        Dans votre fichier `.streamlit/secrets.toml` (ou sur votre tableau de bord Streamlit Cloud) :
        ```toml
        TURSO_DATABASE_URL = "libsql://votre-base-nom.turso.io"
        TURSO_AUTH_TOKEN = "votre_token_secret_turso"
        ```
        """)
