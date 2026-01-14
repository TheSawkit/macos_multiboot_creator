"""
Configuration du script multiboot macOS.
"""

import logging
from typing import TypedDict

# Liste des versions supportées (Ordre décroissant recommandé)
# Format: (Nom affiché, Nom partiel, Nom du volume cible)
TARGET_OS = [
    ("macOS Tahoe", "Tahoe", "Install macOS Tahoe"),
    ("macOS Sequoia", "Sequoia", "Install macOS Sequoia"),
    ("macOS Sonoma", "Sonoma", "Install macOS Sonoma"),
    ("macOS Ventura", "Ventura", "Install macOS Ventura"),
    ("macOS Monterey", "Monterey", "Install macOS Monterey"),
    ("macOS Big Sur", "Big Sur", "Install macOS Big Sur"),
    ("macOS Catalina", "Catalina", "Install macOS Catalina"),
    ("macOS Mojave", "Mojave", "Install macOS Mojave"),
    ("macOS High Sierra", "High Sierra", "Install macOS High Sierra"),
    ("macOS Sierra", "Sierra", "Install macOS Sierra"),
    ("OS X El Capitan", "El Capitan", "Install OS X El Capitan"),
    ("OS X Yosemite", "Yosemite", "Install OS X Yosemite"),
    ("OS X Mavericks", "Mavericks", "Install OS X Mavericks"),
    # TODO: Rendre compatible avec les versions antérieures à Mavericks
    # ("OS X Mountain Lion", "Mountain Lion", "Install OS X Mountain Lion"),
    # ("Mac OS X Lion", "Lion", "Install Mac OS X Lion"),
]

APP_DIR = "/Applications"

MARGIN_SIZE_MB = 500

MAX_VOLUME_WAIT_TIME = 30

MIN_VOLUME_SIZE_BYTES = 100 * 1024 * 1024

EXECUTABLE_PERMISSIONS = 0o111

BYTES_PER_KB = 1024
BYTES_PER_MB = BYTES_PER_KB * 1024
BYTES_PER_GB = BYTES_PER_MB * 1024


class InstallerInfo(TypedDict):
    """Type pour représenter les informations d'un installateur macOS."""

    name: str
    path: str
    volume: str
    size_bytes: int


def setup_logging(debug: bool = False) -> None:
    """
    Configure le logging selon le mode debug.

    Args:
        debug: Si True, active le logging détaillé (DEBUG). Sinon, désactive le logging (WARNING).
    """
    if debug:
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    else:
        logging.basicConfig(
            level=logging.WARNING,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
