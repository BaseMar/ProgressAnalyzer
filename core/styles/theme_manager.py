import streamlit as st

class ThemeManager:
    """
    Klasa odpowiedzialna za stylizację aplikacji Streamlit:
    kolory, fonty, animacje i wygląd komponentów.
    """

    def __init__(self):
        self.colors = {
            "bg": "#222831",
            "panel": "#393E46",
            "accent": "#00ADB5",
            "text": "#EEEEEE",
        }
        self.font_family = "'Poppins', sans-serif"
        self.base_font_size = "15px"

    def apply_theme(self):
        css = f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&display=swap');

        /* --- Global --- */
        html, body, [class*="css"] {{
            background-color: {self.colors['bg']} !important;
            color: {self.colors['text']} !important;
            font-family: {self.font_family} !important;
            font-size: {self.base_font_size};
            transition: background-color 0.4s ease, color 0.4s ease;
        }}

        h1, h2, h3, h4, h5 {{
            color: {self.colors['text']} !important;
            font-weight: 600 !important;
            letter-spacing: 0.5px;
        }}

        /* --- Scrollbar --- */
        ::-webkit-scrollbar {{
            width: 8px;
        }}
        ::-webkit-scrollbar-thumb {{
            background: {self.colors['accent']};
            border-radius: 10px;
        }}

        /* --- Buttons --- */
        .stButton>button {{
            background: linear-gradient(90deg, {self.colors['accent']}, #00E0C6) !important;
            color: {self.colors['bg']} !important;
            border: none !important;
            border-radius: 8px !important;
            font-weight: 600 !important;
            padding: 0.5rem 1rem !important;
            transition: all 0.25s ease-in-out;
        }}
        .stButton>button:hover {{
            transform: scale(1.05);
            filter: brightness(1.15);
        }}
        
        /* --- KPI CARDS --- */
        .kpi-card {{
            position: relative;
            background: {self.colors['panel']};
            border-radius: 16px;
            padding: 20px;
            text-align: center;
            box-shadow: 0 6px 20px rgba(0,0,0,0.35);
            transition: all 0.3s ease;
            min-height: 160px;
            display: flex;
            flex-direction: column;
            justify-content: center;
            overflow: hidden;
        }}
        .kpi-card:hover {{
            box-shadow: 0 0 20px {self.colors['accent']}55;
            transform: translateY(-4px);
        }}

        .kpi-title {{
            font-size: 0.9rem;
            color: {self.colors['accent']};
            text-transform: uppercase;
            letter-spacing: 0.8px;
            margin-bottom: 8px;
        }}

        .kpi-value {{
            font-size: 2rem;
            font-weight: 700;
            background: linear-gradient(90deg, {self.colors['accent']}, #00E0C6);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            opacity: 0;
            animation: fadeIn 0.8s forwards;
        }}
        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(6px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}

        .kpi-delta {{
            font-size: 1rem;
            margin-top: 6px;
            font-weight: 600;
            transition: transform 0.3s ease;
        }}
        .kpi-delta:hover {{
            transform: scale(1.05);
        }}
        .kpi-delta.positive {{ color: #4CAF50; }}
        .kpi-delta.negative {{ color: #F44336; }}
        .kpi-delta.neutral {{ color: #B0BEC5; }}


        /* --- FOOTER --- */
        .footer-wrapper {{
            width: 100%;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            text-align: center;
            margin-top: 80px;
            padding-top: 30px;
            border-top: 1px solid rgba(255,255,255,0.1);
        }}

        .footer-accent {{
            height: 4px;
            width: 100px;
            background: linear-gradient(90deg, #00ADB5, #00E0C6);
            border-radius: 3px;
            margin-bottom: 15px;
            transition: all 0.3s ease;
        }}
        .footer-accent:hover {{
            filter: brightness(1.2);
            transform: scaleX(1.05);
        }}

        .footer-text {{
            font-size: 0.95rem;
            color: #CCCCCC;
            line-height: 1.6;
            letter-spacing: 0.3px;
            max-width: 700px;
            margin: 0 auto;
            text-align: center;
        }}

        .footer-fade {{
            animation: fadeInFooter 1s ease-in-out;
        }}

        @keyframes fadeInFooter {{
            from {{
                opacity: 0;
                transform: translateY(10px);
            }}
            to {{
                opacity: 1;
                transform: translateY(0);
            }}
        }}
        </style>
        """
        st.markdown(css, unsafe_allow_html=True)
