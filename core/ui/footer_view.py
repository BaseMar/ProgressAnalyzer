import streamlit as st

class FooterView:
    """
    Klasa odpowiedzialna za wyświetlanie stopki aplikacji.
    Zawiera jedynie strukturę HTML — stylizacja pochodzi z ThemeManagera.
    """

    def __init__(self):
        self.text = (
            "Ten projekt został stworzony, aby wizualizować mój osobisty progres na siłowni "
            "przy użyciu Streamlit, MS SQL oraz Plotly. "
            "Wszystkie dane są prawdziwe i pochodzą z moich własnych zapisów treningowych."
        )

    def render(self):
        """Renderuje stopkę z animacją i paskiem akcentu."""
        st.markdown(
            f"""
            <div class="footer-wrapper footer-fade">
                <div class="footer-accent"></div>
                <div class="footer-text">
                    <p class="footer-text">{self.text}</p>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
