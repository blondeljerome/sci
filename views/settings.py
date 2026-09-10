"""
Vue Paramètres de la SCI et Diagnostic de la Base de Données Turso.
"""
import streamlit as st
from database import query_one, execute_write, get_connection_info, get_client, init_db

def render_settings():
    st.markdown("## ⚙️ Paramètres & Configuration")
    st.caption("Gérez l'identité juridique de votre SCI et surveillez la connexion à votre base de données Turso.")

    tab_sci, tab_db, tab_smtp, tab_security = st.tabs([
        "🏢 Identité de la SCI",
        "☁️ Base de Données & Turso",
        "📧 Configuration Email (SMTP)",
        "🔐 Sécurité & Utilisateurs"
    ])

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

    # 3. CONFIGURATION SMTP
    with tab_smtp:
        st.markdown("#### Serveur d'Envoi d'Emails (SMTP)")
        st.caption("Configurez votre serveur email (Gmail, Brevo, OVH, etc.) pour envoyer directement les quittances, avis d'échéance et relances à vos locataires.")

        sci_smtp = query_one("SELECT smtp_server, smtp_port, smtp_username, smtp_password, smtp_use_tls, smtp_sender_email, manager_email FROM sci_info WHERE id = 1;") or {}

        with st.form("form_smtp_config"):
            col_s1, col_s2 = st.columns(2)
            with col_s1:
                server = st.text_input("Serveur hôte SMTP", value=sci_smtp.get("smtp_server", ""), placeholder="ex: smtp.gmail.com ou smtp-relay.brevo.com")
                port = st.number_input("Port SMTP", value=int(sci_smtp.get("smtp_port") or 587), step=1)
                use_tls = st.checkbox("Activer le chiffrement TLS / STARTTLS", value=bool(sci_smtp.get("smtp_use_tls", 1)))
            with col_s2:
                username = st.text_input("Identifiant / Email de connexion", value=sci_smtp.get("smtp_username", ""), placeholder="ex: contact@masci.fr")
                password = st.text_input("Mot de passe ou mot de passe d'application", value=sci_smtp.get("smtp_password", ""), type="password", help="Pour Gmail, générez un 'Mot de passe d'application' dans la sécurité de votre compte Google.")
                sender_email = st.text_input("Email expéditeur affiché", value=sci_smtp.get("smtp_sender_email", "") or sci_smtp.get("manager_email", ""), placeholder="ex: gestion@masci.fr")

            save_smtp = st.form_submit_button("💾 Enregistrer la configuration SMTP", type="primary")
            if save_smtp:
                execute_write("""
                    UPDATE sci_info
                    SET smtp_server = ?, smtp_port = ?, smtp_username = ?, smtp_password = ?, smtp_use_tls = ?, smtp_sender_email = ?
                    WHERE id = 1;
                """, [server.strip(), port, username.strip(), password.strip(), 1 if use_tls else 0, sender_email.strip()])
                st.success("Paramètres SMTP enregistrés avec succès !")
                st.rerun()

        st.markdown("---")
        st.markdown("#### 🧪 Tester la connexion email")
        test_col1, test_col2 = st.columns([2, 1])
        with test_col1:
            test_recipient = st.text_input("Email de test (destinataire)", placeholder="votre.email@gmail.com", key="smtp_test_dest")
        with test_col2:
            st.write("")
            st.write("")
            if st.button("📤 Envoyer un email de test", key="btn_test_smtp"):
                from utils.mailer import send_email
                test_body = f"""
                <div style="font-family: sans-serif; padding: 20px; border: 1px solid #2563eb; border-radius: 8px;">
                    <h2 style="color: #2563eb;">Test de configuration SMTP réussi ! 🎉</h2>
                    <p>Votre application de gestion de SCI peut désormais expédier automatiquement :</p>
                    <ul>
                        <li>Les <strong>quittances de loyer</strong> dès validation d'encaissement</li>
                        <li>Les <strong>avis d'échéance</strong> mensuels</li>
                        <li>Les <strong>courriers de relance d'impayés</strong> et lettres de <strong>révision IRL</strong></li>
                    </ul>
                </div>
                """
                success, msg = send_email(test_recipient, "Test de connexion email - Application SCI", test_body)
                if success:
                    st.success(msg)
                else:
                    st.error(msg)

    # 4. SECURITE & UTILISATEURS
    with tab_security:
        from utils.auth import change_password, update_user_profile, get_all_users, hash_password
        
        current_user = st.session_state.get("authenticated_user", {})
        user_id = current_user.get("id")
        user_name = current_user.get("full_name", "Utilisateur")
        user_login = current_user.get("username", "")

        st.markdown("#### 👤 Mon Compte Connecté")
        st.info(f"Connecté en tant que **{user_name}** (`{user_login}`) — Rôle : **{current_user.get('role', 'admin').capitalize()}**")

        col_pwd, col_prof = st.columns(2)

        with col_pwd:
            st.markdown("##### 🔑 Modifier mon mot de passe")
            with st.form("form_change_password"):
                old_pwd = st.text_input("Mot de passe actuel *", type="password")
                new_pwd = st.text_input("Nouveau mot de passe (min. 6 caractères) *", type="password")
                confirm_pwd = st.text_input("Confirmer le nouveau mot de passe *", type="password")

                btn_change = st.form_submit_button("Mettre à jour le mot de passe", type="primary")
                if btn_change:
                    if not old_pwd or not new_pwd:
                        st.error("Veuillez remplir tous les champs obligatoires.")
                    elif new_pwd != confirm_pwd:
                        st.error("Les deux nouveaux mots de passe ne correspondent pas.")
                    elif len(new_pwd) < 6:
                        st.error("Le nouveau mot de passe doit comporter au moins 6 caractères.")
                    else:
                        ok, msg = change_password(user_id, old_pwd, new_pwd)
                        if ok:
                            st.success(msg)
                        else:
                            st.error(msg)

        with col_prof:
            st.markdown("##### 📝 Mes Coordonnées")
            with st.form("form_change_profile"):
                new_fullname = st.text_input("Nom & Prénom *", value=current_user.get("full_name", ""))
                new_email = st.text_input("Adresse email", value=current_user.get("email", ""), placeholder="ex: contact@masci.fr")

                btn_profile = st.form_submit_button("Enregistrer mon profil")
                if btn_profile:
                    if not new_fullname.strip():
                        st.error("Le nom est obligatoire.")
                    else:
                        ok, msg = update_user_profile(user_id, new_fullname, new_email)
                        if ok:
                            # Mettre à jour la session
                            current_user["full_name"] = new_fullname.strip()
                            current_user["email"] = new_email.strip()
                            st.session_state["authenticated_user"] = current_user
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)

        st.markdown("---")
        st.markdown("#### 👥 Comptes Utilisateurs de la SCI")
        st.caption("Gestion des 2 accès autorisés à l'application.")

        all_users = get_all_users()
        if all_users:
            import pandas as pd
            display_users = []
            for u in all_users:
                display_users.append({
                    "Identifiant": u["username"],
                    "Nom Complet": u["full_name"],
                    "Email": u["email"] or "Non renseigné",
                    "Rôle": u["role"],
                    "Statut": "✅ Actif" if u["is_active"] else "❌ Inactif",
                    "Dernière Connexion": u["last_login"] or "Jamais"
                })
            st.dataframe(pd.DataFrame(display_users), use_container_width=True, hide_index=True)

        # Réinitialisation d'un mot de passe par l'administrateur
        with st.expander("🛠️ Réinitialiser le mot de passe d'un utilisateur"):
            st.caption("Permet d'attribuer un nouveau mot de passe temporaire en cas d'oubli.")
            other_users = [u for u in all_users if u["id"] != user_id]
            if other_users:
                target_user = st.selectbox(
                    "Utilisateur concerné",
                    options=other_users,
                    format_func=lambda u: f"{u['full_name']} ({u['username']})"
                )
                temp_pwd = st.text_input("Nouveau mot de passe temporaire (min. 6 car.)", type="password", key="admin_temp_pwd")
                if st.button("Réinitialiser le mot de passe de cet utilisateur"):
                    if len(temp_pwd) < 6:
                        st.error("Le mot de passe doit comporter au moins 6 caractères.")
                    else:
                        new_hash = hash_password(temp_pwd)
                        execute_write("UPDATE users SET password_hash = ? WHERE id = ?;", [new_hash, target_user["id"]])
                        st.success(f"Mot de passe de {target_user['full_name']} réinitialisé avec succès !")
            else:
                st.info("Aucun autre utilisateur configuré.")

