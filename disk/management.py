"""
Gestion des opérations sur les disques (montage, démontage, effacement).
"""

import logging
import re
import sys
from typing import Optional, Tuple

from utils.commands import (
    CommandError,
    CommandNotFoundError,
    PlistParseError,
    read_remaining_output,
    run_command,
)
from utils.progress import run_command_with_progress
from disk.detection import get_disk_info

logger = logging.getLogger(__name__)


def _extract_process_info(error_message: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Extrait les informations du processus qui utilise le disque depuis le message d'erreur.

    Args:
        error_message: Message d'erreur de diskutil

    Returns:
        Tuple (process_name, process_id) ou (None, None) si non trouvé
    """
    pattern = r"in use by process (\d+) \(([^)]+)\)"
    match = re.search(pattern, error_message)
    if match:
        return match.group(2), match.group(1)
    return None, None


def unmount_disk(target_disk: str, force: bool = False) -> None:
    """
    Démonte un disque avant le partitionnement.
    Si le démontage échoue, analyse l'erreur et donne des instructions claires.

    Args:
        target_disk: Chemin du disque à démonter
        force: Si True, essaie de forcer le démontage (non implémenté pour l'instant)

    Raises:
        CommandError: Si le démontage échoue et que le disque est utilisé par un processus
    """
    logger.info(f"Démontage du disque {target_disk}...")
    try:
        output = run_command(["diskutil", "unmountDisk", target_disk], capture=True)
        if output:
            logger.info(f"Sortie de unmountDisk: {output}")
        logger.info(f"Disque {target_disk} démonté avec succès")
    except CommandError as e:
        error_msg = ""
        if e.stderr:
            error_msg = e.stderr
        error_msg = f"{error_msg} {str(e)}".strip()

        if "in use by process" in error_msg or "Couldn't unmount" in error_msg:
            process_name, process_id = _extract_process_info(error_msg)

            logger.error(
                f"Le disque {target_disk} ne peut pas être démonté car il est utilisé par un processus"
            )
            print(f"\n❌ Le disque {target_disk} ne peut pas être démonté.")

            if process_name and process_id:
                print(
                    f"   Le processus '{process_name}' (PID: {process_id}) utilise le disque."
                )
                print(f"\n💡 Solutions possibles :")
                print(f"   1. Fermez toutes les applications qui utilisent le disque")
                print(f"   2. Fermez Finder si le disque y est ouvert")
                print(f"   3. Éjectez le disque depuis Finder (⌘+E)")
                print(f"   4. Tuez le processus manuellement : sudo kill {process_id}")
                print(f"   5. Attendez quelques secondes et réessayez")
            else:
                print(f"   Un processus utilise le disque.")
                print(f"\n💡 Solutions possibles :")
                print(f"   1. Fermez toutes les applications qui utilisent le disque")
                print(f"   2. Fermez Finder si le disque y est ouvert")
                print(f"   3. Éjectez le disque depuis Finder (⌘+E)")

            print(
                f"\n⚠️  Le partitionnement ne peut pas continuer tant que le disque est utilisé."
            )
            print(f"   Après avoir libéré le disque, relancez le script.")

            raise CommandError(
                ["diskutil", "unmountDisk", target_disk],
                e.returncode,
                f"Disque utilisé par un processus. {error_msg}",
            ) from e

        logger.warning(f"Impossible de démonter le disque {target_disk}: {e}")
        print(f"\n⚠️  Avertissement : Impossible de démonter le disque {target_disk}")
        print(f"   Le script continuera mais le partitionnement pourrait échouer.")


def verify_disk_safety(target_disk: str) -> None:
    """
    Vérifie que le disque sélectionné n'est pas le disque système principal.

    Args:
        target_disk: Chemin du disque à vérifier
    """
    try:
        disk_info = get_disk_info(target_disk)
        if disk_info.get("Internal", False):
            logger.warning(f"Le disque {target_disk} est marqué comme interne")
            print(
                f"⚠️ AVERTISSEMENT : Le disque {target_disk} est marqué comme interne."
            )
            print(
                "   Assurez-vous qu'il ne s'agit pas de votre disque système principal."
            )
            confirm_internal = input(
                "   Continuer quand même ? (tapez 'YES' pour confirmer) : "
            )
            if confirm_internal != "YES":
                logger.info("Opération annulée par l'utilisateur (disque interne)")
                print("Annulé.")
                sys.exit(0)
    except (CommandError, CommandNotFoundError, PlistParseError) as e:
        logger.warning(f"Impossible de vérifier les informations du disque: {e}")
        print(f"⚠️  Impossible de vérifier les informations du disque : {e}")
        print("   Le script continuera mais soyez prudent.")


def confirm_disk_erasure(target_disk: str, num_partitions: int) -> bool:
    """
    Demande confirmation à l'utilisateur avant d'effacer le disque.

    Args:
        target_disk: Chemin du disque à effacer
        num_partitions: Nombre de partitions qui seront créées

    Returns:
        True si l'utilisateur confirme, False sinon
    """
    print(f"\n⚠️  ATTENTION : Le disque {target_disk} va être TOTALEMENT EFFACÉ.")
    print(f"   Il sera partitionné en {num_partitions} volumes pour les installateurs.")
    confirm = input("   Tapez 'YES' pour confirmer : ")
    if confirm != "YES":
        logger.info("Opération annulée par l'utilisateur")
        print("Annulé.")
        return False
    return True


def restore_disk(target_disk: str) -> None:
    """
    Restaure un disque en l'effaçant complètement et en créant une nouvelle partition ExFAT avec un nom par défaut.

    Args:
        target_disk: Chemin du disque à restaurer

    Note:
        Cette fonction ne lève pas d'exception si la restauration échoue.
        Elle affiche simplement un avertissement.
    """
    logger.info(f"Restauration du disque {target_disk} en cours...")
    try:
        unmount_disk(target_disk)

        restore_cmd = ["diskutil", "eraseDisk", "ExFAT", "USB_DISK", target_disk]

        progress_rules = [
            ("unmounting", 10, "Démontage du disque..."),
            ("unmount", 10, "Démontage du disque..."),
            ("erasing", 20, "Suppression de la partition..."),
            ("formatting", 40, "Formatage du disque..."),
            ("creating", 60, "Création de la partition..."),
            ("mounting", 80, "Montage du volume..."),
            ("mount", 80, "Montage du volume..."),
            ("finished", 100, "Terminé !"),
            ("complete", 100, "Terminé !"),
        ]

        process, output_lines, progress_bar = run_command_with_progress(
            restore_cmd,
            "Restauration",
            progress_rules,
            time_estimate_seconds=30,
        )

        process.wait()
        progress_bar.stop()

        read_remaining_output(process, output_lines)

        if process.returncode != 0:
            raise CommandError(restore_cmd, process.returncode, "\n".join(output_lines))

        if output_lines:
            logger.info(f"Sortie de eraseDisk: {' '.join(output_lines)}")
        logger.info(f"Disque {target_disk} restauré et reformaté en ExFAT avec succès")
        print(f"\n✅ Disque restauré avec succès")
    except (CommandError, CommandNotFoundError) as e:
        logger.warning(f"Impossible de restaurer le disque {target_disk}: {e}")
        print(f"⚠️  Impossible de restaurer le disque : {e}")
        print(
            f"Vous pouvez le faire manuellement avec : diskutil eraseDisk ExFAT <nom_du_disque> {target_disk}"
        )
