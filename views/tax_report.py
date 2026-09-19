"""
Vue Liasse Fiscale & Déclaration IS (Cerfa 2065 / 2033).
Intègre le Compte de Résultat (2033-B), le Bilan Actif & Passif (2033-A),
le Tableau des Immobilisations & Amortissements (2033-C) et les cases officielles DGFiP.
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date
from utils.tax_calculator import (
    compute_income_statement,
    compute_balance_sheet,
    compute_depreciation_schedule,
    get_cerfa_codes
)

def render_tax_report():
    st.markdown("## 📑 Liasse Fiscale & Déclaration IS (Cerfa 2065 / 2033)")
    st.caption("Synthèse comptable et fiscale complète pour Société Civile Immobilière soumise à l'Impôt sur les Sociétés (IS).")

    # 1. Sélection de l'exercice fiscal
    current_year = date.today().year
    year_options = list(range(2023, 2032))
    default_index = year_options.index(current_year) if current_year in year_options else len(year_options) - 1

    col_y, col_info = st.columns([1, 3])
    with col_y:
        tax_year = st.selectbox(
            "Exercice comptable / Année fiscale (au 31/12)",
            year_options,
            index=default_index,
            key="is_tax_rep_yr"
        )
    with col_info:
        st.write("")
        st.info(f"📅 **Exercice clos le 31 décembre {tax_year}** — Régime Réel Simplifié d'Imposition (RSI - Cerfa 2065 / 2033).")

    # Calculs complets via le moteur fiscal
    with st.spinner("Calcul des postes comptables et du bilan en cours..."):
        inc_stmt = compute_income_statement(tax_year)
        bal_sheet = compute_balance_sheet(tax_year)
        amort_schedule = inc_stmt["amort_schedule"]
        cerfa_codes = get_cerfa_codes(inc_stmt, bal_sheet)

    # 2. Métriques Clés en haut de page
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric(
        "Chiffre d'Affaires",
        f"{inc_stmt['gross_rental_income']:,.2f} €".replace(",", " "),
        help="Loyers nets encaissés hors charges de l'exercice"
    )
    k2.metric(
        "Résultat Net Comptable",
        f"{inc_stmt['net_accounting_result']:,.2f} €".replace(",", " "),
        delta="Bénéfice net" if inc_stmt['net_accounting_result'] >= 0 else "Déficit net",
        delta_color="normal" if inc_stmt['net_accounting_result'] >= 0 else "inverse",
        help="Résultat après impôt sur les sociétés (IS)"
    )
    k3.metric(
        "Total Bilan Net",
        f"{bal_sheet['total_actif_net']:,.2f} €".replace(",", " "),
        help="Total Actif Net = Total Passif au 31 décembre"
    )
    k4.metric(
        "Capitaux Propres",
        f"{bal_sheet['total_equity']:,.2f} €".replace(",", " "),
        help="Capital social + Report à nouveau + Résultat de l'exercice"
    )
    k5.metric(
        "Dettes Totales",
        f"{bal_sheet['total_debts']:,.2f} €".replace(",", " "),
        help="Emprunts bancaires (CRD) + Comptes courants associés + Dépôts + IS dû"
    )

    st.markdown("---")

    # 3. Onglets de Navigation
    tab_cr, tab_bilan, tab_amort, tab_cerfa = st.tabs([
        "📊 Compte de Résultat (2033-B)",
        "🏛️ Bilan Comptable (2033-A)",
        "📉 Amortissements (2033-C)",
        "📑 Cases Cerfa & Télédéclaration"
    ])

    # =========================================================================
    # ONGLET 1 : COMPTE DE RESULTAT (CERFA 2033-B)
    # =========================================================================
    with tab_cr:
        st.markdown("### 📊 Compte de Résultat Simplifié (Formulaire Cerfa 2033-B)")
        st.caption("Synthèse des flux de gestion, des amortissements et détermination du résultat fiscal IS.")

        # Détail sous forme de tableau comptable
        income_rows = [
            {"Poste": "I. PRODUITS D'EXPLOITATION", "Détail": "Chiffre d'affaires net (Loyers perçus hors charges)", "Montant (€)": inc_stmt["gross_rental_income"]},
            {"Poste": "II. CHARGES D'EXPLOITATION", "Détail": "Total des dépenses d'exploitation déductibles", "Montant (€)": -inc_stmt["total_operating_charges"]},
            {"Poste": "  • Frais de gestion & comptabilité", "Détail": "Honoraires expert-comptable, juridique, adhésion CGA", "Montant (€)": -inc_stmt["frais_gestion"]},
            {"Poste": "  • Primes d'assurance PNO", "Détail": "Assurance Propriétaire Non Occupant et responsabilité civile", "Montant (€)": -inc_stmt["assurances"]},
            {"Poste": "  • Impôts & taxes (Taxe foncière)", "Détail": "Taxe foncière acquittée hors taxe ordures ménagères (TEOM)", "Montant (€)": -inc_stmt["taxes_foncieres"]},
            {"Poste": "  • Entretien & petites réparations", "Détail": "Dépenses courantes de maintenance des biens", "Montant (€)": -inc_stmt["total_travaux_entretien"]},
            {"Poste": "  • Charges copropriété non récupérées", "Détail": "Quote-part propriétaire des charges d'immeuble", "Montant (€)": -inc_stmt["copro_non_recup"]},
            {"Poste": "  • Autres charges externes", "Détail": "Autres dépenses courantes d'exploitation", "Montant (€)": -inc_stmt["autres_charges_sci"]},
            {"Poste": "III. DOTATIONS AUX AMORTISSEMENTS (DAA)", "Détail": "Amortissement comptable de l'actif immobilisé", "Montant (€)": -inc_stmt["total_daa"]},
            {"Poste": "  • Amortissement de l'immeuble (bâti)", "Détail": "Amortissement linéaire (bâti hors terrain)", "Montant (€)": -inc_stmt["total_building_amort"]},
            {"Poste": "  • Amortissement du mobilier", "Détail": "Amortissement linéaire des agencements et meubles", "Montant (€)": -inc_stmt["total_furn_amort"]},
            {"Poste": "RÉSULTAT D'EXPLOITATION", "Détail": "Produits - Charges d'exploitation - Amortissements", "Montant (€)": inc_stmt["operating_result"]},
            {"Poste": "IV. CHARGES FINANCIÈRES", "Détail": "Frais financiers et intérêts d'emprunt", "Montant (€)": -inc_stmt["total_financial_charges"]},
            {"Poste": "  • Intérêts des emprunts bancaires", "Détail": "Part intérêts déductible des mensualités de crédit", "Montant (€)": -inc_stmt["interets_emprunt"]},
            {"Poste": "  • Frais bancaires et de compte", "Détail": "Frais de tenue de compte bancaire de la SCI", "Montant (€)": -inc_stmt["frais_bancaires"]},
            {"Poste": "RÉSULTAT COURANT AVANT IMPÔT (RCAI)", "Détail": "Base fiscale brute pour le calcul de l'IS", "Montant (€)": inc_stmt["rcai"]},
            {"Poste": "V. IMPÔT SUR LES SOCIÉTÉS (IS)", "Détail": "Taux réduit 15% (jusqu'à 42 500 €) / Taux normal 25%", "Montant (€)": -inc_stmt["is_tax"]},
            {"Poste": "RÉSULTAT NET COMPTABLE DE L'EXERCICE", "Détail": "Bénéfice net distribuable ou perte mise en report à nouveau", "Montant (€)": inc_stmt["net_accounting_result"]}
        ]

        df_cr = pd.DataFrame(income_rows)
        
        # Affichage avec style visuel
        st.dataframe(
            df_cr.style.format({"Montant (€)": lambda v: f"{v:,.2f} €".replace(",", " ")}),
            use_container_width=True,
            hide_index=True
        )

        col_g1, col_g2 = st.columns([3, 2])
        with col_g1:
            # Graphique en cascade ou barres
            categories_chart = ["Loyers", "Charges Expl.", "Amortissements", "Intérêts Prêt", "IS", "Résultat Net"]
            values_chart = [
                inc_stmt["gross_rental_income"],
                -inc_stmt["total_operating_charges"],
                -inc_stmt["total_daa"],
                -inc_stmt["total_financial_charges"],
                -inc_stmt["is_tax"],
                inc_stmt["net_accounting_result"]
            ]
            colors = ["#2563eb", "#ef4444", "#f59e0b", "#8b5cf6", "#dc2626", "#10b981" if inc_stmt["net_accounting_result"] >= 0 else "#ef4444"]
            fig_cr = go.Figure(go.Bar(
                x=categories_chart,
                y=values_chart,
                marker_color=colors,
                text=[f"{v:+,.0f} €".replace(",", " ") for v in values_chart],
                textposition="auto"
            ))
            fig_cr.update_layout(
                title="Décomposition du Résultat de l'Exercice",
                height=320,
                margin=dict(l=20, r=20, t=40, b=20),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)"
            )
            st.plotly_chart(fig_cr, use_container_width=True)

        with col_g2:
            st.markdown("#### Synthèse Fiscale IS")
            st.write(f"• **Assiette imposable (RCAI) :** `{inc_stmt['rcai']:,.2f} €`")
            if inc_stmt["rcai"] > 0:
                st.write(f"• **Tranche 15% (sous 42 500 €) :** `{inc_stmt['base_15']:,.2f} €` → `{inc_stmt['base_15'] * 0.15:,.2f} €` d'IS")
                if inc_stmt["base_25"] > 0:
                    st.write(f"• **Tranche 25% (au-delà) :** `{inc_stmt['base_25']:,.2f} €` → `{inc_stmt['base_25'] * 0.25:,.2f} €` d'IS")
                st.info(f"💼 **Total IS dû au Trésor Public :** `{inc_stmt['is_tax']:,.2f} €`")
            else:
                st.success("🟢 **Aucun impôt sur les sociétés dû pour cet exercice (déficit fiscal reportable sur les bénéfices futurs).**")

        # Export CSV Compte de Résultat
        csv_cr = df_cr.to_csv(index=False, sep=";").encode("utf-8")
        st.download_button(
            label="📥 Exporter le Compte de Résultat (CSV)",
            data=csv_cr,
            file_name=f"compte_de_resultat_cerfa2033B_{tax_year}.csv",
            mime="text/csv",
            key="dl_cr_csv"
        )

    # =========================================================================
    # ONGLET 2 : BILAN COMPTABLE (CERFA 2033-A)
    # =========================================================================
    with tab_bilan:
        st.markdown("### 🏛️ Bilan Comptable au 31 Décembre (Formulaire Cerfa 2033-A)")
        st.caption("Situation patrimoniale de la SCI à la clôture de l'exercice : Actif (ce que la SCI possède) vs Passif (ce que la SCI doit).")

        # Contrôle d'équilibre comptable
        if bal_sheet["is_balanced"]:
            st.success(f"✅ **Bilan Parfaitement Équilibré !** Total Actif Net (`{bal_sheet['total_actif_net']:,.2f} €`) = Total Passif (`{bal_sheet['total_passif']:,.2f} €`) — Écart de clôture : `0,00 €`.")
        else:
            st.warning(f"⚠️ Écart de contrôle comptable : {bal_sheet['balance_check']:,.2f} €.")

        col_actif, col_passif = st.columns(2)

        # ACTIF
        with col_actif:
            st.markdown("#### 🏢 ACTIF (au 31/12)")
            
            actif_data = [
                {"Rubrique": "ACTIF IMMOBILISÉ", "Brut (€)": bal_sheet["total_fixed_assets_gross"], "Amort. (€)": bal_sheet["total_fixed_assets_amort"], "Net (€)": bal_sheet["total_fixed_assets_net"]},
                {"Rubrique": "  • Terrains (non amortissables)", "Brut (€)": bal_sheet["land_gross"], "Amort. (€)": 0.0, "Net (€)": bal_sheet["land_gross"]},
                {"Rubrique": "  • Constructions & Immeubles", "Brut (€)": bal_sheet["building_gross"], "Amort. (€)": bal_sheet["building_amort_cumul"], "Net (€)": bal_sheet["building_net"]},
                {"Rubrique": "  • Matériel, mobilier & agencements", "Brut (€)": bal_sheet["furn_gross"], "Amort. (€)": bal_sheet["furn_amort_cumul"], "Net (€)": bal_sheet["furn_net"]},
                {"Rubrique": "ACTIF CIRCULANT", "Brut (€)": bal_sheet["total_current_assets"], "Amort. (€)": 0.0, "Net (€)": bal_sheet["total_current_assets"]},
                {"Rubrique": "  • Créances clients (Loyers échus non payés)", "Brut (€)": bal_sheet["tenant_receivables"], "Amort. (€)": 0.0, "Net (€)": bal_sheet["tenant_receivables"]},
                {"Rubrique": "  • Disponibilités (Banque & Trésorerie)", "Brut (€)": bal_sheet["cash_and_equivalents"], "Amort. (€)": 0.0, "Net (€)": bal_sheet["cash_and_equivalents"]},
                {"Rubrique": "TOTAL GÉNÉRAL DE L'ACTIF", "Brut (€)": bal_sheet["total_actif_gross"], "Amort. (€)": bal_sheet["total_actif_amort"], "Net (€)": bal_sheet["total_actif_net"]}
            ]
            df_actif = pd.DataFrame(actif_data)
            st.dataframe(
                df_actif.style.format({
                    "Brut (€)": lambda v: f"{v:,.2f} €".replace(",", " "),
                    "Amort. (€)": lambda v: f"{v:,.2f} €".replace(",", " "),
                    "Net (€)": lambda v: f"{v:,.2f} €".replace(",", " ")
                }),
                use_container_width=True,
                hide_index=True
            )

        # PASSIF
        with col_passif:
            st.markdown("#### ⚖️ PASSIF (au 31/12)")
            
            passif_data = [
                {"Rubrique": "CAPITAUX PROPRES", "Montant (€)": bal_sheet["total_equity"]},
                {"Rubrique": "  • Capital social statutaire", "Montant (€)": bal_sheet["share_capital"]},
                {"Rubrique": "  • Report à nouveau (exercices antérieurs)", "Montant (€)": bal_sheet["report_a_nouveau"]},
                {"Rubrique": "  • Résultat net de l'exercice N", "Montant (€)": bal_sheet["net_result"]},
                {"Rubrique": "DETTES", "Montant (€)": bal_sheet["total_debts"]},
                {"Rubrique": "  • Emprunts bancaires (CRD au 31/12)", "Montant (€)": bal_sheet["total_loan_crd"]},
                {"Rubrique": "      - dont part à moins d'un an (N+1)", "Montant (€)": bal_sheet["loan_crd_less_1y"]},
                {"Rubrique": "      - dont part à plus d'un an", "Montant (€)": bal_sheet["loan_crd_more_1y"]},
                {"Rubrique": "  • Comptes Courants d'Associés (CCA)", "Montant (€)": bal_sheet["total_cca_balance"]},
                {"Rubrique": "  • Dépôts de garantie des locataires", "Montant (€)": bal_sheet["total_deposits"]},
                {"Rubrique": "  • Dettes fiscales (IS N à payer)", "Montant (€)": bal_sheet["tax_liability"]},
                {"Rubrique": "TOTAL GÉNÉRAL DU PASSIF", "Montant (€)": bal_sheet["total_passif"]}
            ]
            df_passif = pd.DataFrame(passif_data)
            st.dataframe(
                df_passif.style.format({
                    "Montant (€)": lambda v: f"{v:,.2f} €".replace(",", " ")
                }),
                use_container_width=True,
                hide_index=True
            )

        st.markdown("---")
        st.markdown("#### 📈 Indicateurs et Ratios de Santé Financière")
        r1, r2, r3 = st.columns(3)
        autonomie = (bal_sheet["total_equity"] / bal_sheet["total_passif"] * 100.0) if bal_sheet["total_passif"] > 0 else 0.0
        endettement = (bal_sheet["total_loan_crd"] / bal_sheet["total_passif"] * 100.0) if bal_sheet["total_passif"] > 0 else 0.0
        fonds_roulement = bal_sheet["total_equity"] + bal_sheet["loan_crd_more_1y"] - bal_sheet["total_fixed_assets_net"]

        r1.metric("Autonomie Financière", f"{autonomie:.1f} %", help="Capitaux Propres / Total Bilan")
        r2.metric("Taux d'Endettement Bancaire", f"{endettement:.1f} %", help="Emprunts Bancaires / Total Bilan")
        r3.metric(
            "Fonds de Roulement Net (FRNG)",
            f"{fonds_roulement:,.2f} €".replace(",", " "),
            delta="Ressources durables suffisantes" if fonds_roulement >= 0 else "Besoin de trésorerie",
            delta_color="normal" if fonds_roulement >= 0 else "inverse"
        )

        # Export CSV Bilan complet
        export_bilan_rows = []
        for r in actif_data:
            export_bilan_rows.append({"Type": "ACTIF", "Rubrique": r["Rubrique"], "Brut (€)": r["Brut (€)"], "Amort. (€)": r["Amort. (€)"], "Net (€)": r["Net (€)"]})
        for r in passif_data:
            export_bilan_rows.append({"Type": "PASSIF", "Rubrique": r["Rubrique"], "Brut (€)": r["Montant (€)"], "Amort. (€)": 0.0, "Net (€)": r["Montant (€)"]})

        df_export_bilan = pd.DataFrame(export_bilan_rows)
        csv_bilan = df_export_bilan.to_csv(index=False, sep=";").encode("utf-8")
        st.download_button(
            label="📥 Exporter le Bilan Complet Actif / Passif (CSV)",
            data=csv_bilan,
            file_name=f"bilan_comptable_cerfa2033A_{tax_year}.csv",
            mime="text/csv",
            key="dl_bilan_csv"
        )

    # =========================================================================
    # ONGLET 3 : IMMOBILISATIONS & AMORTISSEMENTS (CERFA 2033-C)
    # =========================================================================
    with tab_amort:
        st.markdown("### 📉 Tableau des Immobilisations & Amortissements (Cerfa 2033-C)")
        st.caption("Détail bien par bien de l'assiette foncière, du bâti amortissable, des dotations annuelles et de la VNC.")

        if not amort_schedule:
            st.info("Aucun bien immobilier acquis au plus tard au 31/12 de cet exercice.")
        else:
            disp_amort = []
            for item in amort_schedule:
                disp_amort.append({
                    "Bien": item["name"],
                    "Date d'achat": item["acquisition_date"],
                    "Prix total (€)": item["total_cost"],
                    "Part Terrain (€)": item["land_value"],
                    "Bâti amortissable (€)": item["building_base"],
                    "Annuité Bâti (€)": item["annual_building_full"],
                    "Amort. Antérieurs (€)": item["prior_amort_total"],
                    "Dotation N (€)": item["dotation_total"],
                    "Amort. Cumulés 31/12 (€)": item["cumul_amort_total"],
                    "VNC Clôture (€)": item["vnc_total"]
                })

            df_sched = pd.DataFrame(disp_amort)
            st.dataframe(
                df_sched.style.format({
                    "Prix total (€)": lambda v: f"{v:,.2f} €".replace(",", " "),
                    "Part Terrain (€)": lambda v: f"{v:,.2f} €".replace(",", " "),
                    "Bâti amortissable (€)": lambda v: f"{v:,.2f} €".replace(",", " "),
                    "Annuité Bâti (€)": lambda v: f"{v:,.2f} €".replace(",", " "),
                    "Amort. Antérieurs (€)": lambda v: f"{v:,.2f} €".replace(",", " "),
                    "Dotation N (€)": lambda v: f"{v:,.2f} €".replace(",", " "),
                    "Amort. Cumulés 31/12 (€)": lambda v: f"{v:,.2f} €".replace(",", " "),
                    "VNC Clôture (€)": lambda v: f"{v:,.2f} €".replace(",", " ")
                }),
                use_container_width=True,
                hide_index=True
            )

            st.markdown(f"""
            💡 **Règle fiscale d'amortissement IS appliquée :**
            - **Quote-part terrain :** Non amortissable conformément au CGI.
            - **Prorata temporis l'année d'acquisition :** Calcul exact au nombre de jours de détention entre la date d'achat et le 31 décembre.
            - **VNC (Valeur Nette Comptable) :** Coût d'achat initial - Total des amortissements cumulés déduits.
            """)

            csv_amort = df_sched.to_csv(index=False, sep=";").encode("utf-8")
            st.download_button(
                label="📥 Exporter le Tableau des Amortissements (CSV)",
                data=csv_amort,
                file_name=f"tableau_amortissements_cerfa2033C_{tax_year}.csv",
                mime="text/csv",
                key="dl_amort_csv"
            )

    # =========================================================================
    # ONGLET 4 : CASES CERFA DGFiP & TELESIGALEMENT
    # =========================================================================
    with tab_cerfa:
        st.markdown("### 📑 Correspondance des Cases Cerfa 2033 (DGFiP)")
        st.caption("Grille de report direct pour votre télédéclaration sur impots.gouv.fr (Liasses 2065 / 2033).")

        df_cerfa = pd.DataFrame(cerfa_codes)
        
        # Filtre de recherche
        f_type = st.radio("Filtrer par formulaire Cerfa :", ["Tous", "2033-A (Actif)", "2033-A (Passif)", "2033-B"], horizontal=True)
        if f_type != "Tous":
            filtered_df = df_cerfa[df_cerfa["Cerfa"].str.contains(f_type, case=False, na=False)]
        else:
            filtered_df = df_cerfa

        st.dataframe(
            filtered_df.style.format({"Montant (€)": lambda v: f"{v:,.2f} €".replace(",", " ")}),
            use_container_width=True,
            hide_index=True
        )

        csv_cerfa = df_cerfa.to_csv(index=False, sep=";").encode("utf-8")
        st.download_button(
            label="📥 Télécharger le Pack Liasse Fiscale Officiel (CSV complet avec N° de cases)",
            data=csv_cerfa,
            file_name=f"liasse_fiscale_cerfa2033_cases_{tax_year}.csv",
            mime="text/csv",
            key="dl_cerfa_pack_csv"
        )
