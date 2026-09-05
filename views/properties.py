"""
Vue Gestion du Patrimoine Immobilier - Biens, Appartements et Lots (Adaptée SCI à l'IS).
"""
import streamlit as st
import pandas as pd
from database import query_df, query_rows, query_one, execute_write

def render_properties():
    st.markdown("## 🏢 Gestion du Patrimoine Immobilier (SCI à l'IS)")
    st.caption("Consultez vos lots, gérez les paramètres d'amortissement comptable (bâti et meubles) et suivez l'occupation.")

    tab_list, tab_add, tab_edit = st.tabs(["📋 Liste des Biens & Amortissements", "➕ Ajouter un Bien", "✏️ Modifier / Supprimer"])

    # 1. LISTE DES BIENS
    with tab_list:
        properties = query_rows("""
            SELECT p.*, 
                   t.first_name || ' ' || t.last_name as current_tenant,
                   t.rent_amount as current_rent,
                   t.charges_provision as current_charges
            FROM properties p
            LEFT JOIN tenants t ON p.id = t.property_id AND t.is_active = 1
            ORDER BY p.id ASC;
        """)

        if not properties:
            st.info("Aucun bien n'a encore été enregistré. Cliquez sur l'onglet **'➕ Ajouter un Bien'** pour créer votre premier lot.")
        else:
            # Filtres rapides
            col_f1, col_f2 = st.columns([2, 1])
            with col_f1:
                search_text = st.text_input("🔍 Rechercher par nom, ville ou adresse...", "").lower()
            with col_f2:
                status_filter = st.selectbox("Statut d'occupation", ["Tous", "loue", "vacant", "en_travaux"], 
                                             format_func=lambda x: {"Tous": "Tous les statuts", "loue": "🟢 Loué", "vacant": "🔴 Vacant", "en_travaux": "🟠 En travaux"}.get(x, x))

            filtered = []
            for p in properties:
                if status_filter != "Tous" and p.get("status") != status_filter:
                    continue
                full_text = f"{p.get('name', '')} {p.get('city', '')} {p.get('address', '')}".lower()
                if search_text and search_text not in full_text:
                    continue
                filtered.append(p)

            st.write(f"Affichage de **{len(filtered)}** bien(s) :")

            for prop in filtered:
                status = prop.get("status", "vacant")
                status_badge = {
                    "loue": "🟢 **Loué**",
                    "vacant": "🔴 **Vacant**",
                    "en_travaux": "🟠 **En travaux**"
                }.get(status, status)

                # Calculs d'amortissement IS
                acq_price = float(prop.get("acquisition_price", 0.0))
                notary = float(prop.get("notary_fees", 0.0))
                total_cost = acq_price + notary
                land_pct = float(prop.get("land_share_pct", 15.0))
                amort_years = max(1, int(prop.get("amortization_years", 25)))
                
                # Part terrain (non amortissable)
                land_value = acq_price * (land_pct / 100.0)
                # Bâti amortissable (prix hors terrain + frais d'acquisition)
                building_amort_base = total_cost - land_value
                annual_building_amort = building_amort_base / amort_years

                # Meubles
                furn_val = float(prop.get("furniture_value", 0.0))
                furn_years = max(1, int(prop.get("furniture_years", 5)))
                annual_furn_amort = furn_val / furn_years if furn_val > 0 else 0.0
                total_annual_amort = annual_building_amort + annual_furn_amort

                with st.container():
                    st.markdown(f"### {prop.get('name', 'Sans titre')} &nbsp; {status_badge}")
                    c1, c2, c3, c4 = st.columns(4)
                    with c1:
                        st.markdown(f"**Type :** {prop.get('type', 'Appartement')}")
                        st.markdown(f"**Adresse :** {prop.get('address', '')}, {prop.get('postal_code', '')} {prop.get('city', '')}")
                        if prop.get("current_tenant"):
                            st.markdown(f"**Locataire :** {prop.get('current_tenant')}")
                            st.markdown(f"**Loyer :** {prop.get('current_rent', 0):.2f} € + {prop.get('current_charges', 0):.2f} € ch.")
                        else:
                            st.markdown(f"**Loyer cible :** {prop.get('target_rent', 0):.2f} € HC")
                    with c2:
                        door_str = f" - Porte {prop.get('door_number')}" if prop.get("door_number") else ""
                        st.markdown(f"**Surface :** {prop.get('surface', 0)} m² ({prop.get('rooms', 1)} pièces)")
                        st.markdown(f"**Étage :** {prop.get('floor', 0)}{door_str}")
                        st.markdown(f"**Tantièmes copro :** {prop.get('tantiemes', 1000)} / 1000")
                    with c3:
                        st.markdown(f"**Coût d'acquisition :** {acq_price:,.2f} €".replace(",", " "))
                        st.caption(f"Frais de notaire : {notary:,.2f} €")
                        st.markdown(f"**Terrain (non amorti) :** {land_value:,.2f} € ({land_pct:.0f}%)")
                        st.markdown(f"**Bâti amortissable :** {building_amort_base:,.2f} €")
                    with c4:
                        st.markdown(f"**Amortissement Immeuble :**")
                        st.markdown(f"**{annual_building_amort:,.2f} € / an** ({amort_years} ans)")
                        if furn_val > 0:
                            st.markdown(f"**Meubles :** +{annual_furn_amort:,.2f} € / an ({furn_years} ans)")
                        st.success(f"📉 **Déduction IS totale :** **{total_annual_amort:,.2f} € / an**")

                    if prop.get("notes"):
                        st.caption(f"📝 Notes : {prop.get('notes')}")
                    st.divider()

    # 2. AJOUTER UN BIEN
    with tab_add:
        st.markdown("#### Nouveau Bien / Lot Immobilier")
        with st.form("form_add_property", clear_on_submit=True):
            col_a1, col_a2 = st.columns(2)
            with col_a1:
                name = st.text_input("Désignation du bien *", placeholder="ex: Studio #101 - Résidence Meurthe")
                prop_type = st.selectbox("Type de bien", ["Appartement", "Studio", "Maison", "Parking / Garage", "Local Commercial", "Immeuble entier", "Cave"])
                address = st.text_input("Adresse *", placeholder="ex: 12 Rue de la République")
                city = st.text_input("Ville *", value="Nancy")
                postal_code = st.text_input("Code Postal *", value="54000")
            with col_a2:
                surface = st.number_input("Surface habitable (m²)", min_value=0.0, value=25.0, step=0.5)
                rooms = st.number_input("Nombre de pièces", min_value=1, value=1, step=1)
                floor = st.number_input("Étage", value=1, step=1)
                door_number = st.text_input("N° Porte / Lot copro", placeholder="ex: Porte 3, Lot 14")
                tantiemes = st.number_input("Tantièmes / millièmes de copropriété", min_value=0.0, value=100.0, step=1.0)

            st.markdown("##### 💶 Acquisition & Paramètres d'Amortissement (Fiscalité IS)")
            col_f1, col_f2, col_f3 = st.columns(3)
            with col_f1:
                acquisition_price = st.number_input("Prix d'achat net vendeur (€) *", min_value=0.0, value=60000.0, step=1000.0)
                notary_fees = st.number_input("Frais de notaire / agence (€)", min_value=0.0, value=4500.0, step=500.0)
                acquisition_date = st.date_input("Date d'achat").strftime("%Y-%m-%d")
            with col_f2:
                land_share_pct = st.number_input("Quote-part terrain non amortissable (%)", min_value=0.0, max_value=50.0, value=15.0, step=1.0, help="Le terrain n'est pas amortissable (généralement 15% à 20% en milieu urbain)")
                amortization_years = st.number_input("Durée d'amortissement de l'immeuble (ans)", min_value=10, max_value=50, value=25, step=1)
            with col_f3:
                furniture_value = st.number_input("Valeur du mobilier (€ si meublé)", min_value=0.0, value=0.0, step=500.0)
                furniture_years = st.number_input("Durée d'amortissement mobilier (ans)", min_value=3, max_value=10, value=5, step=1)

            st.markdown("##### 🎯 Objectifs Locatifs")
            col_l1, col_l2 = st.columns(2)
            with col_l1:
                target_rent = st.number_input("Loyer mensuel cible (€ HC)", min_value=0.0, value=450.0, step=10.0)
            with col_l2:
                target_charges = st.number_input("Charges mensuelles cibles (€)", min_value=0.0, value=50.0, step=5.0)

            notes = st.text_area("Notes particulières / équipements", placeholder="Cuisine équipée, double vitrage, cave privative...")

            submitted = st.form_submit_button("💾 Enregistrer le nouveau bien", type="primary")
            if submitted:
                if not name.strip() or not address.strip():
                    st.error("Le nom du bien et l'adresse sont obligatoires.")
                else:
                    try:
                        execute_write("""
                            INSERT INTO properties (name, type, address, city, postal_code, surface, rooms, floor, door_number, tantiemes, acquisition_date, acquisition_price, notary_fees, land_share_pct, amortization_years, furniture_value, furniture_years, target_rent, target_charges, status, notes)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'vacant', ?);
                        """, [name, prop_type, address, city, postal_code, surface, rooms, floor, door_number, tantiemes, str(acquisition_date), acquisition_price, notary_fees, land_share_pct, amortization_years, furniture_value, furniture_years, target_rent, target_charges, notes])
                        st.success(f"Le bien **'{name}'** a été ajouté avec succès !")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erreur lors de l'enregistrement : {e}")

    # 3. MODIFIER / SUPPRIMER
    with tab_edit:
        all_props = query_rows("SELECT id, name FROM properties ORDER BY name ASC;")
        if not all_props:
            st.info("Aucun bien disponible à modifier.")
        else:
            prop_choices = {p["id"]: f"#{p['id']} - {p['name']}" for p in all_props}
            selected_id = st.selectbox("Sélectionnez le bien à modifier :", options=list(prop_choices.keys()), format_func=lambda x: prop_choices[x])

            prop_data = query_one("SELECT * FROM properties WHERE id = ?;", [selected_id])
            if prop_data:
                with st.form("form_edit_property"):
                    col_m1, col_m2 = st.columns(2)
                    with col_m1:
                        new_name = st.text_input("Nom du bien", value=prop_data.get("name", ""))
                        new_type = st.selectbox("Type", ["Appartement", "Studio", "Maison", "Parking / Garage", "Local Commercial", "Immeuble entier", "Cave"], 
                                                index=["Appartement", "Studio", "Maison", "Parking / Garage", "Local Commercial", "Immeuble entier", "Cave"].index(prop_data.get("type", "Appartement")) if prop_data.get("type") in ["Appartement", "Studio", "Maison", "Parking / Garage", "Local Commercial", "Immeuble entier", "Cave"] else 0)
                        new_address = st.text_input("Adresse", value=prop_data.get("address", ""))
                        new_city = st.text_input("Ville", value=prop_data.get("city", ""))
                        new_postal_code = st.text_input("Code Postal", value=prop_data.get("postal_code", ""))
                        new_status = st.selectbox("Statut", ["vacant", "loue", "en_travaux"], index=["vacant", "loue", "en_travaux"].index(prop_data.get("status", "vacant")))
                    with col_m2:
                        new_surface = st.number_input("Surface (m²)", value=float(prop_data.get("surface", 0.0)))
                        new_rooms = st.number_input("Pièces", value=int(prop_data.get("rooms", 1)))
                        new_floor = st.number_input("Étage", value=int(prop_data.get("floor", 0)))
                        new_door = st.text_input("N° Porte", value=prop_data.get("door_number", ""))
                        new_tantiemes = st.number_input("Tantièmes", value=float(prop_data.get("tantiemes", 1000.0)))
                        new_rent = st.number_input("Loyer cible (€)", value=float(prop_data.get("target_rent", 0.0)))
                        new_charges = st.number_input("Charges cibles (€)", value=float(prop_data.get("target_charges", 0.0)))

                    st.markdown("##### Paramètres Fiscaux IS")
                    col_is1, col_is2, col_is3 = st.columns(3)
                    with col_is1:
                        new_price = st.number_input("Prix achat (€)", value=float(prop_data.get("acquisition_price", 0.0)))
                        new_notary = st.number_input("Frais notaire (€)", value=float(prop_data.get("notary_fees", 0.0)))
                    with col_is2:
                        new_land_pct = st.number_input("Part terrain (%)", value=float(prop_data.get("land_share_pct", 15.0)))
                        new_amort_yrs = st.number_input("Amortissement bâti (ans)", value=int(prop_data.get("amortization_years", 25)))
                    with col_is3:
                        new_furn_val = st.number_input("Mobilier (€)", value=float(prop_data.get("furniture_value", 0.0)))
                        new_furn_yrs = st.number_input("Amortissement mobilier (ans)", value=int(prop_data.get("furniture_years", 5)))

                    new_notes = st.text_area("Notes", value=prop_data.get("notes", ""))

                    save_btn = st.form_submit_button("💾 Mettre à jour les informations", type="primary")
                    if save_btn:
                        execute_write("""
                            UPDATE properties 
                            SET name=?, type=?, address=?, city=?, postal_code=?, surface=?, rooms=?, floor=?, door_number=?, tantiemes=?, acquisition_price=?, notary_fees=?, land_share_pct=?, amortization_years=?, furniture_value=?, furniture_years=?, target_rent=?, target_charges=?, status=?, notes=?
                            WHERE id=?;
                        """, [new_name, new_type, new_address, new_city, new_postal_code, new_surface, new_rooms, new_floor, new_door, new_tantiemes, new_price, new_notary, new_land_pct, new_amort_yrs, new_furn_val, new_furn_yrs, new_rent, new_charges, new_status, new_notes, selected_id])
                        st.success("Modifications enregistrées !")
                        st.rerun()

                st.markdown("---")
                st.markdown("#### 🗑️ Zone de danger")
                if st.button(f"Supprimer définitivement le bien #{selected_id} ({prop_data.get('name')})", type="secondary"):
                    active_tenant = query_one("SELECT id, first_name, last_name FROM tenants WHERE property_id = ? AND is_active = 1;", [selected_id])
                    if active_tenant:
                        st.error(f"Impossible de supprimer ce bien : le locataire {active_tenant['first_name']} {active_tenant['last_name']} est actuellement rattaché à ce lot. Clôturez d'abord le bail.")
                    else:
                        execute_write("DELETE FROM properties WHERE id = ?;", [selected_id])
                        st.warning("Bien supprimé avec succès.")
                        st.rerun()
