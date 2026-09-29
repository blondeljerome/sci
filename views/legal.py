"""Vue Documents Juridiques & Locatifs :

- Avis d'échéance (Appels de loyer)
- Relances d'impayés graduées (J+7 amiable, J+21 mise en demeure LRAR)
- Indexation annuelle IRL (INSEE) et courriers de révision
- Procès-Verbal d'Assemblée Générale Ordinaire
  (PV d'AGO annuelle d'approbation des comptes)
"""

from datetime import date

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from database import execute_write, query_one, query_rows
from utils import storage
from utils.irl import calculate_irl_revision, generate_irl_letter_html
from utils.legal_docs import (
    MONTH_NAMES,
    generate_avis_echeance_html,
    generate_avis_echeance_pdf,
    generate_mise_en_demeure_html,
    generate_pv_ago_html,
    generate_relance_amiable_html,
    save_avis_echeance_to_ged,
)
from utils.mailer import send_email


def render_legal() -> None:
    """Affiche la vue des documents juridiques et de gestion locative."""
    st.markdown("## 📄 Documents Juridiques & Gestion Locative")
    st.caption(
        "Générez vos avis d'échéance, relances formelles, courriers "
        "de révision IRL et procès-verbaux d'Assemblée Générale."
    )

    tab_avis, tab_relances, tab_irl, tab_ago = st.tabs(
        [
            "📫 Avis d'Échéance",
            "🚨 Relances d'Impayés",
            "📈 Révision des Loyers (IRL)",
            "🏛️ PV d'Assemblée Générale (AGO)",
        ]
    )

    sci_info = query_one("SELECT * FROM sci_info WHERE id = 1;") or {}

    # 1. AVIS D'ECHEANCE
    with tab_avis:
        st.markdown("#### Générateur d'Avis d'Échéance / Appel de Loyer")
        active_tenants = query_rows("""
            SELECT t.*, p.name as property_name, p.address as prop_address,
                   p.city as prop_city, p.postal_code as prop_postal
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
                t_map = {
                    t["id"]: (
                        f"{t['first_name']} {t['last_name']} "
                        f"({t['property_name']})"
                    )
                    for t in active_tenants
                }
                sel_t_id = st.selectbox(
                    "Locataire destinataire :",
                    options=list(t_map.keys()),
                    format_func=lambda x: t_map[x],
                    key="avis_t",
                )
            with col2:
                cur_d = date.today()
                sel_m = st.selectbox(
                    "Mois du terme :",
                    list(range(1, 13)),
                    index=cur_d.month - 1,
                    format_func=lambda m: MONTH_NAMES[m],
                    key="avis_m",
                )
            with col3:
                sel_y = st.selectbox(
                    "Année :",
                    list(range(cur_d.year - 1, cur_d.year + 2)),
                    index=1,
                    key="avis_y",
                )

            sel_t = next(
                (t for t in active_tenants if t["id"] == sel_t_id), None
            )
            due_date_str = f"{sel_y:04d}-{sel_m:02d}-05"

            if sel_t:
                p_info = {
                    "id": sel_t["property_id"],
                    "name": sel_t["property_name"],
                    "address": sel_t["prop_address"],
                    "city": sel_t["prop_city"],
                    "postal_code": sel_t["prop_postal"],
                }
                html_avis = generate_avis_echeance_html(
                    sci_info, sel_t, p_info, sel_m, sel_y, due_date_str
                )
                pdf_avis = generate_avis_echeance_pdf(
                    sci_info, sel_t, p_info, sel_m, sel_y, due_date_str
                )
                pdf_avis_name = (
                    f"appel_loyer_{sel_t['last_name']}_{sel_y}_{sel_m:02d}.pdf"
                )

                # Vérifier si déjà archivé dans la GED
                existing_doc = query_one(
                    """
                    SELECT id, file_path, cloudinary_public_id FROM documents 
                    WHERE category = ? 
                      AND tenant_id = ? 
                      AND notes LIKE ?;
                """,
                    [
                        "Appel de loyer & Avis d'échéance",
                        sel_t["id"],
                        f"%Terme {sel_m:02d}/{sel_y}%",
                    ],
                )

                c_act1, c_act2, c_act3 = st.columns(3)
                with c_act1:
                    # Téléchargement direct depuis la GED si déjà archivé
                    ged_bytes = None
                    if existing_doc and existing_doc.get(
                        "cloudinary_public_id"
                    ):
                        ged_bytes = storage.download_file_bytes(
                            existing_doc["cloudinary_public_id"]
                        )
                    dl_data = ged_bytes if ged_bytes else pdf_avis
                    st.download_button(
                        label="📥 Télécharger l'Avis (GED)"
                        if ged_bytes
                        else "📥 Télécharger l'Avis (PDF)",
                        data=dl_data,
                        file_name=pdf_avis_name,
                        mime="application/pdf",
                        key="dl_avis_pdf",
                        use_container_width=True,
                    )
                with c_act2:
                    ged_btn_label = (
                        "✅ Appel à jour dans la GED"
                        if existing_doc
                        else "📎 Archiver dans la GED"
                    )
                    if st.button(
                        ged_btn_label,
                        key="save_ged_avis_btn",
                        use_container_width=True,
                    ):
                        # Chercher paiement éventuel associé pour mise à jour
                        p_match = query_one(
                            "SELECT id FROM rent_payments WHERE tenant_id = ? "
                            "AND period_month = ? AND period_year = ?;",
                            [sel_t["id"], sel_m, sel_y],
                        )
                        p_match_id = p_match["id"] if p_match else None
                        ok_g, msg_g, _ = save_avis_echeance_to_ged(
                            sci_info,
                            sel_t,
                            p_info,
                            sel_m,
                            sel_y,
                            due_date_str,
                            payment_id=p_match_id,
                        )
                        if ok_g:
                            st.success(msg_g)
                            st.rerun()
                        else:
                            st.error(msg_g)
                with c_act3:
                    if sel_t.get("email"):
                        if st.button(
                            "📧 Envoyer par email (PDF)",
                            key="send_email_avis",
                            use_container_width=True,
                        ):
                            m_name = MONTH_NAMES[sel_m]
                            sci_n = sci_info.get("name")
                            subject = (
                                f"Avis d'échéance - Loyer {m_name} {sel_y} - "
                                f"{sci_n}"
                            )
                            success, msg = send_email(
                                sel_t["email"],
                                subject,
                                html_avis,
                                pdf_avis_name,
                                pdf_avis,
                            )
                            if success:
                                st.success(msg)
                            else:
                                st.error(msg)
                    else:
                        st.caption(
                            "⚠️ Aucun email renseigné pour ce locataire."
                        )

                if existing_doc and (
                    existing_doc.get("cloudinary_public_id")
                    or existing_doc.get("file_path")
                ):
                    ged_preview = storage.get_preview_url(
                        existing_doc.get("cloudinary_public_id"),
                        existing_doc.get("file_path"),
                    )
                    st.markdown(
                        "✅ **Document archivé dans la GED Cloudinary :** "
                        f"[👁️ Voir dans le navigateur]({ged_preview})"
                    )

                components.html(html_avis, height=520, scrolling=True)

    # 2. RELANCES D'IMPAYES
    with tab_relances:
        st.markdown("#### Gestion des Impayés & Courriers de Relance")
        unpaid = query_rows("""
            SELECT rp.*, 
                   t.first_name, t.last_name, t.email, t.guarantor_info,
                   p.name as property_name, p.address as prop_address,
                   p.city as prop_city, p.postal_code as prop_postal
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
                m_str = MONTH_NAMES[item["period_month"]]
                period = f"{m_str} {item['period_year']}"
                t_fullname = f"{item['first_name']} {item['last_name'].upper()}"
                exp_label = (
                    f"⚠️ {t_fullname} — {period} (Reste dû : {bal:.2f} €)"
                )
                with st.expander(exp_label, expanded=True):
                    rc1, rc2 = st.columns(2)
                    with rc1:
                        st.markdown(f"**Logement :** {item['property_name']}")
                        st.markdown(
                            f"**Date d'exigibilité :** {item['due_date']}"
                        )
                        st.markdown(
                            f"**Montant impayé :** "
                            f"<span style='color:red; font-weight:bold;'>"
                            f"{bal:.2f} €</span>",
                            unsafe_allow_html=True,
                        )
                    with rc2:
                        relance_type = st.radio(
                            "Type de procédure :",
                            [
                                "Niveau 1 : Relance amiable (J+7)",
                                "Niveau 2 : Mise en demeure LRAR (J+21)",
                            ],
                            key=f"rel_type_{item['id']}",
                        )

                    p_inf = {
                        "address": item["prop_address"],
                        "city": item["prop_city"],
                        "postal_code": item["prop_postal"],
                    }
                    if "Niveau 1" in relance_type:
                        html_relance = generate_relance_amiable_html(
                            sci_info, item, p_inf, item
                        )
                        fn = f"relance_amiable_{item['last_name']}.html"
                    else:
                        html_relance = generate_mise_en_demeure_html(
                            sci_info, item, p_inf, item
                        )
                        fn = f"mise_en_demeure_LRAR_{item['last_name']}.html"

                    b1, b2 = st.columns(2)
                    with b1:
                        st.download_button(
                            "💾 Télécharger le courrier",
                            data=html_relance,
                            file_name=fn,
                            key=f"dl_rel_{item['id']}",
                        )
                    with b2:
                        if item.get("email"):
                            if st.button(
                                f"📧 Envoyer par email à {item['email']}",
                                key=f"send_rel_{item['id']}",
                            ):
                                sci_title = sci_info.get("name")
                                subj = (
                                    "IMPORTANT : Relance loyer impayé - "
                                    f"{period} - {sci_title}"
                                )
                                ok, msg = send_email(
                                    item["email"],
                                    subj,
                                    html_relance,
                                    fn,
                                    html_relance,
                                )
                                if ok:
                                    st.success(msg)
                                else:
                                    st.error(msg)

                    components.html(html_relance, height=450, scrolling=True)

    # 3. REVISION IRL (INSEE)
    with tab_irl:
        st.markdown("#### 📈 Indexation Annuelle selon l'IRL de l'INSEE")
        st.caption(
            "Révision annuelle légale des loyers basée sur la clause "
            "d'indexation du bail."
        )

        # Affichage des indices enregistrés triés chronologiquement
        indices = query_rows("""
            SELECT quarter, value, published_date 
            FROM irl_indices 
            ORDER BY CAST(SUBSTR(quarter, 4, 4) AS INTEGER) DESC,
                     CAST(SUBSTR(quarter, 2, 1) AS INTEGER) DESC;
        """)
        with st.expander(
            "Voir / Mettre à jour la table des indices IRL INSEE",
            expanded=False,
        ):
            col_s1, col_s2 = st.columns([2, 1])
            with col_s1:
                st.markdown(
                    f"**Indices ({len(indices)} trimestres disponibles) :**"
                )
            with col_s2:
                from utils.irl import sync_irl_indices_to_db

                if st.button(
                    "🔄 Récupérer les IRL en ligne",
                    key="btn_sync_irl_legal",
                    help=(
                        "Télécharge automatiquement les derniers indices "
                        "depuis Service-Public.fr et ANIL"
                    ),
                ):
                    with st.spinner("Téléchargement des indices en ligne..."):
                        sync_res = sync_irl_indices_to_db()
                        if sync_res["success"]:
                            last_q = sync_res['latest_quarter']
                            last_v = sync_res['latest_value']
                            st.success(
                                f"✅ {sync_res['count']} indices synchronisés !"
                                f" Dernier : {last_q} ({last_v})"
                            )
                            st.rerun()
                        else:
                            st.error(sync_res["message"])

            st.dataframe(
                pd.DataFrame(indices), use_container_width=True, hide_index=True
            )
            with st.form("form_add_irl"):
                st.markdown("**Ajouter manuellement un indice trimestriel :**")
                ai1, ai2, ai3 = st.columns(3)
                with ai1:
                    new_q = st.text_input("Trimestre (ex: T3 2026)")
                with ai2:
                    new_v = st.number_input(
                        "Valeur IRL",
                        min_value=100.0,
                        max_value=200.0,
                        value=148.50,
                        step=0.01,
                    )
                with ai3:
                    new_d = st.date_input(
                        "Date publication JO", value=date.today()
                    ).strftime("%Y-%m-%d")
                if st.form_submit_button("Ajouter l'indice"):
                    if new_q.strip():
                        execute_write(
                            """
                            INSERT OR REPLACE INTO irl_indices (
                                quarter, value, published_date
                            ) VALUES (?, ?, ?);
                            """,
                            [new_q.strip(), new_v, new_d],
                        )
                        st.success(f"Indice {new_q} ajouté !")
                        st.rerun()

        # Simulateur et révision pour les locataires actifs
        tenants_for_irl = query_rows("""
            SELECT t.*, p.name as property_name, p.address as prop_address,
                   p.city as prop_city, p.postal_code as prop_postal
            FROM tenants t
            JOIN properties p ON t.property_id = p.id
            WHERE t.is_active = 1
            ORDER BY t.last_name ASC;
        """)

        if tenants_for_irl:
            st.markdown("---")
            st.markdown("##### Calculateur de Révision de Loyer")
            t_irl_map = {
                t["id"]: (
                    f"{t['first_name']} {t['last_name']} — "
                    f"Bail du {t['lease_start']} "
                    f"(Loyer actuel : {t['rent_amount']:.2f} €)"
                )
                for t in tenants_for_irl
            }
            selected_t_id = st.selectbox(
                "Sélectionnez le locataire à réviser :",
                options=list(t_irl_map.keys()),
                format_func=lambda x: t_irl_map[x],
                key="irl_t_sel",
            )
            target_t = next(
                (t for t in tenants_for_irl if t["id"] == selected_t_id), None
            )

            if target_t:
                ind_quarters = [ind["quarter"] for ind in indices]
                ind_dict = {ind["quarter"]: ind["value"] for ind in indices}

                old_q_default = target_t.get("irl_reference_quarter") or (
                    ind_quarters[-2]
                    if len(ind_quarters) > 1
                    else ind_quarters[0]
                )
                new_q_default = ind_quarters[0]

                ic1, ic2, ic3 = st.columns(3)
                with ic1:
                    old_q = st.selectbox(
                        "Indice d'origine (précédent)",
                        ind_quarters,
                        index=ind_quarters.index(old_q_default)
                        if old_q_default in ind_quarters
                        else 0,
                        key="irl_old_q",
                    )
                    old_val = ind_dict[old_q]
                    st.caption(f"Valeur : **{old_val:.2f}**")
                with ic2:
                    new_q = st.selectbox(
                        "Nouvel indice applicable",
                        ind_quarters,
                        index=ind_quarters.index(new_q_default)
                        if new_q_default in ind_quarters
                        else 0,
                        key="irl_new_q",
                    )
                    new_val = ind_dict[new_q]
                    st.caption(f"Valeur : **{new_val:.2f}**")
                with ic3:
                    eff_date = st.date_input(
                        "Date d'effet de la révision",
                        value=date.today(),
                        key="irl_eff_date",
                    ).strftime("%Y-%m-%d")

                old_rent = float(target_t["rent_amount"])
                revised_rent = calculate_irl_revision(
                    old_rent, old_val, new_val
                )
                diff = revised_rent - old_rent

                st.markdown("---")
                mc1, mc2, mc3 = st.columns(3)
                mc1.metric("Loyer HC Actuel", f"{old_rent:.2f} €")
                pct_chg = (new_val - old_val) / old_val * 100
                mc2.metric(
                    "Nouveau Loyer Révisé",
                    f"{revised_rent:.2f} €",
                    delta=f"+{diff:.2f} € / mois (+{pct_chg:.2f}%)",
                )
                chg_prov = float(target_t.get("charges_provision", 0))
                mc3.metric(
                    "Nouveau Total CC",
                    f"{revised_rent + chg_prov:.2f} €",
                )

                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    if st.button(
                        "✅ Valider et appliquer le nouveau loyer au bail",
                        type="primary",
                        key="apply_irl_btn",
                    ):
                        execute_write(
                            """
                            UPDATE tenants 
                            SET rent_amount = ?, irl_reference_quarter = ?,
                                irl_reference_value = ?, last_revision_date = ?
                            WHERE id = ?;
                        """,
                            [
                                revised_rent,
                                new_q,
                                new_val,
                                eff_date,
                                target_t["id"],
                            ],
                        )
                        st.success(
                            f"Le loyer de {target_t['first_name']} "
                            f"{target_t['last_name']} mis à jour à "
                            f"{revised_rent:.2f} € !"
                        )
                        st.rerun()

                # Lettre de révision
                p_inf = {
                    "address": target_t["prop_address"],
                    "city": target_t["prop_city"],
                    "postal_code": target_t["prop_postal"],
                }
                html_irl = generate_irl_letter_html(
                    sci_info,
                    target_t,
                    p_inf,
                    old_rent,
                    revised_rent,
                    old_q,
                    old_val,
                    new_q,
                    new_val,
                    eff_date,
                )

                with col_btn2:
                    t_ln = target_t['last_name']
                    st.download_button(
                        "📄 Télécharger la lettre de notification IRL",
                        data=html_irl,
                        file_name=f"revision_loyer_{t_ln}_{new_q}.html",
                        key="dl_irl_doc",
                    )

                components.html(html_irl, height=520, scrolling=True)

    # 4. PV D'AGO ANNUELLE
    with tab_ago:
        st.markdown(
            "#### 🏛️ Procès-Verbal d'Assemblée Générale Ordinaire (PV d'AGO)"
        )
        st.caption(
            "Document juridique officiel obligatoire chaque année pour "
            "approuver les comptes de la SCI et affecter le résultat."
        )

        ago_year = st.selectbox(
            "Exercice comptable à approuver :",
            list(range(date.today().year - 3, date.today().year + 1)),
            index=len(range(date.today().year - 3, date.today().year + 1)) - 1,
            key="ago_yr",
        )

        from utils.tax_calculator import compute_income_statement

        inc = compute_income_statement(ago_year)
        gross_inc = inc["gross_rental_income"]
        op_exp = inc["total_operating_charges"]
        daa = inc["total_daa"]
        fin_exp = inc["total_financial_charges"]
        rcai = inc["rcai"]
        is_tax = inc["is_tax"]
        net_res = inc["net_accounting_result"]

        html_ago = generate_pv_ago_html(
            sci_info,
            ago_year,
            gross_inc,
            op_exp,
            daa,
            fin_exp,
            rcai,
            is_tax,
            net_res,
        )

        sci_tag = sci_info.get("name", "SCI")
        st.download_button(
            label="💾 Télécharger le PV d'AGO complet (HTML/PDF)",
            data=html_ago,
            file_name=f"PV_AGO_SCI_{sci_tag}_{ago_year}.html",
            mime="text/html",
            key="dl_pv_ago",
        )

        components.html(html_ago, height=600, scrolling=True)
