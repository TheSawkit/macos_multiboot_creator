"""
Gestion des opérations sur les disques (montage, démontage, effacement).
"""

import logging
import re
import sys
from typing import Optional, Tuple

from locales import t
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
    logger.info(t("disk.unmount", target_disk=target_disk))
    try:
        output = run_command(["diskutil", "unmountDisk", target_disk], capture=True)
        if output:
            logger.info(output)
        logger.info(t("disk.unmount_success", target_disk=target_disk))
    except CommandError as e:
        error_msg = ""
        if e.stderr:
            error_msg = e.stderr
        error_msg = f"{error_msg} {str(e)}".strip()

        if "in use by process" in error_msg or "Couldn't unmount" in error_msg:
            process_name, process_id = _extract_process_info(error_msg)
            print(t("disk.unmount_fail", target_disk=target_disk))

            if process_name and process_id:
                print(
                    t(
                        "disk.proc_using",
                        process_name=process_name,
                        process_id=process_id,
                    )
                )
                print(t("disk.solutions"))
                print(t("disk.solution_1"))
                print(t("disk.solution_2"))
                print(t("disk.solution_3"))
                print(t("disk.solution_4_kill", process_id=process_id))
                print(t("disk.solution_5_wait"))
            else:
                print(t("disk.proc_using_generic"))
                print(t("disk.solutions"))
                print(t("disk.solution_1"))
                print(t("disk.solution_2"))
                print(t("disk.solution_3"))

            print(t("disk.partitioning_blocked"))
            print(t("disk.rerun_after_free"))

            raise CommandError(
                ["diskutil", "unmountDisk", target_disk],
                e.returncode,
                f"Disque utilisé par un processus. {error_msg}",
            ) from e

        logger.warning(e)
        print(t("disk.unmount_warning", target_disk=target_disk))
        print(t("disk.unmount_warning_more"))


def verify_disk_safety(target_disk: str) -> None:
    """
    Vérifie que le disque sélectionné n'est pas le disque système principal.

    Args:
        target_disk: Chemin du disque à vérifier
    """
    try:
        disk_info = get_disk_info(target_disk)
        if disk_info.get("Internal", False):
            print(t("disk.internal_warning", target_disk=target_disk))
            print(t("disk.internal_warning_more"))
            confirm_internal = input(t("disk.internal_confirm"))
            if confirm_internal != "YES":
                print(t("common.cancelled"))
                sys.exit(0)
    except (CommandError, CommandNotFoundError, PlistParseError) as e:
        print(t("disk.cannot_check_disk_info", error=e))
        print(t("disk.cannot_check_disk_info_more"))


def confirm_disk_erasure(target_disk: str, num_partitions: int) -> bool:
    """
    Demande confirmation à l'utilisateur avant d'effacer le disque.

    Args:
        target_disk: Chemin du disque à effacer
        num_partitions: Nombre de partitions qui seront créées

    Returns:
        True si l'utilisateur confirme, False sinon
    """
    print(t("disk.erase_warning", target_disk=target_disk))
    print(t("disk.erase_warning_more", num_partitions=num_partitions))
    confirm = input(t("disk.erase_confirm"))
    if confirm != "YES":
        print(t("common.cancelled"))
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
    logger.info(t("disk.restore", target_disk=target_disk))
    try:
        unmount_disk(target_disk)

        restore_cmd = ["diskutil", "eraseDisk", "ExFAT", "USB_DISK", target_disk]

        progress_rules = [
            ("unmounting", 10, t("progress.unmounting_disk")),
            ("unmount", 10, t("progress.unmounting_disk")),
            ("erasing", 20, t("progress.erasing_partition")),
            ("formatting", 40, t("progress.formatting_disk")),
            ("creating", 60, t("progress.creating_partition")),
            ("mounting", 80, t("progress.mounting_volume")),
            ("mount", 80, t("progress.mounting_volume")),
            ("finished", 100, t("progress.done")),
            ("complete", 100, t("progress.done")),
        ]

        process, output_lines, progress_bar = run_command_with_progress(
            restore_cmd,
            t("progress.restore"),
            progress_rules,
            time_estimate_seconds=30,
        )

        process.wait()
        progress_bar.stop()

        read_remaining_output(process, output_lines)

        if process.returncode != 0:
            raise CommandError(restore_cmd, process.returncode, "\n".join(output_lines))

        if output_lines:
            logger.info(" ".join(output_lines))
        print(t("disk.restore_success"))
    except (CommandError, CommandNotFoundError) as e:
        print(t("disk.restore_fail", error=e))
        print(t("disk.restore_manual", target_disk=target_disk))
