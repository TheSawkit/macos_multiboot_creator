"""
Module core - Configuration et interface en ligne de commande.
"""

from .cli import parse_arguments
from .config import (
    APP_DIR,
    InstallerInfo,
    MARGIN_SIZE_MB,
    MAX_VOLUME_WAIT_TIME,
    TARGET_OS,
    setup_logging,
)

__all__ = [
    "APP_DIR",
    "InstallerInfo",
    "MARGIN_SIZE_MB",
    "MAX_VOLUME_WAIT_TIME",
    "TARGET_OS",
    "parse_arguments",
    "setup_logging",
]
