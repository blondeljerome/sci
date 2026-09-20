"""
Vue Gestion des Locataires et des Baux :
- Consultation des locataires actifs et détails du bail
- Création d'un nouveau locataire / bail avec affectation de lot
- Édition et modification complète d'un locataire (coordonnées, bail, loyer, charges, IRL, réassignation de bien)
- Historique des anciens baux et réactivation
"""
import streamlit as st
import pandas as pd
from typing import Any, Optional, Tuple, List, Dict
from datetime import datetime, date
from database import query_rows, query_one, execute_write

def get_irl_indices_data() -> Tuple[List[str], Dict[str, float]]:
    """
    Récupère les trimestres et valeurs officielles directement depuis la table irl_indices,
    triés rigoureusement par année et trimestre décroissant (le plus récent en premier).
    """
    rows = query_rows("""
        SELECT quarter, value 
        FROM irl_indices 
        ORDER BY CAST(SUBSTR(quarter, 4, 4) AS INTEGER) DESC, CAST(SUBSTR(quarter, 2, 1) AS INTEGER) DESC;
    """)
    if not rows:
        return ["T2 2026", "T1 2026", "T4 2025"], {"T2 2026": 148.37, "T1 2026": 146.60, "T4 2025": 145.78}
    quarters = [r["quarter"] for r in rows]
    val_map = {r["quarter"]: float(r["value"]) for r in rows}
    return quarters, val_map

def parse_date(date_str: Any) -> Optional[date]:
    if not date_str:
        return None
    try:
        return datetime.strptime(str(date_str)[:10], "%Y-%m-%d").date()
    except Exception:
        return None

def sync_property_status(property_id: Optional[int]):
    """
    Met à jour le statut d'un bien en fonction de ses locataires actifs.
    """
    if not property_id:
        return
    active_count_row = query_one(
        "SELECT COUNT(*) as c FROM tenants WHERE property_id = ? AND is_active = 1;",
        [property_id]
    )
    active_count = active_count_row["c"] if active_count_row else 0
    new_status = "loue" if active_count > 0 else "vacant"
    execute_write("UPDATE properties SET status = ? WHERE id = ?;", [new_status, property_id])

