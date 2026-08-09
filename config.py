"""
Configuration settings for Mirchi Fashion Gemini Visual Generation System.
"""

import os
from pathlib import Path
from dataclasses import dataclass, field
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()


@dataclass
class Settings:
    # Vertex AI Configuration
    VERTEX_CREDENTIALS_BASE64: str = field(default_factory=lambda: os.getenv("VERTEX_CREDENTIALS_BASE64", ""))
    VERTEX_CREDENTIALS_PATH: Path = field(default_factory=lambda: Path(os.getenv("VERTEX_CREDENTIALS_PATH", "vertex-cred.json")))
    VERTEX_PROJECT_ID: str = field(default_factory=lambda: os.getenv("VERTEX_PROJECT_ID", "silicon-cocoa-476407-n3"))
    VERTEX_LOCATION: str = field(default_factory=lambda: os.getenv("VERTEX_LOCATION", "global"))

    # Gemini API Configuration
    GEMINI_API_KEY: str = field(default_factory=lambda: os.getenv("GEMINI_API_KEY", ""))
    
    # Model Configurations
    ORCHESTRATOR_MODEL: str = field(default_factory=lambda: os.getenv("ORCHESTRATOR_MODEL", "gemini-3.6-flash"))
    GENERATION_MODEL: str = field(default_factory=lambda: os.getenv("GENERATION_MODEL", "gemini-3-pro-image"))
    INSPECTOR_MODEL: str = field(default_factory=lambda: os.getenv("INSPECTOR_MODEL", "gemini-3.6-flash"))
    
    # Quality Gate Thresholds
    MIN_PATTERN_FIDELITY: float = 0.88
    MIN_ANATOMICAL_ACCURACY: float = 0.90
    MIN_COMPOSITE_SCORE: float = 0.88
    
    # Execution Settings
    MAX_RETRIES: int = 2
    OUTPUT_RESOLUTION: str = "2048x2048"
    
    # Directory Paths
    BASE_DIR: Path = field(default_factory=lambda: Path(__file__).resolve().parent)
    
    @property
    def INPUT_DIR(self) -> Path:
        return self.BASE_DIR / "1  INPUT"
        
    @property
    def MOODBOARD_DIR(self) -> Path:
        return self.BASE_DIR / "3  MOODBOARD REFERENCE"
        
    @property
    def OUTPUT_DIR(self) -> Path:
        return self.BASE_DIR / "output"
        
    @property
    def HUMAN_REVIEW_DIR(self) -> Path:
        return self.OUTPUT_DIR / "human_review"
        
    @property
    def APPROVED_DIR(self) -> Path:
        return self.OUTPUT_DIR / "approved"


settings = Settings()

