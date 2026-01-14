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
from disk.detection import get_disk_info

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
                f"Les partitions sont trop grandes: {total_needed_gb:.2f} GB nécessaires, "
                f"{disk_size_gb:.2f} GB disponibles"
            )
            raise ValueError(
                f"Les partitions sont trop grandes pour le disque.\n"
                f"   Espace nécessaire (partitions fixes) : {total_needed_gb:.2f} GB\n"
                f"   Espace disponible : {disk_size_gb:.2f} GB\n"
                f"   Il faut au moins {total_needed_gb:.2f} GB pour les partitions fixes."
            )

        logger.info(
            f"Validation réussie: {total_needed_gb:.2f} GB nécessaires pour les partitions fixes, "
            f"{disk_size_gb:.2f} GB disponibles"
        )
    except (KeyError, TypeError) as e:
        logger.warning(f"Impossible de valider les tailles de partitions: {e}")


def partition_disk(target_disk: str, installers: List[InstallerInfo]) -> None:
    """
    Partitionne le disque en volumes séparés pour chaque installateur.

    Args:
        target_disk: Chemin du disque à partitionner
        installers: Liste des installateurs à installer

    Raises:
        CommandError: Si la commande de partitionnement échoue
        CommandNotFoundError: Si diskutil n'est pas trouvé
        ValueError: Si les tailles de partitions sont invalides
    """
    logger.info(f"Début du partitionnement du disque {target_disk}")
    print(t("disk.partitioning"))

    validate_partition_sizes(target_disk, installers)

    remaining_size_str = ""
    if len(installers) > 1:
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
                remaining_size_str = f"{remaining_mb:.0f}M"
            else:
                remaining_size_str = f"{remaining_gb:.1f}G"
        except (KeyError, TypeError) as e:
            logger.warning(f"Impossible de calculer l'espace restant: {e}")

    partition_cmd = ["diskutil", "partitionDisk", target_disk, "GPT"]

    for i, inst in enumerate(installers):
        partition_cmd.extend(["JHFS+", inst["volume"]])
        if i == len(installers) - 1:
            partition_cmd.append("0b")
            if remaining_size_str:
                logger.info(
                    f"{inst['name']}: dernière partition (espace restant: {remaining_size_str})"
                )
                print(
                    t(
                        "disk.partition_last_remaining",
                        name=inst["name"],
                        remaining=remaining_size_str,
                    )
                )
            else:
                logger.info(
                    f"{inst['name']}: dernière partition (prend tout l'espace restant)"
                )
                print(t("disk.partition_last_all", name=inst["name"]))
        else:
            partition_size = format_size_for_diskutil(inst["size_bytes"])
            partition_cmd.append(partition_size)
            logger.info(f"{inst['name']}: partition de {partition_size}")
            print(t("disk.partition_size", name=inst["name"], size=partition_size))

    logger.info(
        f"Exécution de la commande de partitionnement: {' '.join(partition_cmd)}"
    )

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

    try:
        process, output_lines, progress_bar = run_command_with_progress(
            partition_cmd,
            t("progress.partitioning"),
            progress_rules,
            time_estimate_seconds=60,
        )

        process.wait()
        progress_bar.stop()

        read_remaining_output(process, output_lines)

        if process.returncode != 0:
            error_output = "\n".join(output_lines)

            if (
                "in use by process" in error_output
                or "Couldn't unmount" in error_output
            ):
                from disk.management import _extract_process_info

                process_name, process_id = _extract_process_info(error_output)

                logger.error(
                    f"Échec du partitionnement: le disque est utilisé par un processus"
                )
                print(t("disk.partition_fail_in_use", target_disk=target_disk))

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
                if process_name and process_id:
                    print(
                        t("disk.solution_4_kill", process_id=process_id)
                    )
                print(t("disk.solution_5_wait"))
                print(t("disk.partitioning_blocked"))
                print(t("disk.rerun_after_free"))

            raise CommandError(partition_cmd, process.returncode, error_output)

        logger.info("Partitionnement terminé avec succès")
    except (CommandError, CommandNotFoundError) as e:
        error_already_displayed = False
        if isinstance(e, CommandError) and e.stderr:
            if "in use by process" in str(e.stderr) or "Couldn't unmount" in str(
                e.stderr
            ):
                error_already_displayed = True

        if not error_already_displayed:
            logger.error(f"Échec du partitionnement: {e}")
            print(t("disk.partition_fail", error=e))
            if isinstance(e, CommandError) and e.stderr:
                print(t("disk.partition_error_details", details=e.stderr))
        else:
            logger.error(f"Échec du partitionnement: {e}")
        raise
