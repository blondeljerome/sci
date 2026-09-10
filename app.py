"""
Point d'entrée principal de l'application Streamlit de Gestion Immobilière SCI à l'IS.
"""
import streamlit as st
from database import init_db, query_one, get_connection_info
from views.dashboard import render_dashboard
from views.properties import render_properties
from views.tenants import render_tenants
from views.rents import render_rents
from views.loans import render_loans
from views.sci_expenses import render_sci_expenses
from views.property_expenses import render_property_expenses
from views.partner_accounts import render_partner_accounts
from views.legal import render_legal
from views.documents import render_documents
from views.tax_report import render_tax_report
from views.settings import render_settings

# Configuration de la page Streamlit
st.set_page_config(
    page_title="Gestion Immobilière SCI à l'IS",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Injection CSS pour une interface moderne et soignée
st.markdown("""
<style>
    html, body, [class*="css"] {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    
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
    
    section[data-testid="stSidebar"] {
        background-color: #f8fafc;
        border-right: 1px solid #e2e8f0;
    }
    
    .stButton > button {
        border-radius: 8px;
        font-weight: 500;
        transition: all 0.2s ease;
    }
    
    h1, h2, h3 {
        color: #0f172a;
        font-weight: 700;
    }
    
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
    .badge-is {
        background-color: #eff6ff;
        color: #2563eb;
        border: 1px solid #bfdbfe;
        margin-top: 4px;
    }
</style>
""", unsafe_allow_html=True)

# Initialisation automatique de la base de données au démarrage
if "db_initialized" not in st.session_state:
    try:
        init_db()
        st.session_state["db_initialized"] = True
    except Exception as e:
        st.error(f"Erreur initialisation DB : {e}")

# Récupération des informations de la SCI
sci_info = {}
try:
    sci_info = query_one("SELECT name, city, tax_regime FROM sci_info WHERE id = 1;") or {}
except Exception:
    pass

sci_name = sci_info.get("name", "Ma SCI Immobilière")
tax_regime = sci_info.get("tax_regime", "IS")

# Vérification de l'authentification
from utils.auth import authenticate

if "authenticated_user" not in st.session_state:
    # Interface d'accueil / Connexion centrée
    _, col_login, _ = st.columns([1, 1.3, 1])
    with col_login:
        st.write("")
        st.write("")
        st.markdown(f"""
        <div style="text-align: center; margin-bottom: 24px; padding-top: 20px;">
            <span style="font-size: 48px;">🏢</span>
            <h1 style="font-size: 26px; margin: 8px 0; color: #0f172a;">{sci_name}</h1>
            <p style="color: #64748b; font-size: 14px; margin-bottom: 0;">Portail de Gestion Immobilière — Accès sécurisé</p>
        </div>
        """, unsafe_allow_html=True)

        with st.form("form_login"):
            st.markdown("#### Connexion")
            username_input = st.text_input("Identifiant", placeholder="ex: jerome ou claire")
            password_input = st.text_input("Mot de passe", type="password", placeholder="Votre mot de passe")
            
            submit_btn = st.form_submit_button("Se connecter 🔐", type="primary", use_container_width=True)
            if submit_btn:
                user = authenticate(username_input, password_input)
                if user:
                    st.session_state["authenticated_user"] = user
                    st.success(f"Bienvenue, {user.get('full_name')} !")
                    st.rerun()
                else:
                    st.error("Identifiant ou mot de passe incorrect.")

        with st.expander("ℹ️ Première connexion / Aide"):
            st.markdown("""
            **Accès autorisés pour les associés :**
            - Identifiants configurés : `jerome` ou `claire`
            - Mot de passe initial : `sci2026!`
            
            *Une fois connecté, vous pourrez modifier votre mot de passe dans **Paramètres > Sécurité & Utilisateurs**.*
            """)

    # Bloquer l'exécution du reste de l'application tant que non connecté
    st.stop()

# Utilisateur authentifié
current_user = st.session_state["authenticated_user"]

# Barre latérale (Sidebar)
with st.sidebar:
    st.markdown(f"### 🏢 {sci_name}")
    
    # Badge utilisateur connecté + déconnexion
    st.markdown(f"""
    <div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px 14px; margin-bottom: 10px;">
        <div style="font-weight: 600; color: #0f172a; font-size: 14px;">👤 {current_user.get('full_name', current_user.get('username'))}</div>
        <div style="font-size: 12px; color: #64748b;">Compte : <code>{current_user.get('username')}</code></div>
    </div>
    """, unsafe_allow_html=True)

    if st.button("🚪 Se déconnecter", use_container_width=True):
        st.session_state.pop("authenticated_user", None)
        st.rerun()

    st.markdown("---")

    conn_info = get_connection_info()
    if conn_info["is_turso"]:
        st.markdown('<span class="badge badge-turso">☁️ Turso Cloud Connecté</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span class="badge badge-local">💾 Mode Local SQLite</span>', unsafe_allow_html=True)

    st.markdown(f'<br><span class="badge badge-is">⚖️ Régime : {tax_regime} (Impôt sur les Sociétés)</span>', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("**Navigation**")
    menu = st.radio(
        "Menu principal",
        [
            "📊 Tableau de Bord",
            "🏢 Biens & Amortissements",
            "👥 Locataires & Baux",
            "💳 Loyers & Quittances",
            "🏦 Emprunts Bancaires",
            "🏛️ Charges de la SCI",
            "🏠 Charges Lots & Réguls",
            "🤝 Comptes Courants (CCA)",
            "📄 Documents & Juridique",
            "📎 Coffre-fort Numérique (GED)",
            "📑 Liasse Fiscale IS (2065)",
            "⚙️ Paramètres & Configuration"
        ],
        label_visibility="collapsed"
    )

    st.markdown("---")
    st.caption("Application de Gestion SCI à l'IS v2.1")
    st.caption("Développé avec Streamlit & Turso libSQL")

# Routage des vues
if menu == "📊 Tableau de Bord":
    render_dashboard()
elif menu == "🏢 Biens & Amortissements":
    render_properties()
elif menu == "👥 Locataires & Baux":
    render_tenants()
elif menu == "💳 Loyers & Quittances":
    render_rents()
elif menu == "🏦 Emprunts Bancaires":
    render_loans()
elif menu == "🏛️ Charges de la SCI":
    render_sci_expenses()
elif menu == "🏠 Charges Lots & Réguls":
    render_property_expenses()
elif menu == "🤝 Comptes Courants (CCA)":
    render_partner_accounts()
elif menu == "📄 Documents & Juridique":
    render_legal()
elif menu == "📎 Coffre-fort Numérique (GED)":
    render_documents()
elif menu == "📑 Liasse Fiscale IS (2065)":
    render_tax_report()
elif menu == "⚙️ Paramètres & Configuration":
    render_settings()
