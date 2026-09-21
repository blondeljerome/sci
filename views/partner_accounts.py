"""
Vue Comptes Courants d'Associés (CCA) - Spécifique SCI à l'IS.
Permet de suivre les associés de la SCI, les apports personnels et les remboursements en franchise d'impôt.
"""
import streamlit as st
import pandas as pd
from datetime import date
from database import query_rows, query_df, execute_write

def get_all_partners():
    """Retourne la liste triée et dédoublonnée de tous les associés enregistrés."""
    try:
        rows = query_rows("SELECT name FROM partners ORDER BY name ASC;")
        db_partners = [r["name"].strip() for r in rows if r.get("name")]
    except Exception:
        db_partners = []
    try:
        cca_rows = query_rows("SELECT DISTINCT partner_name FROM partner_accounts ORDER BY partner_name ASC;")
        cca_partners = [r["partner_name"].strip() for r in cca_rows if r.get("partner_name")]
    except Exception:
        cca_partners = []
    return sorted(list(set(db_partners + cca_partners)))

def render_partner_accounts():
    st.markdown("## 🤝 Comptes Courants d'Associés (CCA)")
    st.caption("Gérez les associés de la SCI, suivez leurs apports personnels et les remboursements de trésorerie en franchise d'impôt.")

    tab_summary, tab_add, tab_partners, tab_history = st.tabs([
        "📊 Soldes des Associés",
        "➕ Enregistrer un Mouvement",
        "👥 Associés de la SCI",
        "📜 Grand Livre des CCA"
    ])

    all_partners = get_all_partners()

    # 1. SYNTHESE DES SOLDES
    with tab_summary:
        all_ops = query_rows("SELECT partner_name, type, amount FROM partner_accounts;")
        if not all_partners and not all_ops:
            st.info("Aucun associé ni mouvement de compte courant enregistré. Utilisez l'onglet **'➕ Enregistrer un Mouvement'** ou **'👥 Associés de la SCI'** pour commencer.")
        else:
            ops_df = pd.DataFrame(all_ops) if all_ops else pd.DataFrame(columns=["partner_name", "type", "amount"])
            partner_summaries = []
            total_cca_balance = 0.0

            for p in all_partners:
                p_df = ops_df[ops_df["partner_name"] == p] if not ops_df.empty else pd.DataFrame()
                if not p_df.empty:
                    apports = p_df[p_df["type"] == "apport"]["amount"].sum()
                    remboursements = p_df[p_df["type"] == "remboursement"]["amount"].sum()
                else:
                    apports = 0.0
                    remboursements = 0.0
                balance = apports - remboursements
                total_cca_balance += balance
                partner_summaries.append({
                    "Associé": p,
                    "Total Apports (€)": apports,
                    "Total Remboursé (€)": remboursements,
                    "Solde Récupérable (€)": balance,
                    "Nb Mouvements": len(p_df)
                })

            st.metric(
                label="Dette totale de la SCI envers les associés (Total CCA)",
                value=f"{total_cca_balance:,.2f} €".replace(",", " "),
                help="Montant total de trésorerie que la SCI peut reverser aux associés sans aucun impôt (reprise d'apport personnel)."
            )

            st.markdown("---")
            st.markdown("### Répartition par Associé")
            
            for row in partner_summaries:
                with st.container():
                    c1, c2, c3, c4 = st.columns(4)
                    c1.markdown(f"#### 👤 {row['Associé']}")
                    if row["Nb Mouvements"] == 0:
                        c1.caption("Aucun mouvement financier enregistré")
                    c2.metric("Apports cumulés", f"{row['Total Apports (€)']:,.2f} €".replace(",", " "))
                    c3.metric("Remboursements perçus", f"{row['Total Remboursé (€)']:,.2f} €".replace(",", " "))
                    c4.metric(
                        "Solde disponible",
                        f"{row['Solde Récupérable (€)']:,.2f} €".replace(",", " "),
                        delta="À récupérer net d'impôt" if row['Solde Récupérable (€)'] > 0 else None,
                        delta_color="normal"
                    )
                    st.divider()

    # 2. ENREGISTRER UN MOUVEMENT
    with tab_add:
        st.markdown("#### Nouveau Mouvement de Compte Courant d'Associé")

        NEW_PARTNER_LABEL = "➕ Créer un nouvel associé..."
        col1, col2 = st.columns(2)
        with col1:
            if all_partners:
                dropdown_options = all_partners + [NEW_PARTNER_LABEL]
                selected_choice = st.selectbox(
                    "Sélectionnez l'associé *",
                    dropdown_options,
                    key="cca_partner_select"
                )
                if selected_choice == NEW_PARTNER_LABEL:
                    partner_name = st.text_input(
                        "Nom & Prénom du nouvel associé *",
                        placeholder="ex: Marie DUPONT",
                        key="cca_new_partner_name"
                    )
                else:
                    partner_name = selected_choice
            else:
                partner_name = st.text_input(
                    "Nom & Prénom de l'associé *",
                    placeholder="ex: Jérôme BLONDEL",
                    key="cca_new_partner_name"
                )

            op_date = st.date_input("Date du mouvement *", value=date.today(), key="cca_op_date").strftime("%Y-%m-%d")
            op_type = st.selectbox(
                "Nature de l'opération *",
                ["apport", "remboursement"],
                format_func=lambda x: "➕ Apport (L'associé avance ou injecte de l'argent dans la SCI)" if x == "apport" else "➖ Remboursement (La SCI rembourse l'associé sur son compte perso)",
                key="cca_op_type"
            )

        with col2:
            amount = st.number_input("Montant (€) *", min_value=0.01, value=5000.0, step=100.0, key="cca_amount")
            description = st.text_input("Libellé / Objet *", placeholder="ex: Apport personnel apport prêt bancaire lot #101", key="cca_description")
            notes = st.text_area("Notes / Réf. virement", placeholder="Virement bancaire compte perso vers compte SCI...", key="cca_notes")

        submitted = st.button("💾 Enregistrer l'opération CCA", type="primary")
        if submitted:
            clean_partner = partner_name.strip() if partner_name else ""
            clean_desc = description.strip() if description else ""
            if not clean_partner:
                st.error("Le nom de l'associé est obligatoire.")
            elif not clean_desc:
                st.error("Le libellé de l'opération est obligatoire.")
            else:
                try:
                    # Enregistrer dans partners si inexistant
                    try:
                        execute_write("INSERT OR IGNORE INTO partners (name) VALUES (?);", [clean_partner])
                    except Exception:
                        pass
                    # Enregistrer le mouvement CCA
                    execute_write("""
                        INSERT INTO partner_accounts (partner_name, date, type, amount, description, notes)
                        VALUES (?, ?, ?, ?, ?, ?);
                    """, [clean_partner, op_date, op_type, amount, clean_desc, notes.strip()])
                    st.success(f"Opération de **{amount:,.2f} €** enregistrée avec succès pour **{clean_partner}** !")
                    for k in ["cca_new_partner_name", "cca_description", "cca_notes"]:
                        st.session_state.pop(k, None)
                    st.rerun()
                except Exception as e:
                    st.error(f"Erreur : {e}")

    # 3. GESTION DES ASSOCIÉS
    with tab_partners:
        st.markdown("#### 👥 Gestion des Associés de la SCI")
        st.caption("Déclarez et gérez les associés composant votre société civile immobilière.")

        with st.expander("➕ Créer un nouvel associé", expanded=not bool(all_partners)):
            c_p1, c_p2 = st.columns(2)
            with c_p1:
                p_new_name = st.text_input("Nom & Prénom de l'associé *", placeholder="ex: Second Associé", key="form_p_name")
                p_new_email = st.text_input("Adresse email (optionnel)", placeholder="associe@email.com", key="form_p_email")
            with c_p2:
                p_new_shares = st.number_input("Parts sociales détenues", min_value=0, value=0, step=10, key="form_p_shares")
                p_new_phone = st.text_input("Numéro de téléphone (optionnel)", placeholder="06 12 34 56 78", key="form_p_phone")

            if st.button("✅ Enregistrer cet associé", type="primary", key="btn_save_partner"):
                clean_name = p_new_name.strip()
                if not clean_name:
                    st.error("Le nom et prénom de l'associé sont obligatoires.")
                else:
                    try:
                        execute_write("""
                            INSERT INTO partners (name, email, phone, shares)
                            VALUES (?, ?, ?, ?);
                        """, [clean_name, p_new_email.strip(), p_new_phone.strip(), int(p_new_shares)])
                        st.success(f"L'associé **{clean_name}** a été créé avec succès !")
                        for k in ["form_p_name", "form_p_email", "form_p_shares", "form_p_phone"]:
                            st.session_state.pop(k, None)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erreur lors de la création de l'associé : {e}")

        # Affichage des associés existants
        try:
            partner_db_rows = query_rows("SELECT * FROM partners ORDER BY name ASC;")
        except Exception:
            partner_db_rows = []

        if partner_db_rows:
            st.markdown("##### Associés déclarés")
            p_data = []
            for r in partner_db_rows:
                # Solde CCA pour cet associé
                ops = query_rows("SELECT type, amount FROM partner_accounts WHERE partner_name = ?;", [r["name"]])
                ap = sum(float(x["amount"]) for x in ops if x["type"] == "apport")
                rem = sum(float(x["amount"]) for x in ops if x["type"] == "remboursement")
                p_data.append({
                    "id": r["id"],
                    "Nom de l'associé": r["name"],
                    "Email": r.get("email") or "—",
                    "Téléphone": r.get("phone") or "—",
                    "Parts": r.get("shares", 0),
                    "Solde CCA (€)": f"{(ap - rem):,.2f} €".replace(",", " "),
                    "Nb Opérations": len(ops)
                })

            df_p = pd.DataFrame(p_data)
            st.dataframe(df_p.drop(columns=["id"]), use_container_width=True, hide_index=True)

            with st.expander("🗑️ Supprimer un associé"):
                p_dict = {r["id"]: f"{r['name']} ({r.get('email') or 'sans email'})" for r in partner_db_rows}
                sel_del_p = st.selectbox("Sélectionnez l'associé à supprimer :", options=list(p_dict.keys()), format_func=lambda x: p_dict[x], key="sb_del_partner")
                p_obj = next((r for r in partner_db_rows if r["id"] == sel_del_p), None)
                if p_obj:
                    # Vérifier s'il a des mouvements CCA
                    has_ops = query_rows("SELECT id FROM partner_accounts WHERE partner_name = ? LIMIT 1;", [p_obj["name"]])
                    if has_ops:
                        st.warning("⚠️ Cet associé possède des opérations de compte courant enregistrées. Sa suppression supprimera également son historique CCA.")
                    if st.button(f"Confirmer la suppression de {p_obj['name']}", type="secondary", key="btn_confirm_del_p"):
                        execute_write("DELETE FROM partner_accounts WHERE partner_name = ?;", [p_obj["name"]])
                        execute_write("DELETE FROM partners WHERE id = ?;", [sel_del_p])
                        st.success(f"Associé {p_obj['name']} supprimé.")
                        st.rerun()

    # 4. HISTORIQUE / GRAND LIVRE
    with tab_history:
        current_year = date.today().year
        col_y, col_p = st.columns([1, 2])
        with col_y:
            f_year = st.selectbox("Année", ["Toutes"] + list(range(current_year - 5, current_year + 5)), key="cca_f_yr")
        with col_p:
            f_partner = st.selectbox("Filtrer par associé", ["Tous"] + all_partners, key="cca_f_ptn")

        q = "SELECT * FROM partner_accounts WHERE 1=1"
        params = []
        if f_year != "Toutes":
            q += " AND strftime('%Y', date) = ?"
            params.append(str(f_year))
        if f_partner != "Tous":
            q += " AND partner_name = ?"
            params.append(f_partner)
        q += " ORDER BY date DESC, id DESC;"

        rows = query_rows(q, params)
        if not rows:
            st.info("Aucune opération trouvée pour ces filtres.")
        else:
            df = pd.DataFrame(rows)
            disp_df = df[["date", "partner_name", "type", "description", "amount", "notes"]].copy()
            disp_df["type"] = disp_df["type"].apply(lambda t: "🟢 Apport (+)" if t == "apport" else "🔵 Remboursement (-)")
            disp_df.columns = ["Date", "Associé", "Type", "Description", "Montant (€)", "Notes"]
            st.dataframe(disp_df, use_container_width=True, hide_index=True)

            with st.expander("🗑️ Supprimer une opération"):
                del_options = {r["id"]: f"#{r['id']} | {r['date']} | {r['partner_name']} | {r['type'].upper()} {r['amount']:,.2f} € — {r['description']}" for r in rows}
                op_to_del = st.selectbox("Sélectionnez l'opération à supprimer", options=list(del_options.keys()), format_func=lambda x: del_options[x], key="cca_del_op_sel")
                if st.button("Confirmer la suppression", type="secondary", key="cca_btn_confirm_del"):
                    execute_write("DELETE FROM partner_accounts WHERE id = ?;", [op_to_del])
                    st.success("Opération supprimée avec succès.")
                    st.rerun()
