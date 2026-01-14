"""
Fonctions utilitaires pour le calcul de tailles.
"""

from pathlib import Path
from typing import Union

from core.config import BYTES_PER_GB, BYTES_PER_MB, MARGIN_SIZE_MB


def get_directory_size(path: Union[str, Path]) -> int:
    """
    Calcule la taille totale d'un répertoire en octets.

    Args:
        path: Chemin du répertoire à mesurer (str ou Path)

    Returns:
        Taille totale en octets
    """
    total_size = 0
    path_obj = Path(path) if isinstance(path, str) else path
    try:
        for filepath in path_obj.rglob("*"):
            if filepath.is_file():
                try:
                    total_size += filepath.stat().st_size
                except (OSError, FileNotFoundError):
                    pass
    except (OSError, PermissionError):
        return 0
    return total_size


def calculate_size_with_margin(size_bytes: int) -> int:
    """
    Calcule la taille avec la marge de sécurité ajoutée.

    Args:
        size_bytes: Taille de base en octets

    Returns:
        Taille avec marge en octets
    """
    return size_bytes + (MARGIN_SIZE_MB * BYTES_PER_MB)


def calculate_partition_size_bytes(size_bytes: int) -> int:
    """
    Calcule la taille d'une partition en octets avec la marge de sécurité.
    Arrondit vers le haut en GB.

    Args:
        size_bytes: Taille de base en octets

    Returns:
        Taille de la partition en octets (arrondie vers le haut en GB)
    """
    size_with_margin = calculate_size_with_margin(size_bytes)
    size_gb = size_with_margin / BYTES_PER_GB
    return int(size_gb + 1) * BYTES_PER_GB


def format_size_for_diskutil(size_bytes: int) -> str:
    """
    Convertit une taille en octets en format accepté par diskutil.
    Format: "XG" pour GB ou "XM" pour MB
    La marge de sécurité est automatiquement ajoutée.

    Args:
        size_bytes: Taille en octets (sans marge)

    Returns:
        Chaîne formatée pour diskutil (ex: "8G", "500M")
    """
    size_with_margin = calculate_size_with_margin(size_bytes)
    size_gb = size_with_margin / BYTES_PER_GB

    if size_gb < 1:
        size_mb = size_with_margin / BYTES_PER_MB
        return f"{int(size_mb)}M"

    return f"{int(size_gb) + 1}G"
