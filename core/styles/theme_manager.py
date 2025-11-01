import streamlit as st
from typing import Dict, Optional
from dataclasses import dataclass

@dataclass
class ColorPalette:
    """Data class for color management"""
    bg: str = "#222831"
    panel: str = "#393E46"
    accent: str = "#00ADB5"
    accent_light: str = "#00E0C6"
    text: str = "#EEEEEE"
    text_muted: str = "#CCCCCC"
    sidebar_bg: str = "#1d2228"

class ThemeManager:
    """
    Optimized theme manager for Streamlit applications.
    Handles styling with better organization and performance.
    """
    
    def __init__(self, colors: Optional[ColorPalette] = None):
        self.colors = colors or ColorPalette()
        self.font_family = "'Poppins', sans-serif"
        self.base_font_size = "15px"
        self._css_cache = None
    
    def _generate_global_styles(self) -> str:
        """Generate global CSS styles"""
        return f"""
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&display=swap');
        
        /* Global Styles */
        html, body, [class*="css"] {{
            background-color: {self.colors.bg} !important;
            color: {self.colors.text} !important;
            font-family: {self.font_family} !important;
            font-size: {self.base_font_size};
        }}
        
        h1, h2, h3, h4, h5 {{
            color: {self.colors.text} !important;
            font-weight: 600 !important;
            letter-spacing: 0.5px;
        }}
        """
    
    def _generate_scrollbar_styles(self) -> str:
        """Generate scrollbar styles"""
        return f"""
        /* Custom Scrollbar */
        ::-webkit-scrollbar {{
            width: 8px;
        }}
        ::-webkit-scrollbar-thumb {{
            background: {self.colors.accent};
            border-radius: 10px;
        }}
        ::-webkit-scrollbar-track {{
            background: {self.colors.panel};
        }}
        """
    
    def _generate_button_styles(self) -> str:
        """Generate button styles"""
        return f"""
        /* Button Styles */
        .stButton > button {{
            background: linear-gradient(90deg, {self.colors.accent}, {self.colors.accent_light}) !important;
            color: {self.colors.bg} !important;
            border: none !important;
            border-radius: 8px !important;
            font-weight: 600 !important;
            padding: 0.5rem 1rem !important;
            transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
            cursor: pointer;
        }}
        
        .stButton > button:hover {{
            transform: scale(1.05);
            filter: brightness(1.15);
            box-shadow: 0 4px 15px rgba(0, 173, 181, 0.3);
        }}
        
        .stButton > button:active {{
            transform: scale(0.98);
        }}
        """
    
    def _generate_kpi_styles(self) -> str:
        """Generate KPI card styles"""
        return f"""
        /* KPI Cards */
        .kpi-card {{
            background: {self.colors.panel};
            border-radius: 16px;
            padding: 20px;
            text-align: center;
            box-shadow: 0 6px 20px rgba(0, 0, 0, 0.35);
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            min-height: 160px;
            display: flex;
            flex-direction: column;
            justify-content: center;
            overflow: hidden;
            border: 1px solid rgba(255, 255, 255, 0.05);
        }}
        
        .kpi-card:hover {{
            box-shadow: 0 0 20px {self.colors.accent}55;
            transform: translateY(-4px);
            border-color: {self.colors.accent}33;
        }}
        
        .kpi-icon {{
            font-size: 1.5rem;
            margin-bottom: 8px;
        }}
        
        .kpi-title {{
            font-size: 0.9rem;
            color: {self.colors.accent};
            text-transform: uppercase;
            margin-bottom: 8px;
            font-weight: 500;
            letter-spacing: 1px;
        }}
        
        .kpi-value {{
            font-size: 2rem;
            font-weight: 700;
            background: linear-gradient(90deg, {self.colors.accent}, {self.colors.accent_light});
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 4px;
        }}
        
        .kpi-delta {{
            font-size: 0.8rem;
            color: {self.colors.text_muted};
            font-weight: 500;
        }}
        """
    
    def _generate_sidebar_styles(self) -> str:
        """Generate sidebar styles"""
        return f"""
        /* Sidebar Styles */
        section[data-testid="stSidebar"] {{
            background-color: {self.colors.sidebar_bg} !important;
            border-right: 1px solid rgba(255, 255, 255, 0.1);
            width: 300px !important;
            min-width: 300px !important;
            max-width: 300px !important;
            animation: slideInSidebar 0.8s cubic-bezier(0.4, 0, 0.2, 1) forwards;
            opacity: 0;
        }}
        
        @keyframes slideInSidebar {{
            from {{
                transform: translateX(-40px);
                opacity: 0;
            }}
            to {{
                transform: translateX(0);
                opacity: 1;
            }}
        }}
        
        [data-testid="stSidebarContent"] {{
            width: 100% !important;
            padding: 0 !important;
        }}
        
        /* Hide sidebar collapse control */
        div[data-testid="stSidebarCollapseControl"] {{
            display: none !important;
        }}
        
        /* Sidebar stats */
        .sidebar-stats {{
            background: rgba(57, 62, 70, 0.3);
            border-radius: 12px;
            padding: 1rem;
            margin-top: 1rem;
            border: 1px solid rgba(255, 255, 255, 0.05);
        }}
        
        .stat-item {{
            padding: 0.5rem 0;
            font-size: 0.9rem;
            color: {self.colors.text_muted};
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        }}
        
        .stat-item:last-child {{
            border-bottom: none;
        }}
        
        .sidebar-title {{
            color: {self.colors.accent};
            font-weight: 600;
            margin-bottom: 1rem;
            text-transform: uppercase;
            letter-spacing: 1px;
            font-size: 0.9rem;
        }}
        """
    
    def _generate_radio_button_styles(self) -> str:
        """Generate radio button styles for sidebar navigation"""
        return f"""
        /* Radio Button Navigation */
        [data-testid="stSidebar"] .stRadio {{
            width: 100% !important;
            padding: 0 !important;
        }}
        
        [data-testid="stSidebar"] label[data-testid="stWidgetLabel"] {{
            display: none !important;
        }}
        
        [data-testid="stSidebar"] .stRadio > div {{
            display: flex !important;
            flex-direction: column !important;
            width: 100% !important;
            gap: 2px !important;
            padding: 0 !important;
        }}
        
        [data-testid="stSidebar"] .stRadio div[role="radiogroup"] label {{
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            width: 100% !important;
            height: 48px !important;
            background: rgba(57, 62, 70, 0.3);
            color: {self.colors.text} !important;
            font-weight: 500 !important;
            border: none !important;
            cursor: pointer !important;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            text-align: center !important;
            font-size: 0.95rem;
            opacity: 0;
            animation: fadeInButtons 0.8s ease forwards;
        }}
        
        [data-testid="stSidebar"] .stRadio div[role="radiogroup"] label:hover {{
            background: {self.colors.panel} !important;
            color: {self.colors.accent} !important;
            box-shadow: inset 3px 0 0 {self.colors.accent};
        }}
        
        [data-testid="stSidebar"] .stRadio div[role="radiogroup"] [aria-checked="true"] label {{
            background: linear-gradient(90deg, {self.colors.accent}, {self.colors.accent_light}) !important;
            color: {self.colors.bg} !important;
            font-weight: 600 !important;
            box-shadow: 0 0 15px rgba(0, 173, 181, 0.4);
        }}
        
        @keyframes fadeInButtons {{
            from {{ 
                opacity: 0; 
                transform: translateX(-10px); 
            }}
            to {{ 
                opacity: 1; 
                transform: translateX(0); 
            }}
        }}
        
        /* Hide radio button circles */
        [data-testid="stSidebar"] .stRadio div[role="radio"] input,
        [data-testid="stSidebar"] .stRadio div[role="radio"] svg {{
            display: none !important;
        }}
        """
    
    def _generate_footer_styles(self) -> str:
        """Generate footer styles"""
        return f"""
        /* Footer Styles */
        .footer-wrapper {{
            width: 100%;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            text-align: center;
            margin-top: 80px;
            padding: 30px 20px;
            border-top: 1px solid rgba(255, 255, 255, 0.1);
        }}
        
        .footer-accent {{
            height: 4px;
            width: 100px;
            background: linear-gradient(90deg, {self.colors.accent}, {self.colors.accent_light});
            border-radius: 3px;
            margin-bottom: 15px;
        }}
        
        .footer-text {{
            font-size: 0.95rem;
            color: {self.colors.text_muted};
            line-height: 1.6;
            max-width: 700px;
            margin: 0 auto;
        }}
        
        .footer-fade {{
            animation: fadeInFooter 1s ease-in-out;
        }}
        
        @keyframes fadeInFooter {{
            from {{
                opacity: 0;
                transform: translateY(20px);
            }}
            to {{
                opacity: 1;
                transform: translateY(0);
            }}
        }}
        """
    
    def _generate_additional_styles(self) -> str:
        """Generate additional utility styles"""
        return f"""
        /* Additional Utilities */
        .stMetric {{
            background: rgba(57, 62, 70, 0.3);
            padding: 1rem;
            border-radius: 8px;
            border: 1px solid rgba(255, 255, 255, 0.05);
        }}
        
        .stSelectbox > div > div {{
            background-color: rgba(57, 62, 70, 0.5);
            border: 1px solid rgba(255, 255, 255, 0.1);
        }}
        
        .stExpander {{
            background: rgba(57, 62, 70, 0.2);
            border: 1px solid rgba(255, 255, 255, 0.05);
            border-radius: 8px;
        }}
        
        /* Loading animations */
        @keyframes pulse {{
            0%, 100% {{ opacity: 1; }}
            50% {{ opacity: 0.5; }}
        }}
        
        .loading {{
            animation: pulse 2s infinite;
        }}
        
        /* Custom divider */
        hr {{
            border: none;
            height: 1px;
            background: linear-gradient(90deg, transparent, {self.colors.accent}, transparent);
            margin: 2rem 0;
        }}
        """
    
    def generate_css(self) -> str:
        """Generate complete CSS with all styles"""
        if self._css_cache is None:
            styles = [
                self._generate_global_styles(),
                self._generate_scrollbar_styles(),
                self._generate_button_styles(),
                self._generate_kpi_styles(),
                self._generate_sidebar_styles(),
                self._generate_radio_button_styles(),
                self._generate_footer_styles(),
                self._generate_additional_styles()
            ]
            self._css_cache = "\n".join(styles)
        
        return f"<style>{self._css_cache}</style>"
    
    def apply_theme(self) -> None:
        """Apply the complete theme to Streamlit"""
        st.markdown(self.generate_css(), unsafe_allow_html=True)
    
    def update_colors(self, **kwargs) -> None:
        """Update color palette and clear cache"""
        for key, value in kwargs.items():
            if hasattr(self.colors, key):
                setattr(self.colors, key, value)
        self._css_cache = None  # Clear cache to regenerate CSS
    
    def create_kpi_card(self, title: str, value: str, icon: str = "", delta: Optional[str] = None) -> str:
        """Create a KPI card HTML"""
        icon_html = f'<div class="kpi-icon">{icon}</div>' if icon else ''
        delta_html = f'<div class="kpi-delta">{delta}</div>' if delta else ''
        
        return f"""
        <div class="kpi-card">
            {icon_html}
            <div class="kpi-title">{title}</div>
            <div class="kpi-value">{value}</div>
            {delta_html}
        </div>
        """
    
    def create_footer(self, text: str) -> str:
        """Create footer HTML"""
        return f"""
        <div class="footer-wrapper footer-fade">
            <div class="footer-accent"></div>
            <div class="footer-text">
                <p>{text}</p>
            </div>
        </div>
        """