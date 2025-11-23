from dataclasses import dataclass
from typing import List, Optional


@dataclass
class AppConfig:
    """Application configuration"""

    APP_TITLE: str = "Gym Progress Dashboard"
    SIDEBAR_SECTIONS: Optional[List[str]] = None

    def __post_init__(self):
        if self.SIDEBAR_SECTIONS is None:
            self.SIDEBAR_SECTIONS = [
                "Dashboard",
                "Forms",
                "Exercise Analysis",
                "Muscle Groups",
                "Body Measurements",
            ]
