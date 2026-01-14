"""
Gestion de la ligne de commande (CLI) pour le script multiboot macOS.
"""
import argparse

from .config import APP_DIR


def parse_arguments() -> argparse.Namespace:
    """
    Parse les arguments de ligne de commande.

    Returns:
        Namespace contenant les arguments parsés
    """
    parser = argparse.ArgumentParser(
        description="Créer une clé USB multiboot pour macOS",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Active le mode debug avec affichage des logs détaillés",
    )
    parser.add_argument(
        "--app-dir",
        type=str,
        default=APP_DIR,
        help=f"Répertoire où chercher les installateurs macOS (par défaut: {APP_DIR})",
    )
    return parser.parse_args()