def render_tenants():
    st.markdown("## 👥 Gestion des Locataires & Baux")
    st.caption("Suivez les locataires en place, modifiez leurs informations contractuelles, ajoutez de nouveaux baux et gérez l'historique.")

    tab_active, tab_add, tab_edit, tab_history = st.tabs([
        "🟢 Locataires Actuels",
        "➕ Nouveau Locataire / Bail",
        "✏️ Modifier un Locataire",
        "📜 Historique & Anciens Baux"
    ])

    # =========================================================================
    # 1. LOCATAIRES ACTUELS
    # =========================================================================
    with tab_active:
        active_tenants = query_rows("""
            SELECT t.*, p.name as property_name, p.address as prop_address, p.city as prop_city
            FROM tenants t
            LEFT JOIN properties p ON t.property_id = p.id
            WHERE t.is_active = 1
            ORDER BY t.last_name ASC;
        """)

        if not active_tenants:
            st.info("Aucun locataire actif pour le moment. Utilisez l'onglet **'➕ Nouveau Locataire / Bail'** pour enregistrer votre premier locataire.")
        else:
            for t in active_tenants:
                rent = float(t.get("rent_amount", 0.0) or 0.0)
                charges = float(t.get("charges_provision", 0.0) or 0.0)
                total = rent + charges
                
                with st.expander(f"👤 {t.get('first_name')} {t.get('last_name', '').upper()} — {t.get('property_name', 'Sans bien')} ({total:.2f} €/mois CC)", expanded=True):
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        st.markdown(f"**Bien occupé :** {t.get('property_name') or 'Non assigné'}")
                        if t.get("prop_address"):
                            st.markdown(f"**Adresse :** {t.get('prop_address', '')}, {t.get('prop_city', '')}")
                        st.markdown(f"**Début de bail :** `{t.get('lease_start')}`")
                        if t.get("lease_end"):
                            st.markdown(f"**Fin prévue :** `{t.get('lease_end')}`")
                    with c2:
                        st.markdown(f"**Loyer HC :** `{rent:,.2f} €`")
                        st.markdown(f"**Provision charges :** `{charges:,.2f} €`")
                        st.markdown(f"**Total mensuel dû :** **`{total:,.2f} € CC`**")
                        st.markdown(f"**Dépôt de garantie :** `{float(t.get('deposit_amount', 0.0) or 0.0):,.2f} €`")
                    with c3:
                        st.markdown(f"**Email :** {t.get('email') or 'Non renseigné'}")
                        st.markdown(f"**Téléphone :** {t.get('phone') or 'Non renseigné'}")
                        st.markdown(f"**Garant / Caution :** {t.get('guarantor_info') or 'Aucun'}")

                    if t.get("irl_reference_quarter"):
                        rev_str = f" • Dernière révision : {t.get('last_revision_date')}" if t.get('last_revision_date') else ""
                        st.caption(f"📈 Référence IRL : **{t.get('irl_reference_quarter')}** ({float(t.get('irl_reference_value', 144.51) or 144.51):.2f}){rev_str}")
                    if t.get("notes"):
                        st.caption(f"📝 Notes : {t.get('notes')}")

                    st.markdown("---")
                    col_act1, col_act2 = st.columns([1, 1])

                    # Bouton raccourci de modification
                    with col_act1:
                        if st.button(f"✏️ Modifier les informations de {t.get('first_name')}", key=f"btn_quick_edit_{t['id']}", use_container_width=True):
                            st.session_state["edit_tenant_id"] = t["id"]
                            st.info("Basculez sur l'onglet **'✏️ Modifier un Locataire'** pour éditer ce dossier.")

                    # Action clôture de bail (départ)
                    with col_act2:
                        with st.popover(f"🚪 Clôturer le bail (Départ de {t.get('first_name')})", use_container_width=True):
                            st.markdown(f"**Confirmer le départ de {t.get('first_name')} {t.get('last_name')}**")
                            dep_date = st.date_input("Date effective de fin de bail", value=date.today(), key=f"dep_date_{t['id']}")
                            if st.button("Confirmer le départ et libérer le logement", type="primary", key=f"btn_confirm_dep_{t['id']}"):
                                execute_write("""
                                    UPDATE tenants SET is_active = 0, lease_end = ? WHERE id = ?;
                                """, [str(dep_date), t["id"]])
                                if t.get("property_id"):
                                    sync_property_status(t["property_id"])
                                st.success(f"Le bail de {t.get('first_name')} a été clôturé et archivé.")
                                st.rerun()

    # =========================================================================
    # 2. NOUVEAU LOCATAIRE / NOUVEAU BAIL
    # =========================================================================
    with tab_add:
        available_props = query_rows("SELECT id, name, target_rent, target_charges, city FROM properties WHERE status != 'loue' ORDER BY name ASC;")
        
        c_head1, c_head2 = st.columns([3, 1])
        with c_head1:
            st.markdown("#### Création d'un Nouveau Contrat de Location")
        with c_head2:
            from utils.irl import sync_irl_indices_to_db
            if st.button("🔄 Actualiser les IRL en ligne", key="btn_sync_irl_tab_add", help="Télécharge automatiquement les derniers indices parus sur Service-Public et ANIL"):
                with st.spinner("Récupération des derniers indices en ligne..."):
                    sync_res = sync_irl_indices_to_db()
                    if sync_res["success"]:
                        st.success(f"✅ {sync_res['count']} indices synchronisés ! Dernier : {sync_res['latest_quarter']} ({sync_res['latest_value']})")
                        st.rerun()
                    else:
                        st.error(sync_res["message"])

        with st.form("form_add_tenant", clear_on_submit=True):
            st.markdown("#### Coordonnées du Locataire")
            c_t1, c_t2 = st.columns(2)
            with c_t1:
                first_name = st.text_input("Prénom *", placeholder="ex: Jean")
                email = st.text_input("Adresse Email", placeholder="ex: jean.dupont@email.com")
            with c_t2:
                last_name = st.text_input("Nom de famille *", placeholder="ex: Dupont")
                phone = st.text_input("Téléphone", placeholder="ex: 06 12 34 56 78")

            st.markdown("#### Affectation du Logement & Conditions du Bail")
            prop_options = {p["id"]: f"{p['name']} ({p['city']}) - Cible: {p['target_rent']:.0f}€ + {p['target_charges']:.0f}€" for p in available_props}
            prop_options[None] = "Aucun bien pour l'instant (locataire en attente)"

            selected_prop = st.selectbox("Sélectionnez le bien à louer :", options=list(prop_options.keys()), format_func=lambda x: prop_options[x])

            default_rent = 450.0
            default_charges = 50.0
            if selected_prop:
                p_selected = next((p for p in available_props if p["id"] == selected_prop), None)
                if p_selected:
                    default_rent = float(p_selected.get("target_rent", 450.0) or 450.0)
                    default_charges = float(p_selected.get("target_charges", 50.0) or 50.0)

            c_f1, c_f2, c_f3 = st.columns(3)
            with c_f1:
                rent_amount = st.number_input("Loyer mensuel HC (€) *", min_value=0.0, value=default_rent, step=10.0)
                lease_start = st.date_input("Date de prise d'effet du bail *", value=date.today()).strftime("%Y-%m-%d")
            with c_f2:
                charges_provision = st.number_input("Provision sur charges mensuelle (€)", min_value=0.0, value=default_charges, step=5.0)
                deposit_amount = st.number_input("Dépôt de garantie encaissé (€)", min_value=0.0, value=default_rent, step=50.0)
            with c_f3:
                guarantor_info = st.text_input("Garant / Caution solidaire", placeholder="Nom, lien, téléphone...")

            st.markdown("##### 📈 Indexation Annuelle (Clause IRL du Bail)")
            irl_quarters, irl_val_map = get_irl_indices_data()
            st.caption(f"📋 *Indices officiels chargés depuis la table irl_indices (Derniers publiés : {', '.join(irl_quarters[:3])})*")
            ci1, ci2 = st.columns(2)
            with ci1:
                irl_q = st.selectbox(
                    "Indice IRL de référence du contrat *",
                    options=irl_quarters,
                    format_func=lambda q: f"{q} — {irl_val_map.get(q, 0.0):.2f} (INSEE)",
                    index=0,
                    help="Sélectionné directement depuis la table officielle des indices IRL"
                )
            with ci2:
                default_irl_v = irl_val_map.get(irl_q, 144.51)
                irl_v = st.number_input(
                    "Valeur de l'indice de référence retenue",
                    min_value=100.0,
                    max_value=200.0,
                    value=default_irl_v,
                    step=0.01,
                    help="Valeur officielle enregistrée dans la table irl_indices"
                )

            notes = st.text_area("Observations / Inventaire / État des lieux d'entrée", placeholder="Remise des clés, numéro de cave, badge...")

            submitted = st.form_submit_button("✅ Enregistrer le Locataire et Activer le Bail", type="primary")
            if submitted:
                if not first_name.strip() or not last_name.strip():
                    st.error("Le prénom et le nom sont obligatoires.")
                else:
                    try:
                        # Si l'utilisateur n'a pas modifié manuellement la valeur, s'assurer qu'elle correspond au trimestre sélectionné
                        final_irl_val = irl_val_map.get(irl_q, irl_v) if irl_v == default_irl_v else irl_v
                        tenant_id = execute_write("""
                            INSERT INTO tenants (property_id, first_name, last_name, email, phone, lease_start, rent_amount, charges_provision, deposit_amount, is_active, guarantor_info, irl_reference_quarter, irl_reference_value, notes)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?);
                        """, [selected_prop, first_name.strip(), last_name.strip(), email.strip(), phone.strip(), lease_start, rent_amount, charges_provision, deposit_amount, guarantor_info.strip(), irl_q, final_irl_val, notes.strip()])

                        if selected_prop:
                            sync_property_status(selected_prop)

                        st.success(f"Le locataire **{first_name} {last_name}** a été enregistré avec succès et rattaché au bien !")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erreur : {e}")

    # =========================================================================
    # 3. MODIFIER UN LOCATAIRE / EDITION COMPLETE
    # =========================================================================
    with tab_edit:
        st.markdown("### ✏️ Édition & Modification d'un Locataire")
        st.caption("Modifiez l'état civil, le bien rattaché, les montants de loyer et charges, les clauses d'indexation ou le statut du bail.")

        all_tenants = query_rows("""
            SELECT t.id, t.first_name, t.last_name, t.is_active, p.name as property_name
            FROM tenants t
            LEFT JOIN properties p ON t.property_id = p.id
            ORDER BY t.is_active DESC, t.last_name ASC;
        """)

        if not all_tenants:
            st.info("Aucun locataire enregistré pour le moment.")
        else:
            tenant_choices = {
                t["id"]: f"{'🟢 [ACTIF]' if t['is_active'] else '⚪ [ARCHIVÉ]'} {t['first_name']} {t['last_name'].upper()} ({t.get('property_name') or 'Sans bien'})"
                for t in all_tenants
            }

            # Si un locataire a été sélectionné via un raccourci
            preselected_id = st.session_state.get("edit_tenant_id")
            default_t_idx = 0
            if preselected_id and preselected_id in tenant_choices:
                default_t_idx = list(tenant_choices.keys()).index(preselected_id)

            c_edit_h1, c_edit_h2 = st.columns([3, 1])
            with c_edit_h1:
                selected_id = st.selectbox(
                    "Sélectionnez le locataire à modifier :",
                    options=list(tenant_choices.keys()),
                    format_func=lambda x: tenant_choices[x],
                    index=default_t_idx,
                    key="sel_tenant_to_edit"
                )
            with c_edit_h2:
                st.write("")
                st.write("")
                from utils.irl import sync_irl_indices_to_db
                if st.button("🔄 Actualiser les IRL", key="btn_sync_irl_tab_edit", help="Actualise la table des indices IRL en ligne"):
                    with st.spinner("Actualisation..."):
                        sync_res = sync_irl_indices_to_db()
                        if sync_res["success"]:
                            st.success(f"Dernier : {sync_res['latest_quarter']}")
                            st.rerun()

            t_data = query_one("SELECT * FROM tenants WHERE id = ?;", [selected_id])
            if t_data:
                # Récupérer tous les biens pour la réassignation
                all_properties = query_rows("SELECT id, name, city, status, target_rent, target_charges FROM properties ORDER BY name ASC;")
                prop_map = {p["id"]: f"{p['name']} ({p['city']}) [{p['status']}]" for p in all_properties}
                prop_map[None] = "Aucun bien (Locataire non rattaché)"

                current_prop_id = t_data.get("property_id")
                prop_keys = list(prop_map.keys())
                prop_index = prop_keys.index(current_prop_id) if current_prop_id in prop_keys else prop_keys.index(None)

                # Parsing sécurisé des dates existantes
                d_lease_start = parse_date(t_data.get("lease_start")) or date.today()
                d_lease_end = parse_date(t_data.get("lease_end"))
                d_last_rev = parse_date(t_data.get("last_revision_date"))

                with st.form(f"form_edit_tenant_{selected_id}"):
                    st.markdown("#### 1. Coordonnées & État Civil")
                    col_c1, col_c2 = st.columns(2)
                    with col_c1:
                        new_first_name = st.text_input("Prénom *", value=t_data.get("first_name", ""))
                        new_email = st.text_input("Adresse Email", value=t_data.get("email", ""))
                        new_guarantor = st.text_input("Garant / Caution solidaire", value=t_data.get("guarantor_info", ""), placeholder="Nom, coordonnées, lien...")
                    with col_c2:
                        new_last_name = st.text_input("Nom de famille *", value=t_data.get("last_name", ""))
                        new_phone = st.text_input("Téléphone", value=t_data.get("phone", ""))
                        new_is_active = st.selectbox(
                            "Statut du locataire",
                            options=[1, 0],
                            format_func=lambda x: "🟢 Locataire actuel (Bail en cours / Actif)" if x == 1 else "⚪ Ancien locataire (Bail terminé / Archivé)",
                            index=0 if t_data.get("is_active", 1) == 1 else 1
                        )

                    st.markdown("#### 2. Logement & Période du Bail")
                    col_b1, col_b2 = st.columns(2)
                    with col_b1:
                        new_property_id = st.selectbox(
                            "Logement / Bien attribué :",
                            options=prop_keys,
                            format_func=lambda x: prop_map[x],
                            index=prop_index
                        )
                        new_lease_start = st.date_input("Date de prise d'effet du bail *", value=d_lease_start)
                    with col_b2:
                        has_end_date = st.checkbox("Définir une date de fin de bail", value=bool(d_lease_end))
                        new_lease_end = st.date_input(
                            "Date de fin de bail",
                            value=d_lease_end if d_lease_end else date.today(),
                            disabled=not has_end_date
                        ) if has_end_date else None

                    st.markdown("#### 3. Conditions Financières & Dépôt de Garantie")
                    col_f1, col_f2, col_f3 = st.columns(3)
                    with col_f1:
                        new_rent = st.number_input("Loyer mensuel HC (€) *", min_value=0.0, value=float(t_data.get("rent_amount", 0.0) or 0.0), step=10.0)
                    with col_f2:
                        new_charges = st.number_input("Provision sur charges mensuelle (€)", min_value=0.0, value=float(t_data.get("charges_provision", 0.0) or 0.0), step=5.0)
                    with col_f3:
                        new_deposit = st.number_input("Dépôt de garantie encaissé (€)", min_value=0.0, value=float(t_data.get("deposit_amount", 0.0) or 0.0), step=50.0)

                    st.markdown("#### 4. Clause d'Indexation Annuelle (IRL)")
                    irl_quarters, irl_val_map = get_irl_indices_data()
                    st.caption(f"📋 *Indices officiels chargés depuis la table irl_indices (Derniers publiés : {', '.join(irl_quarters[:3])})*")
                    cur_irl_q = t_data.get("irl_reference_quarter") or (irl_quarters[0] if irl_quarters else "T3 2024")
                    all_irl_choices = list(irl_quarters)
                    if cur_irl_q not in all_irl_choices:
                        all_irl_choices.insert(0, cur_irl_q)
                        irl_val_map[cur_irl_q] = float(t_data.get("irl_reference_value", 144.51) or 144.51)

                    irl_idx = all_irl_choices.index(cur_irl_q) if cur_irl_q in all_irl_choices else 0

                    col_i1, col_i2, col_i3 = st.columns(3)
                    with col_i1:
                        new_irl_q = st.selectbox(
                            "Indice IRL de référence du contrat *",
                            options=all_irl_choices,
                            format_func=lambda q: f"{q} — {irl_val_map.get(q, 0.0):.2f} (INSEE)",
                            index=irl_idx,
                            help="Issu directement de la table des indices IRL enregistrés en base"
                        )
                    with col_i2:
                        cur_saved_v = float(t_data.get("irl_reference_value", 0.0) or 0.0)
                        default_edit_v = cur_saved_v if cur_saved_v > 0 else irl_val_map.get(new_irl_q, 144.51)
                        new_irl_v = st.number_input(
                            "Valeur de l'indice de référence",
                            min_value=100.0,
                            max_value=200.0,
                            value=default_edit_v,
                            step=0.01,
                            help="Valeur officielle enregistrée dans la table irl_indices"
                        )
                    with col_i3:
                        has_last_rev = st.checkbox("Dernière révision appliquée", value=bool(d_last_rev))
                        new_last_rev = st.date_input(
                            "Date de dernière révision",
                            value=d_last_rev if d_last_rev else date.today(),
                            disabled=not has_last_rev
                        ) if has_last_rev else None

                    st.markdown("#### 5. Observations & Notes")
                    new_notes = st.text_area("Notes internes", value=t_data.get("notes", "") or "", placeholder="Historique, particularités, état des lieux...")

                    btn_save = st.form_submit_button("💾 Enregistrer les modifications", type="primary", use_container_width=True)
                    if btn_save:
                        if not new_first_name.strip() or not new_last_name.strip():
                            st.error("Le prénom et le nom sont obligatoires.")
                        else:
                            try:
                                final_edit_irl_val = irl_val_map.get(new_irl_q, new_irl_v) if (new_irl_q != cur_irl_q and new_irl_v == default_edit_v) else new_irl_v
                                # Mise à jour du locataire
                                execute_write("""
                                    UPDATE tenants
                                    SET first_name=?, last_name=?, email=?, phone=?, guarantor_info=?,
                                        property_id=?, is_active=?, lease_start=?, lease_end=?,
                                        rent_amount=?, charges_provision=?, deposit_amount=?,
                                        irl_reference_quarter=?, irl_reference_value=?, last_revision_date=?,
                                        notes=?
                                    WHERE id = ?;
                                """, [
                                    new_first_name.strip(),
                                    new_last_name.strip(),
                                    new_email.strip(),
                                    new_phone.strip(),
                                    new_guarantor.strip(),
                                    new_property_id,
                                    new_is_active,
                                    str(new_lease_start),
                                    str(new_lease_end) if new_lease_end else None,
                                    new_rent,
                                    new_charges,
                                    new_deposit,
                                    new_irl_q,
                                    final_edit_irl_val,
                                    str(new_last_rev) if new_last_rev else None,
                                    new_notes.strip(),
                                    selected_id
                                ])

                                # Synchronisation des statuts de lots si réassignation
                                if current_prop_id != new_property_id:
                                    sync_property_status(current_prop_id)
                                    sync_property_status(new_property_id)
                                else:
                                    sync_property_status(new_property_id)

                                st.success(f"Les modifications pour **{new_first_name} {new_last_name}** ont été enregistrées avec succès !")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erreur lors de l'enregistrement : {e}")

                # Zone de danger : Suppression sécurisée
                st.markdown("---")
                st.markdown("#### 🗑️ Zone de Danger — Suppression du Locataire")
                linked_rents = query_rows("SELECT COUNT(*) as c FROM rent_payments WHERE tenant_id = ?;", [selected_id])
                rents_count = linked_rents[0]["c"] if linked_rents else 0

                if rents_count > 0:
                    st.warning(f"⚠️ Ce locataire possède **{rents_count} quittance(s) ou échéance(s) de loyer liée(s)** dans la base de données. Supprimer le locataire supprimera également ces paiements.")
                
                with st.expander("Supprimer définitivement la fiche de ce locataire"):
                    st.write(f"Êtes-vous sûr de vouloir supprimer définitivement **{t_data.get('first_name')} {t_data.get('last_name')}** ? Cette action est irréversible.")
                    confirm_del = st.checkbox(f"Oui, je confirme vouloir supprimer le dossier de {t_data.get('first_name')} {t_data.get('last_name')}", key=f"del_chk_{selected_id}")
                    if st.button("Confirmer la suppression définitive", type="secondary", disabled=not confirm_del, key=f"del_btn_{selected_id}"):
                        prop_to_sync = t_data.get("property_id")
                        execute_write("DELETE FROM tenants WHERE id = ?;", [selected_id])
                        if prop_to_sync:
                            sync_property_status(prop_to_sync)
                        st.session_state.pop("edit_tenant_id", None)
                        st.warning("Le locataire a été supprimé.")
                        st.rerun()

    # =========================================================================
    # 4. HISTORIQUE DES ANCIENS LOCATAIRES
    # =========================================================================
    with tab_history:
        past_tenants = query_rows("""
            SELECT t.*, p.name as property_name
            FROM tenants t
            LEFT JOIN properties p ON t.property_id = p.id
            WHERE t.is_active = 0
            ORDER BY t.lease_end DESC, t.last_name ASC;
        """)

        if not past_tenants:
            st.info("Aucun ancien bail archivé.")
        else:
            past_df = pd.DataFrame(past_tenants)
            display_past = past_df[["last_name", "first_name", "property_name", "lease_start", "lease_end", "rent_amount", "charges_provision", "deposit_amount"]].copy()
            display_past.columns = ["Nom", "Prénom", "Bien occupé", "Date Début", "Date Sortie", "Loyer HC (€)", "Charges (€)", "Dépôt de garantie (€)"]
            st.dataframe(display_past, use_container_width=True, hide_index=True)

            st.caption("💡 Pour réactiver un ancien locataire ou corriger ses informations, rendez-vous dans l'onglet **'✏️ Modifier un Locataire'**.")
