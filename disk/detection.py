"""
Détection et sélection des disques externes.
"""

import logging
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

from core.config import BYTES_PER_GB, MAX_VOLUME_WAIT_TIME
from locales import t
from utils.commands import (
    CommandError,
    CommandNotFoundError,
    PlistParseError,
    parse_plist,
    prompt_with_retry,
    run_command,
)

logger = logging.getLogger(__name__)


def list_external_disks() -> List[Tuple[str, str]]:
    """
    Liste les disques physiques externes via diskutil info.

    Returns:
        Liste de tuples (device_path, description) pour chaque disque externe.
    """
    logger.info("Recherche des disques externes...")
    try:
        output = run_command(["diskutil", "list", "-plist"])
        data = parse_plist(output)
    except (CommandError, CommandNotFoundError, PlistParseError) as e:
        logger.error(f"Erreur lors de la recherche des disques: {e}")
        print(t("disk.search_error", error=e))
        sys.exit(1)

    external_disks = []
    VALID_PARTITION_SCHEMES = (
        "GUID_partition_scheme",
        "FDisk_partition_scheme",
        "Apple_partition_scheme",
    )

    for disk in data.get("AllDisksAndPartitions", []):
        dev_id = disk.get("DeviceIdentifier")
        if not dev_id:
            continue

        content = disk.get("Content", "")
        if content and content not in VALID_PARTITION_SCHEMES:
            continue

        is_mounted = bool(disk.get("MountPoint"))

        try:
            info_xml = run_command(["diskutil", "info", "-plist", dev_id])
            if not info_xml:
                continue
            info = parse_plist(info_xml)
        except (CommandError, CommandNotFoundError, PlistParseError):
            continue

        if (
            info.get("Ejectable")
            and not info.get("Internal")
            and info.get("WholeDisk", False)
        ):
            size_gb = info.get("TotalSize", 0) / BYTES_PER_GB
            name = info.get("MediaName", "Inconnu")
            mount_status = " (monté)" if is_mounted else ""
            external_disks.append(
                (f"/dev/{dev_id}", f"{name} ({size_gb:.1f} GB){mount_status}")
            )

    return external_disks


def select_disk(disks: List[Tuple[str, str]]) -> str:
    """
    Permet à l'utilisateur de sélectionner un disque parmi la liste.

    Args:
        disks: Liste des disques disponibles

    Returns:
        Chemin du disque sélectionné (ex: /dev/disk2)

    Raises:
        SystemExit: Si aucun disque disponible ou choix invalide
    """
    if not disks:
        logger.error("Aucun disque externe détecté")
        print(t("disk.none_detected"))
        sys.exit(1)

    print(t("disk.available_disks"))
    for i, (dev, desc) in enumerate(disks):
        print(f"   [{i+1}] {dev} - {desc}")

    def validate_choice(choice: str) -> Tuple[bool, str]:
        """Valide le choix de l'utilisateur."""
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(disks):
                return True, disks[idx][0]
            return False, ""
        except (ValueError, IndexError):
            return False, ""

    target_disk = prompt_with_retry(
        t("disk.pick_target", max=len(disks)),
        validate_choice,
        t("disk.invalid_range", max=len(disks)),
    )
    logger.info(f"Disque sélectionné: {target_disk}")
    return target_disk


def get_disk_info(target_disk: str) -> Dict[str, Any]:
    """
    Récupère les informations d'un disque.

    Args:
        target_disk: Chemin du disque (ex: /dev/disk2)

    Returns:
        Dictionnaire contenant les informations du disque

    Raises:
        CommandError: Si la commande diskutil échoue
        CommandNotFoundError: Si diskutil n'est pas trouvé
        PlistParseError: Si le parsing du plist échoue
    """
    disk_info_xml = run_command(["diskutil", "info", "-plist", target_disk])
    return parse_plist(disk_info_xml)


