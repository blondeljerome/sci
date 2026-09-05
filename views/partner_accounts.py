"""
Vue Comptes Courants d'Associés (CCA) - Spécifique SCI à l'IS.
Permet de suivre les apports personnels des associés et les remboursements en franchise d'impôt.
"""
import streamlit as st
import pandas as pd
from datetime import date
from database import query_rows, query_df, execute_write

def render_partner_accounts():
    st.markdown("## 🤝 Comptes Courants d'Associés (CCA)")
    st.caption("Suivez les apports personnels (apport bancaire, factures avancées) et les remboursements de trésorerie sans frottement fiscal.")

    tab_summary, tab_add, tab_history = st.tabs(["📊 Soldes des Associés", "➕ Enregistrer un Mouvement", "📜 Grand Livre des CCA"])

    # 1. SYNTHESE DES SOLDES
    with tab_summary:
        all_ops = query_rows("SELECT partner_name, type, amount FROM partner_accounts;")
        if not all_ops:
            st.info("Aucun mouvement de compte courant enregistré. Utilisez l'onglet **'➕ Enregistrer un Mouvement'** pour enregistrer votre apport initial ou des fonds avancés.")
        else:
            ops_df = pd.DataFrame(all_ops)
            partners = ops_df["partner_name"].unique()

            partner_summaries = []
            total_cca_balance = 0.0

            for p in partners:
                p_df = ops_df[ops_df["partner_name"] == p]
                apports = p_df[p_df["type"] == "apport"]["amount"].sum()
                remboursements = p_df[p_df["type"] == "remboursement"]["amount"].sum()
                balance = apports - remboursements
                total_cca_balance += balance
                partner_summaries.append({
                    "Associé": p,
                    "Total Apports (€)": apports,
                    "Total Remboursé (€)": remboursements,
                    "Solde Récupérable (€)": balance
                })

            st.metric(
                label="Dette totale de la SCI envers les associés (Total CCA)",
                value=f"{total_cca_balance:,.2f} €".replace(",", " "),
                help="Montant total de trésorerie que la SCI peut reverser aux associés sans aucun impôt (reprise d'apport personnel)."
            )

            st.markdown("---")
            st.markdown("### Répartition par Associé")
            sum_df = pd.DataFrame(partner_summaries)
            
            for row in partner_summaries:
                with st.container():
                    c1, c2, c3, c4 = st.columns(4)
                    c1.markdown(f"#### 👤 {row['Associé']}")
                    c2.metric("Apports cumulés", f"{row['Total Apports (€)']:,.2f} €".replace(",", " "))
                    c3.metric("Remboursements perçus", f"{row['Total Remboursé (€)']:,.2f} €".replace(",", " "))
                    c4.metric(
                        "Solde disponible",
                        f"{row['Solde Récupérable (€)']:,.2f} €".replace(",", " "),
                        delta="À récupérer net d'impôt",
                        delta_color="normal"
                    )
                    st.divider()

    # 2. ENREGISTRER UN MOUVEMENT
    with tab_add:
        st.markdown("#### Nouveau Mouvement de Compte Courant d'Associé")

        # Liste des associés déjà connus
        existing_partners = [r["partner_name"] for r in query_rows("SELECT DISTINCT partner_name FROM partner_accounts ORDER BY partner_name ASC;")]

        with st.form("form_add_cca_op", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                if existing_partners:
                    use_new = st.checkbox("Nouvel associé (non listé ci-dessous)", value=False)
                    if use_new:
                        partner_name = st.text_input("Nom & Prénom de l'associé *", placeholder="ex: Jérôme BLONDEL")
                    else:
                        partner_name = st.selectbox("Sélectionnez l'associé *", existing_partners)
                else:
                    partner_name = st.text_input("Nom & Prénom de l'associé *", placeholder="ex: Jérôme BLONDEL")

                op_date = st.date_input("Date du mouvement *", value=date.today()).strftime("%Y-%m-%d")
                op_type = st.selectbox(
                    "Nature de l'opération *",
                    ["apport", "remboursement"],
                    format_func=lambda x: "➕ Apport (L'associé avance ou injecte de l'argent dans la SCI)" if x == "apport" else "➖ Remboursement (La SCI rembourse l'associé sur son compte perso)"
                )

            with col2:
                amount = st.number_input("Montant (€) *", min_value=0.01, value=5000.0, step=100.0)
                description = st.text_input("Libellé / Objet *", placeholder="ex: Apport personnel apport prêt bancaire lot #101")
                notes = st.text_area("Notes / Réf. virement", placeholder="Virement bancaire compte perso vers compte SCI...")

            submitted = st.form_submit_button("💾 Enregistrer l'opération CCA", type="primary")
            if submitted:
                if not partner_name or not partner_name.strip():
                    st.error("Le nom de l'associé est obligatoire.")
                elif not description.strip():
                    st.error("Le libellé de l'opération est obligatoire.")
                else:
                    try:
                        execute_write("""
                            INSERT INTO partner_accounts (partner_name, date, type, amount, description, notes)
                            VALUES (?, ?, ?, ?, ?, ?);
                        """, [partner_name.strip(), op_date, op_type, amount, description.strip(), notes.strip()])
                        st.success(f"Opération de **{amount:,.2f} €** enregistrée avec succès pour **{partner_name}** !")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erreur : {e}")

    # 3. HISTORIQUE / GRAND LIVRE
    with tab_history:
        current_year = date.today().year
        col_y, col_p = st.columns([1, 2])
        with col_y:
            f_year = st.selectbox("Année", ["Toutes"] + list(range(current_year - 5, current_year + 5)), key="cca_f_yr")
        with col_p:
            existing_partners = [r["partner_name"] for r in query_rows("SELECT DISTINCT partner_name FROM partner_accounts ORDER BY partner_name ASC;")]
            f_partner = st.selectbox("Filtrer par associé", ["Tous"] + existing_partners, key="cca_f_ptn")

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
