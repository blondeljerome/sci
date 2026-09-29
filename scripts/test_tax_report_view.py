"""Test d'exécution de la vue tax_report.py."""

from unittest.mock import MagicMock, patch

from views.tax_report import render_tax_report


def test_render_tax_report() -> None:
    """Valide l'exécution complète de render_tax_report() avec mocks."""
    with (
        patch("streamlit.selectbox", return_value=2026),
        patch("streamlit.tabs") as mock_tabs,
        patch("streamlit.plotly_chart"),
    ):
        # Simuler les 4 onglets
        mock_tabs.return_value = [
            MagicMock(),
            MagicMock(),
            MagicMock(),
            MagicMock(),
        ]

        render_tax_report()
        print("✅ render_tax_report() s'est exécuté sans aucune exception !")


if __name__ == "__main__":
    test_render_tax_report()
