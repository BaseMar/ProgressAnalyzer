from dataclasses import dataclass
from typing import List

@dataclass
class AppConfig:
    """Application configuration"""
    APP_TITLE: str = "Gym Progress Dashboard"
    SIDEBAR_SECTIONS: List[str] = None
    
    def __post_init__(self):
        if self.SIDEBAR_SECTIONS is None:
            self.SIDEBAR_SECTIONS = [
                "Dashboard",
                "Formularz",
                "Analiza ćwiczeń", 
                "Analiza grup mięśniowych",
                "Pomiary ciała"
            ]