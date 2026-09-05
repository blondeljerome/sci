"""
Vue Gestion des Locataires et des Baux.
"""
import streamlit as st
import pandas as pd
from datetime import date
from database import query_rows, query_one, execute_write

def render_tenants():
    st.markdown("## 👥 Gestion des Locataires & Baux")
    st.caption("Suivez les locataires en place, les baux en cours, les loyers contractuels et les dépôts de garantie.")

    tab_active, tab_add, tab_history = st.tabs(["🟢 Locataires Actuels", "➕ Nouveau Locataire / Bail", "📜 Historique & Anciens Baux"])

    # 1. LOCATAIRES ACTUELS
    with tab_active:
        active_tenants = query_rows("""
            SELECT t.*, p.name as property_name, p.address as prop_address, p.city as prop_city
            FROM tenants t
            LEFT JOIN properties p ON t.property_id = p.id
            WHERE t.is_active = 1
            ORDER BY t.last_name ASC;
        """)

        if not active_tenants:
            st.info("Aucun locataire actif pour le moment. Utilisez l'onglet **'➕ Nouveau Locataire / Bail'** pour affecter un locataire à un bien.")
        else:
            for t in active_tenants:
                rent = float(t.get("rent_amount", 0.0))
                charges = float(t.get("charges_provision", 0.0))
                total = rent + charges
                
                with st.expander(f"👤 {t.get('first_name')} {t.get('last_name').upper()} — {t.get('property_name', 'Bien non assigné')} ({total:.2f} €/mois CC)", expanded=True):
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        st.markdown(f"**Bien occupé :** {t.get('property_name')}")
                        st.markdown(f"**Adresse :** {t.get('prop_address', '')}, {t.get('prop_city', '')}")
                        st.markdown(f"**Début de bail :** {t.get('lease_start')}")
                        if t.get("lease_end"):
                            st.markdown(f"**Fin prévue :** {t.get('lease_end')}")
                    with c2:
                        st.markdown(f"**Loyer HC :** {rent:.2f} €")
                        st.markdown(f"**Provision charges :** {charges:.2f} €")
                        st.markdown(f"**Total mensuel dû :** **{total:.2f} € CC**")
                        st.markdown(f"**Dépôt de garantie :** {float(t.get('deposit_amount', 0.0)):.2f} €")
                    with c3:
                        st.markdown(f"**Email :** {t.get('email') or 'Non renseigné'}")
                        st.markdown(f"**Téléphone :** {t.get('phone') or 'Non renseigné'}")
                        st.markdown(f"**Garant / Caution :** {t.get('guarantor_info') or 'Aucun'}")

                    if t.get("notes"):
                        st.caption(f"📝 Notes : {t.get('notes')}")

                    st.markdown("---")
                    st.markdown("##### Actions relatives au bail")
                    col_b1, col_b2 = st.columns([2, 1])
                    with col_b1:
                        departure_date = st.date_input(f"Date de fin / sortie pour {t.get('first_name')}", value=date.today(), key=f"dep_date_{t['id']}")
                    with col_b2:
                        st.write("")
                        st.write("")
                        if st.button("🚪 Clôturer le bail (Départ locataire)", key=f"btn_leave_{t['id']}", type="secondary"):
                            # Mettre is_active = 0, date de fin, et libérer le bien
                            execute_write("""
                                UPDATE tenants SET is_active = 0, lease_end = ? WHERE id = ?;
                            """, [str(departure_date), t["id"]])
                            if t.get("property_id"):
                                execute_write("UPDATE properties SET status = 'vacant' WHERE id = ?;", [t["property_id"]])
                            st.success(f"Le bail de {t.get('first_name')} {t.get('last_name')} a été clôturé et le bien est désormais vacant.")
                            st.rerun()

    # 2. NOUVEAU LOCATAIRE / NOUVEAU BAIL
    with tab_add:
        # Récupérer les biens disponibles (vacants ou en travaux)
        available_props = query_rows("SELECT id, name, target_rent, target_charges, city FROM properties WHERE status != 'loue' ORDER BY name ASC;")
        
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

            # Valeurs par défaut selon le bien sélectionné
            default_rent = 450.0
            default_charges = 50.0
            if selected_prop:
                p_selected = next((p for p in available_props if p["id"] == selected_prop), None)
                if p_selected:
                    default_rent = float(p_selected.get("target_rent", 450.0))
                    default_charges = float(p_selected.get("target_charges", 50.0))

            c_f1, c_f2, c_f3 = st.columns(3)
            with c_f1:
                rent_amount = st.number_input("Loyer mensuel HC (€) *", min_value=0.0, value=default_rent, step=10.0)
                lease_start = st.date_input("Date de prise d'effet du bail *", value=date.today()).strftime("%Y-%m-%d")
            with c_f2:
                charges_provision = st.number_input("Provision sur charges mensuelle (€)", min_value=0.0, value=default_charges, step=5.0)
                deposit_amount = st.number_input("Dépôt de garantie encaissé (€)", min_value=0.0, value=default_rent, step=50.0)
            with c_f3:
                guarantor_info = st.text_input("Garant / Caution solidaire", placeholder="Nom, lien, contact...")

            notes = st.text_area("Observations / Inventaire / État des lieux d'entrée", placeholder="Remise de 2 jeux de clés, badge d'accès...")

            submitted = st.form_submit_button("✅ Enregistrer le Locataire et Activer le Bail", type="primary")
            if submitted:
                if not first_name.strip() or not last_name.strip():
                    st.error("Le prénom et le nom sont obligatoires.")
                else:
                    try:
                        tenant_id = execute_write("""
                            INSERT INTO tenants (property_id, first_name, last_name, email, phone, lease_start, rent_amount, charges_provision, deposit_amount, is_active, guarantor_info, notes)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?);
                        """, [selected_prop, first_name.strip(), last_name.strip(), email.strip(), phone.strip(), lease_start, rent_amount, charges_provision, deposit_amount, guarantor_info, notes])

                        # Mettre le bien en statut "loue"
                        if selected_prop:
                            execute_write("UPDATE properties SET status = 'loue' WHERE id = ?;", [selected_prop])

                        st.success(f"Le locataire **{first_name} {last_name}** a été enregistré avec succès et rattaché au bien !")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erreur : {e}")

    # 3. HISTORIQUE DES ANCIENS LOCATAIRES
    with tab_history:
        past_tenants = query_rows("""
            SELECT t.*, p.name as property_name
            FROM tenants t
            LEFT JOIN properties p ON t.property_id = p.id
            WHERE t.is_active = 0
            ORDER BY t.lease_end DESC;
        """)

        if not past_tenants:
            st.info("Aucun ancien bail archivé.")
        else:
            past_df = pd.DataFrame(past_tenants)
            display_past = past_df[["last_name", "first_name", "property_name", "lease_start", "lease_end", "rent_amount", "charges_provision", "deposit_amount"]].copy()
            display_past.columns = ["Nom", "Prénom", "Bien occupé", "Date Début", "Date Sortie", "Loyer HC (€)", "Charges (€)", "Dépôt de garantie (€)"]
            st.dataframe(display_past, use_container_width=True, hide_index=True)
