"""
Test d'exécution de la vue tax_report.py
"""
import sys
from unittest.mock import MagicMock, patch
import pandas as pd

# Mocker Streamlit pour valider l'exécution complète de render_tax_report() sans erreur
def test_render_tax_report():
    import streamlit as st
    from views.tax_report import render_tax_report
    
    with patch("streamlit.selectbox", return_value=2026), \
         patch("streamlit.tabs") as mock_tabs, \
         patch("streamlit.plotly_chart") as mock_plotly:
        
        # Simuler les 4 onglets
        mock_tabs.return_value = [MagicMock(), MagicMock(), MagicMock(), MagicMock()]
        
        try:
            render_tax_report()
            print("✅ render_tax_report() s'est exécuté sans aucune exception !")
        except Exception as e:
            print(f"❌ Erreur lors de l'exécution de render_tax_report : {e}")
            raise e

if __name__ == "__main__":
    test_render_tax_report()
