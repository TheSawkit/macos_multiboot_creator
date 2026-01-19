"""
Gestion du partitionnement du disque.
"""

import logging
from typing import List

from core.config import BYTES_PER_GB, BYTES_PER_MB, InstallerInfo
from locales import t
from utils.commands import CommandError, CommandNotFoundError, read_remaining_output
from utils.progress import run_command_with_progress
from utils.size import (
    calculate_partition_size_bytes,
    format_size_for_diskutil,
)
from disk.detection import DISKUTIL_PATH, get_disk_info

logger = logging.getLogger(__name__)


def validate_partition_sizes(target_disk: str, installers: List[InstallerInfo]) -> None:
    """
    Valide que la somme des tailles de partitions ne dépasse pas la taille du disque.

    Args:
        target_disk: Chemin du disque
        installers: Liste des installateurs

    Raises:
        ValueError: Si les partitions sont trop grandes pour le disque
        CommandError: Si la récupération des infos du disque échoue
    """
    try:
        disk_info = get_disk_info(target_disk)
        disk_size_bytes = disk_info.get("TotalSize", 0)

        total_needed_bytes = sum(
            calculate_partition_size_bytes(inst["size_bytes"])
            for inst in installers[:-1]
        )

        disk_size_gb = disk_size_bytes / BYTES_PER_GB
        total_needed_gb = total_needed_bytes / BYTES_PER_GB

        if total_needed_bytes > disk_size_bytes:
            logger.error(
                t(
                    "disk.partition_fail_size_large",
                    total_needed_gb=total_needed_gb,
                    disk_size_gb=disk_size_gb,
                )
            )
            raise ValueError(
                t(
                    "disk.partition_fail_size_large",
                    total_needed_gb=total_needed_gb,
                    disk_size_gb=disk_size_gb,
                )
            )

        logger.info(
            t(
                "disk.partition_success_validate",
                total_needed_gb=total_needed_gb,
                disk_size_gb=disk_size_gb,
            )
        )
    except (KeyError, TypeError) as e:
        logger.warning(t("disk.partition_fail_validate", error=e))


def partition_disk(target_disk: str, installers: List[InstallerInfo]) -> None:
    """
    Partitionne le disque en volumes séparés pour chaque installateur.

    Orchestre trois phases :
    1. Préparation de la commande et calculs
    2. Exécution via diskutil
    3. Gestion fine des erreurs (notamment disque occupé)
    """
    print(t("disk.partitioning"))

    validate_partition_sizes(target_disk, installers)

    partition_cmd = _build_partition_command(target_disk, installers)

    try:
        _execute_partition_command(partition_cmd)
        logger.info(t("disk.partition_success"))

    except CommandError as e:
        _handle_partition_error(e, target_disk)


def _build_partition_command(
    target_disk: str, installers: List[InstallerInfo]
) -> List[str]:
    """Construit la liste des arguments pour la commande diskutil."""
    cmd = [DISKUTIL_PATH, "partitionDisk", target_disk, "GPT"]

    remaining_info = _get_remaining_space_info(target_disk, installers)

    for i, inst in enumerate(installers):
        is_last = i == len(installers) - 1

        if is_last:
            cmd.extend(["JHFS+", inst["volume"], "0b"])
            _log_last_partition(inst["name"], remaining_info)
        else:
            size_str = format_size_for_diskutil(inst["size_bytes"])
            cmd.extend(["JHFS+", inst["volume"], size_str])
            print(t("disk.partition_size", name=inst["name"], size=size_str))

    logger.info(f"{' '.join(cmd)}")
    return cmd


def _execute_partition_command(cmd: List[str]) -> None:
    """Exécute la commande diskutil avec une barre de progression."""
    progress_rules = [
        ("unmounting", 10, t("progress.unmounting_disk")),
        ("unmount", 10, t("progress.unmounting_disk")),
        ("creating partition", 20, t("progress.creating_partition_table")),
        ("waiting for partitions to activate", 40, t("progress.waiting_partitions")),
        ("formatting", 60, t("progress.formatting_partitions")),
        ("mounting", 80, t("progress.mounting_volumes")),
        ("mount", 80, t("progress.mounting_volumes")),
        ("finished", 100, t("progress.done")),
        ("complete", 100, t("progress.done")),
    ]

    process, output_lines, progress_bar = run_command_with_progress(
        cmd,
        t("progress.partitioning"),
        progress_rules,
        time_estimate_seconds=60,
    )

    process.wait()
    progress_bar.stop()
    read_remaining_output(process, output_lines)

    if process.returncode != 0:
        raise CommandError(cmd, process.returncode, "\n".join(output_lines))


def _handle_partition_error(e: CommandError, target_disk: str) -> None:
    """Analyse l'erreur pour fournir des conseils contextuels (disque occupé)."""
    error_output = e.stderr or ""

    if "in use by process" in error_output or "Couldn't unmount" in error_output:
        _suggest_solutions_for_busy_disk(target_disk, error_output)
    else:
        print(t("disk.partition_fail", error=e))
        if error_output:
            print(t("disk.partition_error_details", details=error_output))

    raise e


def _suggest_solutions_for_busy_disk(target_disk: str, error_output: str) -> None:
    """Affiche les solutions détaillées quand le disque est occupé."""
    from disk.management import _extract_process_info

    process_name, process_id = _extract_process_info(error_output)

    print(t("disk.partition_fail_in_use", target_disk=target_disk))

    if process_name and process_id:
        print(t("disk.proc_using", process_name=process_name, process_id=process_id))

    print(t("disk.solutions"))
    print(t("disk.solution_1"))
    print(t("disk.solution_2"))
    print(t("disk.solution_3"))

    if process_name and process_id:
        print(t("disk.solution_4_kill", process_id=process_id))

    print(t("disk.solution_5_wait"))
    print(t("disk.partitioning_blocked"))
    print(t("disk.rerun_after_free"))


def _get_remaining_space_info(target_disk: str, installers: List[InstallerInfo]) -> str:
    """
    Calcule l'espace restant estimé pour l'affichage.
    Retourne une chaîne vide si le calcul échoue ou n'est pas pertinent.
    """
    if len(installers) <= 1:
        return ""

    try:
        disk_info = get_disk_info(target_disk)
        disk_size_bytes = disk_info.get("TotalSize", 0)

        total_fixed_partitions_bytes = sum(
            calculate_partition_size_bytes(inst["size_bytes"])
            for inst in installers[:-1]
        )

        remaining_bytes = disk_size_bytes - total_fixed_partitions_bytes
        remaining_gb = remaining_bytes / BYTES_PER_GB

        if remaining_gb < 1:
            remaining_mb = remaining_bytes / BYTES_PER_MB
            return f"{remaining_mb:.0f}M"

        return f"{remaining_gb:.1f}G"
    except (KeyError, TypeError, Exception) as e:
        logger.warning(t("disk.remaining_space_fail", error=e))
        return ""


def _log_last_partition(name: str, remaining_info: str) -> None:
    """Gère l'affichage spécifique pour la dernière partition."""
    if remaining_info:
        print(t("disk.partition_last_remaining", name=name, remaining=remaining_info))
    else:
        print(t("disk.partition_last_all", name=name))