def check_disk_space(target_disk: str, needed_bytes: int) -> None:
    """
    Vérifie si le disque a suffisamment d'espace et affiche un résumé.

    Args:
        target_disk: Chemin du disque
        needed_bytes: Espace nécessaire en octets
    """
    try:
        disk_info = get_disk_info(target_disk)
        disk_size_gb = disk_info.get("TotalSize", 0) / BYTES_PER_GB
        needed_gb = needed_bytes / BYTES_PER_GB

        if disk_size_gb < needed_gb:
            logger.warning(
                f"Espace disque insuffisant: {disk_size_gb:.1f} GB disponible, {needed_gb:.1f} GB nécessaire"
            )
            print(t("disk.warning_small", size_gb=disk_size_gb))
            print(t("disk.space_needed", needed_gb=needed_gb))
            print(t("disk.space_continue_may_fail"))
        else:
            logger.info(
                f"Espace disque suffisant: {disk_size_gb:.1f} GB disponible, {needed_gb:.1f} GB nécessaire"
            )
            print(t("disk.space_available", size_gb=disk_size_gb))
            print(t("disk.space_needed", needed_gb=needed_gb))
            print(t("disk.space_remaining", remaining_gb=(disk_size_gb - needed_gb)))
    except (
        KeyError,
        ValueError,
        TypeError,
        CommandError,
        CommandNotFoundError,
        PlistParseError,
    ) as e:
        logger.warning(f"Impossible de vérifier l'espace disque: {e}")
        print(t("disk.cannot_check_space", error=e))
        print(t("disk.space_may_be_insufficient"))


def find_volume_path(expected_name: str, installer_name: str) -> Path:
    """
    Trouve le chemin réel d'un volume monté, même s'il a été renommé.

    Args:
        expected_name: Nom attendu du volume (ex: "INSTALL_ELCAPITAN")
        installer_name: Nom de l'installateur pour la recherche (ex: "OS X El Capitan")

    Returns:
        Path du volume trouvé

    Raises:
        FileNotFoundError: Si le volume n'est pas trouvé
    """
    expected_path = Path(f"/Volumes/{expected_name}")
    if expected_path.exists() and _is_volume_mounted(expected_path, expected_name):
        logger.info(f"Volume trouvé avec le nom attendu: {expected_path}")
        return expected_path

    logger.info(f"Recherche du volume pour {installer_name} dans /Volumes/...")
    volumes_dir = Path("/Volumes")

    if not volumes_dir.exists():
        raise FileNotFoundError("/Volumes")

    keywords = installer_name.lower().split()

    for vol_path in volumes_dir.iterdir():
        if not vol_path.is_dir():
            continue

        vol_name_lower = vol_path.name.lower()
        if expected_name.lower() in vol_name_lower:
            if _is_volume_mounted(vol_path, vol_path.name):
                logger.info(f"Volume trouvé par nom attendu: {vol_path}")
                return vol_path

        meaningful_keywords = [
            k for k in keywords if k not in ["os", "x", "macos", "install"]
        ]
        if meaningful_keywords:
            if any(kw in vol_name_lower for kw in meaningful_keywords):
                if _is_volume_mounted(vol_path, vol_path.name):
                    logger.info(f"Volume trouvé par mots-clés: {vol_path}")
                    return vol_path

    raise FileNotFoundError(
        f"{installer_name} (expected: {expected_name})"
    )


def wait_for_volume(volume_name: str, max_wait: int = MAX_VOLUME_WAIT_TIME) -> bool:
    """
    Attend qu'un volume soit monté et accessible.

    Args:
        volume_name: Nom du volume à attendre
        max_wait: Temps maximum d'attente en secondes

    Returns:
        True si le volume est monté et accessible, False si timeout
    """
    vol_path = Path(f"/Volumes/{volume_name}")
    wait_start = time.time()
    logger.info(f"Attente du montage du volume {volume_name}...")

    while True:
        elapsed_time = time.time() - wait_start
        if elapsed_time > max_wait:
            logger.error(
                f"Timeout: le volume {volume_name} n'est pas monté après {max_wait}s"
            )
            return False

        if vol_path.exists():
            if _is_volume_mounted(vol_path, volume_name):
                return True

        time.sleep(0.5)


def _is_volume_mounted(vol_path: Path, volume_name: str) -> bool:
    """
    Vérifie si un volume est monté et accessible.

    Args:
        vol_path: Chemin du volume (Path)
        volume_name: Nom du volume (pour le logging)

    Returns:
        True si le volume est monté et accessible
    """
    try:
        if not (vol_path.is_dir() and vol_path.exists()):
            return False

        result = subprocess.run(
            ["diskutil", "info", str(vol_path)],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0 and "Mounted" in result.stdout:
            logger.info(f"Volume {volume_name} monté avec succès")
            return True
    except (OSError, subprocess.TimeoutExpired):
        pass
    return False
