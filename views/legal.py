"""
Vue Documents Juridiques & Locatifs :
- Avis d'échéance (Appels de loyer)
- Relances d'impayés graduées (J+7 amiable, J+21 mise en demeure LRAR)
- Indexation annuelle IRL (INSEE) et courriers de révision
- Procès-Verbal d'Assemblée Générale Ordinaire (PV d'AGO annuelle d'approbation des comptes)
"""
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from datetime import date
from database import query_rows, query_one, execute_write
from utils.legal_docs import (
    generate_avis_echeance_html,
    generate_relance_amiable_html,
    generate_mise_en_demeure_html,
    generate_pv_ago_html,
    MONTH_NAMES
)
from utils.irl import calculate_irl_revision, generate_irl_letter_html
from utils.mailer import send_email

def render_legal():
    st.markdown("## 📄 Documents Juridiques & Gestion Locative")
    st.caption("Générez vos avis d'échéance, relances formelles, courriers de révision IRL et procès-verbaux d'Assemblée Générale.")

    tab_avis, tab_relances, tab_irl, tab_ago = st.tabs([
        "📫 Avis d'Échéance",
        "🚨 Relances d'Impayés",
        "📈 Révision des Loyers (IRL)",
        "🏛️ PV d'Assemblée Générale (AGO)"
    ])

    sci_info = query_one("SELECT * FROM sci_info WHERE id = 1;") or {}

    # 1. AVIS D'ECHEANCE
    with tab_avis:
        st.markdown("#### Générateur d'Avis d'Échéance / Appel de Loyer")
        active_tenants = query_rows("""
            SELECT t.*, p.name as property_name, p.address as prop_address, p.city as prop_city, p.postal_code as prop_postal
            FROM tenants t
            JOIN properties p ON t.property_id = p.id
            WHERE t.is_active = 1
            ORDER BY t.last_name ASC;
        """)

        if not active_tenants:
            st.info("Aucun locataire actif.")
        else:
            col1, col2, col3 = st.columns(3)
            with col1:
                t_map = {t["id"]: f"{t['first_name']} {t['last_name']} ({t['property_name']})" for t in active_tenants}
                sel_t_id = st.selectbox("Locataire destinataire :", options=list(t_map.keys()), format_func=lambda x: t_map[x], key="avis_t")
            with col2:
                cur_d = date.today()
                sel_m = st.selectbox("Mois du terme :", list(range(1, 13)), index=cur_d.month - 1, format_func=lambda m: MONTH_NAMES[m], key="avis_m")
            with col3:
                sel_y = st.selectbox("Année :", list(range(cur_d.year - 1, cur_d.year + 2)), index=1, key="avis_y")

            sel_t = next((t for t in active_tenants if t["id"] == sel_t_id), None)
            due_date_str = f"{sel_y:04d}-{sel_m:02d}-05"

            if sel_t:
                p_info = {"address": sel_t["prop_address"], "city": sel_t["prop_city"], "postal_code": sel_t["prop_postal"]}
                html_avis = generate_avis_echeance_html(sci_info, sel_t, p_info, sel_m, sel_y, due_date_str)

                c_act1, c_act2 = st.columns([1, 1])
                with c_act1:
                    st.download_button(
                        label="💾 Télécharger l'Avis d'Échéance (HTML/PDF)",
                        data=html_avis,
                        file_name=f"avis_echeance_{sel_t['last_name']}_{sel_y}_{sel_m:02d}.html",
                        mime="text/html",
                        key="dl_avis"
                    )
                with c_act2:
                    if sel_t.get("email"):
                        if st.button(f"📧 Envoyer l'avis par email à {sel_t['email']}", key="send_email_avis"):
                            subject = f"Avis d'échéance - Loyer {MONTH_NAMES[sel_m]} {sel_y} - {sci_info.get('name')}"
                            success, msg = send_email(sel_t["email"], subject, html_avis, f"Avis_{MONTH_NAMES[sel_m]}_{sel_y}.html", html_avis)
                            if success:
                                st.success(msg)
                            else:
                                st.error(msg)
                    else:
                        st.caption("⚠️ Aucun email renseigné sur la fiche de ce locataire.")

                components.html(html_avis, height=520, scrolling=True)

    # 2. RELANCES D'IMPAYES
    with tab_relances:
        st.markdown("#### Gestion des Impayés & Courriers de Relance")
        unpaid = query_rows("""
            SELECT rp.*, 
                   t.first_name, t.last_name, t.email, t.guarantor_info,
                   p.name as property_name, p.address as prop_address, p.city as prop_city, p.postal_code as prop_postal
            FROM rent_payments rp
            JOIN tenants t ON rp.tenant_id = t.id
            JOIN properties p ON rp.property_id = p.id
            WHERE rp.status IN ('en_attente', 'retard', 'partiel')
            ORDER BY rp.due_date ASC;
        """)

        if not unpaid:
            st.success("🎉 Aucun impayé ni retard de loyer à ce jour !")
        else:
            for item in unpaid:
                bal = item["total_due"] - item["amount_paid"]
                period = f"{MONTH_NAMES[item['period_month']]} {item['period_year']}"
                with st.expander(f"⚠️ {item['first_name']} {item['last_name'].upper()} — {period} (Reste dû : {bal:.2f} €)", expanded=True):
                    rc1, rc2 = st.columns(2)
                    with rc1:
                        st.markdown(f"**Logement :** {item['property_name']}")
                        st.markdown(f"**Date d'exigibilité :** {item['due_date']}")
                        st.markdown(f"**Montant impayé :** <span style='color:red; font-weight:bold;'>{bal:.2f} €</span>", unsafe_allow_html=True)
                    with rc2:
                        relance_type = st.radio(
                            "Type de procédure :",
                            ["Niveau 1 : Relance amiable (J+7)", "Niveau 2 : Mise en demeure formelle LRAR (J+21)"],
                            key=f"rel_type_{item['id']}"
                        )

                    p_inf = {"address": item["prop_address"], "city": item["prop_city"], "postal_code": item["prop_postal"]}
                    if "Niveau 1" in relance_type:
                        html_relance = generate_relance_amiable_html(sci_info, item, p_inf, item)
                        fn = f"relance_amiable_{item['last_name']}.html"
                    else:
                        html_relance = generate_mise_en_demeure_html(sci_info, item, p_inf, item)
                        fn = f"mise_en_demeure_LRAR_{item['last_name']}.html"

                    b1, b2 = st.columns(2)
                    with b1:
                        st.download_button("💾 Télécharger le courrier", data=html_relance, file_name=fn, key=f"dl_rel_{item['id']}")
                    with b2:
                        if item.get("email"):
                            if st.button(f"📧 Envoyer par email à {item['email']}", key=f"send_rel_{item['id']}"):
                                subj = f"IMPORTANT : Relance loyer impayé - {period} - {sci_info.get('name')}"
                                ok, msg = send_email(item["email"], subj, html_relance, fn, html_relance)
                                if ok:
                                    st.success(msg)
                                else:
                                    st.error(msg)

                    components.html(html_relance, height=450, scrolling=True)

    # 3. REVISION IRL (INSEE)
    with tab_irl:
        st.markdown("#### 📈 Indexation Annuelle selon l'IRL de l'INSEE")
        st.caption("Révision annuelle légale des loyers basée sur la clause d'indexation du bail.")

        # Affichage des indices enregistrés
        indices = query_rows("SELECT quarter, value, published_date FROM irl_indices ORDER BY id DESC;")
        with st.expander("Voir / Mettre à jour la table des indices IRL INSEE", expanded=False):
            st.dataframe(pd.DataFrame(indices), use_container_width=True, hide_index=True)
            with st.form("form_add_irl"):
                st.markdown("**Ajouter un nouvel indice trimestriel publié :**")
                ai1, ai2, ai3 = st.columns(3)
                with ai1:
                    new_q = st.text_input("Trimestre (ex: T2 2025)")
                with ai2:
                    new_v = st.number_input("Valeur IRL", min_value=100.0, max_value=200.0, value=145.80, step=0.01)
                with ai3:
                    new_d = st.date_input("Date publication JO", value=date.today()).strftime("%Y-%m-%d")
                if st.form_submit_button("Ajouter l'indice"):
                    if new_q.strip():
                        execute_write("INSERT OR REPLACE INTO irl_indices (quarter, value, published_date) VALUES (?, ?, ?);", [new_q.strip(), new_v, new_d])
                        st.success(f"Indice {new_q} ajouté !")
                        st.rerun()

        # Simulateur et révision pour les locataires actifs
        tenants_for_irl = query_rows("""
            SELECT t.*, p.name as property_name, p.address as prop_address, p.city as prop_city, p.postal_code as prop_postal
            FROM tenants t
            JOIN properties p ON t.property_id = p.id
            WHERE t.is_active = 1
            ORDER BY t.last_name ASC;
        """)

        if tenants_for_irl:
            st.markdown("---")
            st.markdown("##### Calculateur de Révision de Loyer")
            t_irl_map = {t["id"]: f"{t['first_name']} {t['last_name']} — Bail du {t['lease_start']} (Loyer actuel : {t['rent_amount']:.2f} €)" for t in tenants_for_irl}
            selected_t_id = st.selectbox("Sélectionnez le locataire à réviser :", options=list(t_irl_map.keys()), format_func=lambda x: t_irl_map[x], key="irl_t_sel")
            target_t = next((t for t in tenants_for_irl if t["id"] == selected_t_id), None)

            if target_t:
                ind_quarters = [ind["quarter"] for ind in indices]
                ind_dict = {ind["quarter"]: ind["value"] for ind in indices}

                old_q_default = target_t.get("irl_reference_quarter") or (ind_quarters[-2] if len(ind_quarters) > 1 else ind_quarters[0])
                new_q_default = ind_quarters[0]

                ic1, ic2, ic3 = st.columns(3)
                with ic1:
                    old_q = st.selectbox("Indice d'origine (précédent)", ind_quarters, index=ind_quarters.index(old_q_default) if old_q_default in ind_quarters else 0, key="irl_old_q")
                    old_val = ind_dict[old_q]
                    st.caption(f"Valeur : **{old_val:.2f}**")
                with ic2:
                    new_q = st.selectbox("Nouvel indice applicable", ind_quarters, index=ind_quarters.index(new_q_default) if new_q_default in ind_quarters else 0, key="irl_new_q")
                    new_val = ind_dict[new_q]
                    st.caption(f"Valeur : **{new_val:.2f}**")
                with ic3:
                    eff_date = st.date_input("Date d'effet de la révision", value=date.today(), key="irl_eff_date").strftime("%Y-%m-%d")

                old_rent = float(target_t["rent_amount"])
                revised_rent = calculate_irl_revision(old_rent, old_val, new_val)
                diff = revised_rent - old_rent

                st.markdown("---")
                mc1, mc2, mc3 = st.columns(3)
                mc1.metric("Loyer HC Actuel", f"{old_rent:.2f} €")
                mc2.metric("Nouveau Loyer Révisé", f"{revised_rent:.2f} €", delta=f"+{diff:.2f} € / mois (+{(new_val-old_val)/old_val*100:.2f}%)")
                mc3.metric("Nouveau Total CC", f"{revised_rent + float(target_t.get('charges_provision', 0)):.2f} €")

                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    if st.button("✅ Valider et appliquer le nouveau loyer au bail", type="primary", key="apply_irl_btn"):
                        execute_write("""
                            UPDATE tenants 
                            SET rent_amount = ?, irl_reference_quarter = ?, irl_reference_value = ?, last_revision_date = ?
                            WHERE id = ?;
                        """, [revised_rent, new_q, new_val, eff_date, target_t["id"]])
                        st.success(f"Le loyer de {target_t['first_name']} {target_t['last_name']} a été mis à jour à {revised_rent:.2f} € !")
                        st.rerun()

                # Lettre de révision
                p_inf = {"address": target_t["prop_address"], "city": target_t["prop_city"], "postal_code": target_t["prop_postal"]}
                html_irl = generate_irl_letter_html(sci_info, target_t, p_inf, old_rent, revised_rent, old_q, old_val, new_q, new_val, eff_date)
                
                with col_btn2:
                    st.download_button(
                        "📄 Télécharger la lettre de notification IRL (HTML/PDF)",
                        data=html_irl,
                        file_name=f"revision_loyer_{target_t['last_name']}_{new_q}.html",
                        key="dl_irl_doc"
                    )

                components.html(html_irl, height=520, scrolling=True)

    # 4. PV D'AGO ANNUELLE
    with tab_ago:
        st.markdown("#### 🏛️ Procès-Verbal d'Assemblée Générale Ordinaire (PV d'AGO)")
        st.caption("Document juridique officiel obligatoire chaque année pour approuver les comptes de la SCI et affecter le résultat.")

        ago_year = st.selectbox("Exercice comptable à approuver :", list(range(date.today().year - 3, date.today().year + 1)), index=len(range(date.today().year - 3, date.today().year + 1)) - 1, key="ago_yr")

        from utils.tax_calculator import compute_income_statement
        inc = compute_income_statement(ago_year)
        gross_inc = inc["gross_rental_income"]
        op_exp = inc["total_operating_charges"]
        daa = inc["total_daa"]
        fin_exp = inc["total_financial_charges"]
        rcai = inc["rcai"]
        is_tax = inc["is_tax"]
        net_res = inc["net_accounting_result"]

        html_ago = generate_pv_ago_html(sci_info, ago_year, gross_inc, op_exp, daa, fin_exp, rcai, is_tax, net_res)

        st.download_button(
            label="💾 Télécharger le PV d'AGO complet (HTML/PDF imprimable)",
            data=html_ago,
            file_name=f"PV_AGO_SCI_{sci_info.get('name', 'SCI')}_{ago_year}.html",
            mime="text/html",
            key="dl_pv_ago"
        )

        components.html(html_ago, height=600, scrolling=True)
