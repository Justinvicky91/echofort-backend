"""
EchoFort Configuration
Centralized config for all features including Block 5 safety filters
"""

import os
from typing import Literal

# ============================================================================
# BLOCK 5: EXTREMISM & AI ATTACK DETECTION
# ============================================================================

class Block5Config:
    """Block 5: AI Attack & Harmful Extremism Filters"""
    
    # Feature toggles
    ENABLE_EXTREMISM_DETECTION_IMAGE: bool = os.getenv("ENABLE_EXTREMISM_DETECTION_IMAGE", "true").lower() == "true"
    ENABLE_EXTREMISM_DETECTION_EMAIL: bool = os.getenv("ENABLE_EXTREMISM_DETECTION_EMAIL", "true").lower() == "true"
    ENABLE_EXTREMISM_DETECTION_VOICE: bool = os.getenv("ENABLE_EXTREMISM_DETECTION_VOICE", "false").lower() == "true"
    
    # Vault logging threshold (set to 99 to effectively disable)
    EXTREMISM_VAULT_THRESHOLD: int = int(os.getenv("EXTREMISM_VAULT_THRESHOLD", "7"))
    
    # Detection sensitivity multipliers
    EXTREMISM_KEYWORD_MULTIPLIER: float = float(os.getenv("EXTREMISM_KEYWORD_MULTIPLIER", "2.0"))
    SELF_HARM_KEYWORD_MULTIPLIER: float = float(os.getenv("SELF_HARM_KEYWORD_MULTIPLIER", "3.0"))
    
    # Disclaimer text
    AI_PREDICTION_DISCLAIMER: str = (
        "These are automated predictions, not legal determinations. "
        "Use your own judgment and seek professional advice if needed."
    )

# ============================================================================
# GENERAL CONFIG
# ============================================================================

class GeneralConfig:
    """General application config"""
    
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    JWT_SECRET: str = os.getenv("JWT_SECRET", "")
    ENVIRONMENT: Literal["dev", "staging", "prod"] = os.getenv("ENVIRONMENT", "dev")  # type: ignore

# Export for easy import
block5_config = Block5Config()
general_config = GeneralConfig()
