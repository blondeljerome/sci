"""
Module d'envoi d'emails via SMTP (Quittances, Avis d'échéance, Relances).
Prend en charge TLS, pièces jointes HTML/PDF et messages personnalisés.
"""
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from typing import Tuple, Optional
import streamlit as st
from database import query_one

def get_smtp_config() -> dict:
    """
    Récupère les paramètres SMTP depuis :
    1. La table sci_info en base de données
    2. Streamlit Secrets (st.secrets)
    """
    config = {
        "server": "",
        "port": 587,
        "username": "",
        "password": "",
        "use_tls": True,
        "sender_email": ""
    }

    # 1. En base
    try:
        sci = query_one("SELECT smtp_server, smtp_port, smtp_username, smtp_password, smtp_use_tls, smtp_sender_email, manager_email FROM sci_info WHERE id = 1;")
        if sci:
            config["server"] = sci.get("smtp_server") or ""
            config["port"] = int(sci.get("smtp_port") or 587)
            config["username"] = sci.get("smtp_username") or ""
            config["password"] = sci.get("smtp_password") or ""
            config["use_tls"] = bool(sci.get("smtp_use_tls", 1))
            config["sender_email"] = sci.get("smtp_sender_email") or sci.get("manager_email") or ""
    except Exception:
        pass

    # 2. Fallback st.secrets
    try:
        if hasattr(st, "secrets") and "SMTP_SERVER" in st.secrets:
            config["server"] = st.secrets["SMTP_SERVER"]
            config["port"] = int(st.secrets.get("SMTP_PORT", 587))
            config["username"] = st.secrets.get("SMTP_USERNAME", "")
            config["password"] = st.secrets.get("SMTP_PASSWORD", "")
            config["sender_email"] = st.secrets.get("SMTP_SENDER_EMAIL", config["sender_email"])
    except Exception:
        pass

    return config

def send_email(
    to_email: str,
    subject: str,
    html_body: str,
    attachment_filename: Optional[str] = None,
    attachment_content: Optional[str] = None
) -> Tuple[bool, str]:
    """
    Envoie un email HTML avec pièce jointe optionnelle.
    Retourne (succès: bool, message: str).
    """
    if not to_email or "@" not in to_email:
        return False, "Adresse email du destinataire invalide ou non renseignée."

    config = get_smtp_config()
    if not config["server"] or not config["username"]:
        return False, "Le serveur SMTP n'est pas configuré. Rendez-vous dans '⚙️ Paramètres > Configuration Email SMTP' pour renseigner vos identifiants."

    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = config["sender_email"] or config["username"]
        msg["To"] = to_email
        msg["Subject"] = subject

        # Corps de message HTML
        part_html = MIMEText(html_body, "html", "utf-8")
        msg.attach(part_html)

        # Pièce jointe optionnelle (ex: quittance HTML/PDF)
        if attachment_filename and attachment_content:
            part_attach = MIMEApplication(attachment_content.encode("utf-8"), Name=attachment_filename)
            part_attach['Content-Disposition'] = f'attachment; filename="{attachment_filename}"'
            msg.attach(part_attach)

        # Connexion SMTP
        server = smtplib.SMTP(config["server"], config["port"], timeout=15)
        if config["use_tls"]:
            server.starttls()
        
        if config["password"]:
            server.login(config["username"], config["password"])

        server.sendmail(msg["From"], [to_email], msg.as_string())
        server.quit()

        return True, f"Email envoyé avec succès à {to_email} !"

    except Exception as e:
        return False, f"Erreur lors de l'envoi de l'email : {str(e)}"
