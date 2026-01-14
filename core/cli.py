"""
Gestion de la ligne de commande (CLI) pour le script multiboot macOS.
"""
import argparse

from .config import APP_DIR
from locales import t


def parse_arguments() -> argparse.Namespace:
    """
    Parse les arguments de ligne de commande.

    Returns:
        Namespace contenant les arguments parsés
    """
    parser = argparse.ArgumentParser(
        description=t("cli.description"),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help=t("cli.debug_help"),
    )
    parser.add_argument(
        "--app-dir",
        type=str,
        default=APP_DIR,
        help=t("cli.app_dir_help", app_dir=APP_DIR),
    )
    return parser.parse_args()
