"""
Point d'entrée principal de l'application Streamlit de Gestion Immobilière SCI.
"""
import streamlit as st
from database import init_db, query_one, get_connection_info
from views.dashboard import render_dashboard
from views.properties import render_properties
from views.tenants import render_tenants
from views.rents import render_rents
from views.sci_expenses import render_sci_expenses
from views.property_expenses import render_property_expenses
from views.tax_report import render_tax_report
from views.settings import render_settings

# Configuration de la page Streamlit
st.set_page_config(
    page_title="Gestion Immobilière SCI",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Injection CSS pour une interface moderne et élégante
st.markdown("""
<style>
    /* Polices et typographie */
    html, body, [class*="css"] {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    
    /* Cartes de métriques Streamlit */
    div[data-testid="stMetric"] {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        padding: 16px 20px;
        border-radius: 10px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
        transition: transform 0.15s ease, box-shadow 0.15s ease;
    }
    div[data-testid="stMetric"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
    }
    
    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #f8fafc;
        border-right: 1px solid #e2e8f0;
    }
    
    /* Boutons personnalisés */
    .stButton > button {
        border-radius: 8px;
        font-weight: 500;
        transition: all 0.2s ease;
    }
    
    /* Titres */
    h1, h2, h3 {
        color: #0f172a;
        font-weight: 700;
    }
    
    /* Badges personnalisés */
    .badge {
        display: inline-block;
        padding: 4px 10px;
        font-size: 12px;
        font-weight: 600;
        border-radius: 9999px;
    }
    .badge-turso {
        background-color: #ecfdf5;
        color: #059669;
        border: 1px solid #a7f3d0;
    }
    .badge-local {
        background-color: #fffbeb;
        color: #d97706;
        border: 1px solid #fde68a;
    }
</style>
""", unsafe_allow_html=True)

# Initialisation automatique de la base de données au démarrage
if "db_initialized" not in st.session_state:
    try:
        init_db()
        st.session_state["db_initialized"] = True
    except Exception as e:
        st.sidebar.error(f"Erreur initialisation DB : {e}")

# Récupération des informations de la SCI
sci_info = {}
try:
    sci_info = query_one("SELECT name, city FROM sci_info WHERE id = 1;") or {}
except Exception:
    pass

sci_name = sci_info.get("name", "Ma SCI Immobilière")

# Barre latérale (Sidebar)
with st.sidebar:
    st.markdown(f"### 🏢 {sci_name}")
    
    conn_info = get_connection_info()
    if conn_info["is_turso"]:
        st.markdown('<span class="badge badge-turso">☁️ Turso Cloud Connecté</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span class="badge badge-local">💾 Mode Local SQLite</span>', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("**Navigation**")
    menu = st.radio(
        "Menu principal",
        [
            "📊 Tableau de Bord",
            "🏢 Biens & Patrimoine",
            "👥 Locataires & Baux",
            "💳 Loyers & Quittances",
            "🏛️ Charges de la SCI",
            "🏠 Charges des Lots & Réguls",
            "📑 Synthèse Fiscale (2072)",
            "⚙️ Paramètres & Configuration"
        ],
        label_visibility="collapsed"
    )

    st.markdown("---")
    st.caption("Application de Gestion SCI v1.0")
    st.caption("Développé avec Streamlit & Turso libSQL")

# Routage des vues
if menu == "📊 Tableau de Bord":
    render_dashboard()
elif menu == "🏢 Biens & Patrimoine":
    render_properties()
elif menu == "👥 Locataires & Baux":
    render_tenants()
elif menu == "💳 Loyers & Quittances":
    render_rents()
elif menu == "🏛️ Charges de la SCI":
    render_sci_expenses()
elif menu == "🏠 Charges des Lots & Réguls":
    render_property_expenses()
elif menu == "📑 Synthèse Fiscale (2072)":
    render_tax_report()
elif menu == "⚙️ Paramètres & Configuration":
    render_settings()
