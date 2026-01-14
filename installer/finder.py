"""
Gestion de la détection et du traitement des installateurs macOS.
"""

import logging
import sys
from pathlib import Path
from typing import List

from core.config import (
    APP_DIR,
    BYTES_PER_GB,
    InstallerInfo,
    MARGIN_SIZE_MB,
    TARGET_OS,
)
from utils.size import calculate_size_with_margin, get_directory_size

logger = logging.getLogger(__name__)


def find_installers(app_dir: str = APP_DIR) -> List[InstallerInfo]:
    """
    Trouve les installateurs disponibles dans le répertoire spécifié.

    Args:
        app_dir: Répertoire où chercher les installateurs (par défaut: APP_DIR)

    Returns:
        Liste de dictionnaires contenant 'name', 'path', 'volume' et 'size_bytes'
        pour chaque installateur trouvé.

    Raises:
        SystemExit: Si aucun installateur n'est trouvé
    """
    found = []
    app_path = Path(app_dir)
    logger.info(f"Recherche des installateurs dans {app_dir}...")
    print(f"🔍 Recherche des installateurs dans {app_dir}...")

    if not app_path.exists():
        logger.error(f"Le répertoire {app_dir} n'existe pas")
        print(f"❌ Le répertoire {app_dir} n'existe pas.")
        sys.exit(1)

    if not app_path.is_dir():
        logger.error(f"{app_dir} n'est pas un répertoire")
        print(f"❌ {app_dir} n'est pas un répertoire.")
        sys.exit(1)

    for name, keyword, vol_name in TARGET_OS:
        try:
            candidates = [
                f
                for f in app_path.iterdir()
                if keyword in f.name and f.suffix == ".app" and "Install" in f.name
            ]
        except PermissionError:
            logger.error(f"Permission refusée pour accéder à {app_dir}")
            print(f"❌ Permission refusée pour accéder à {app_dir}")
            sys.exit(1)

        if not candidates:
            continue

        if len(candidates) > 1:
            logger.warning(
                f"Plusieurs installateurs trouvés pour {name}: {[c.name for c in candidates]}. "
                f"Utilisation du premier: {candidates[0].name}"
            )
            print(
                f"⚠️ Plusieurs installateurs trouvés pour {name}, utilisation de: {candidates[0].name}"
            )

        path = candidates[0]
        if path.is_dir():
            logger.info(f"Calcul de la taille de {name}...")
            size_bytes = get_directory_size(path)
            size_gb = size_bytes / BYTES_PER_GB
            size_with_margin = calculate_size_with_margin(size_bytes)
            size_with_margin_gb = size_with_margin / BYTES_PER_GB
            logger.info(
                f"Trouvé: {name} -> {path} ({size_gb:.2f} GB, {size_with_margin_gb:.2f} GB avec marge)"
            )
            print(f"✅ Trouvé : {name}")
            found.append(
                InstallerInfo(
                    name=name,
                    path=str(path),
                    volume=vol_name,
                    size_bytes=size_bytes,
                )
            )
        else:
            logger.warning(f"Chemin invalide pour {name}: {path}")
            print(f"   ⚠️  Chemin invalide pour {name}: {path}")

    if not found:
        logger.error("Aucun installateur trouvé")
        print(
            "❌ Aucun installateur trouvé. Utilisez 'Mist' pour les télécharger d'abord."
        )
        print("\n📥 Télécharger Mist : https://github.com/ninxsoft/Mist/releases")
        sys.exit(1)

    return found


def display_size_summary(installers: List[InstallerInfo]) -> None:
    """
    Affiche un résumé des tailles des installateurs.

    Args:
        installers: Liste des installateurs trouvés
    """
    logger.info("Affichage du résumé des tailles")
    print(f"\n📊 Résumé des tailles :")
    for inst in installers:
        size_gb = inst["size_bytes"] / BYTES_PER_GB
        size_with_margin = calculate_size_with_margin(inst["size_bytes"])
        size_with_margin_gb = size_with_margin / BYTES_PER_GB
        print(
            f"   • {inst['name']}: {size_gb:.2f} GB (+ {MARGIN_SIZE_MB} MB marge = {size_with_margin_gb:.2f} GB)"
        )


def calculate_total_space_needed(installers: List[InstallerInfo]) -> int:
    """
    Calcule l'espace total nécessaire en octets pour tous les installateurs.

    Args:
        installers: Liste des installateurs trouvés

    Returns:
        Espace total nécessaire en octets (avec marge incluse)
    """
    total_needed_bytes = sum(
        calculate_size_with_margin(inst["size_bytes"]) for inst in installers
    )
    logger.info(f"Espace total nécessaire: {total_needed_bytes / BYTES_PER_GB:.2f} GB")
    return total_needed_bytes
