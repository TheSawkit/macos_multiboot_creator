"""
Gestion de la création des médias d'installation.
"""

from gettext import install
import logging
import subprocess
import time
from pathlib import Path
from typing import List, Optional

from core.config import (
    EXECUTABLE_PERMISSIONS,
    InstallerInfo,
    MAX_VOLUME_WAIT_TIME,
    MIN_VOLUME_SIZE_BYTES,
)
from disk.detection import find_volume_path, wait_for_volume
from locales import t
from utils.commands import read_remaining_output
from utils.progress import run_command_with_progress

logger = logging.getLogger(__name__)


class InstallationError(Exception):
    """Exception levée lorsqu'une erreur survient lors de l'installation."""

    def __init__(self, installer_name: str, message: str):
        self.installer_name = installer_name
        self.message = message
        super().__init__(f"{installer_name}: {message}")


def _verify_installation_success(vol_path: Path) -> bool:
    """
    Vérifie que l'installation a réussi en cherchant des fichiers essentiels.

    Stratégie de validation :
    1. Le volume doit exister et être accessible
    2. Vérification par fichiers attendus (le plus fiable)
    3. Vérification par taille minimale (fallback)

    Returns:
        True si l'installation semble valide, False sinon
    """
    if not _is_volume_accessible(vol_path):
        return False

    items = _get_volume_items(vol_path)
    if items is None:
        return False

    if not items:
        logger.warning(t("install_media.volume_empty"))
        return False

    if _has_expected_installation_files(items):
        logger.debug(t("install_media.seems_success"))
        return True

    return _verify_by_volume_size(vol_path, items)


def _is_volume_accessible(vol_path: Path) -> bool:
    """Vérifie que le volume existe et est un dossier accessible."""
    return vol_path.exists() and vol_path.is_dir()


def _get_volume_items(vol_path: Path) -> Optional[List[str]]:
    """
    Récupère la liste des noms d'items à la racine du volume.

    Returns:
        Liste des noms d'items, ou None en cas d'erreur
    """
    try:
        return [item.name for item in vol_path.iterdir()]
    except (OSError, PermissionError) as e:
        logger.warning(
            t("install_media.volume_permission_error", vol_path=vol_path, error=e)
        )
        return None


def _has_expected_installation_files(items: List[str]) -> bool:
    """
    Vérifie si des fichiers/dossiers d'installation macOS sont présents.

    Args:
        items: Liste des noms d'items à vérifier

    Returns:
        True si au moins un fichier attendu est trouvé
    """
    expected_items = [
        "Applications",
        "System",
        "Library",
        "BaseSystem.dmg",
        "InstallESD.dmg",
        "Install macOS",
        "Install OS X",
    ]

    items_lower = [item.lower() for item in items]

    for expected in expected_items:
        if any(expected.lower() in item for item in items_lower):
            logger.debug(t("install_media.files_found", expected=expected))
            return True

    return False


def _verify_by_volume_size(vol_path: Path, items: List[str]) -> bool:
    """
    Vérifie l'installation par la taille du volume (méthode de fallback).

    Si aucun fichier attendu n'est trouvé, on vérifie que le volume
    contient suffisamment de données pour être une installation valide.
    """
    total_size = _calculate_volume_size(vol_path)

    if total_size < MIN_VOLUME_SIZE_BYTES:
        min_size_mb = MIN_VOLUME_SIZE_BYTES / (1024 * 1024)
        actual_size_mb = total_size / (1024 * 1024)

        logger.error(
            t(
                "install_media.volume_too_small",
                size_mb=actual_size_mb,
                min_mb=min_size_mb,
            )
            + " "
            + t("install_media.files_present", items=items)
        )
        print(
            t(
                "install_media.volume_too_small",
                size_mb=actual_size_mb,
                min_mb=min_size_mb,
            )
        )
        print(t("install_media.files_present", items=items))
        return False

    logger.warning(
        t(
            "install_media.volume_standard_warning",
            vol_path=vol_path,
            total_size=total_size,
            items=items,
        )
    )
    return True


def _calculate_volume_size(vol_path: Path, max_files: int = 100) -> int:
    """
    Calcule la taille totale approximative du volume.

    Pour éviter les calculs trop longs, on limite le comptage à max_files.
    Cette approximation suffit pour détecter les installations incomplètes.

    Args:
        vol_path: Chemin du volume à analyser
        max_files: Nombre maximum de fichiers à compter (évite les scans trop longs)

    Returns:
        Taille totale en octets
    """
    total_size = 0
    file_count = 0

    try:
        for item in vol_path.iterdir():
            if file_count >= max_files:
                logger.debug(t("install_media.files_limit", max_files=max_files))
                break

            try:
                if item.is_file():
                    total_size += item.stat().st_size
                    file_count += 1
                elif item.is_dir():
                    size, count = _calculate_directory_size(
                        item, max_files - file_count
                    )
                    total_size += size
                    file_count += count
            except (OSError, PermissionError) as e:
                logger.debug(
                    t("install_media.item_permission_error", item=item, error=e)
                )
                continue

    except (OSError, PermissionError) as e:
        logger.warning(t("install_media.calculate_size_error", path=vol_path, error=e))

    return total_size


def _calculate_directory_size(dir_path: Path, max_files: int) -> tuple[int, int]:
    """
    Calcule la taille d'un dossier de manière limitée.

    Returns:
        Tuple (taille_totale, nombre_fichiers)
    """
    total_size = 0
    file_count = 0

    try:
        for subitem in dir_path.rglob("*"):
            if file_count >= max_files:
                break

            try:
                if subitem.is_file():
                    total_size += subitem.stat().st_size
                    file_count += 1
            except (OSError, PermissionError):
                continue

    except (OSError, PermissionError) as e:
        logger.warning(t("install_media.calculate_size_error", path=dir_path, error=e))

    return total_size, file_count


def create_install_media(installers: List[InstallerInfo]) -> None:
    """Crée les médias d'installation pour chaque installateur."""
    print(t("install_media.creating"))
    print(t("install_media.duration_hint"))

    for inst in installers:
        try:
            _create_single_install_media(inst)
        except InstallationError:
            raise


def _create_single_install_media(inst: InstallerInfo) -> None:
    """Crée le média d'installation pour un installateur unique."""
    app_path = Path(inst["path"])
    create_media_tool = app_path / "Contents/Resources/createinstallmedia"

    _validate_createinstallmedia_tool(create_media_tool, inst["name"])

    vol_path = _prepare_volume(inst)

    _execute_createinstallmedia(create_media_tool, app_path, vol_path, inst)

    _verify_and_confirm_installation(vol_path, inst["name"])


def _validate_createinstallmedia_tool(tool_path: Path, installer_name: str) -> None:
    """Vérifie l'existence et les permissions de l'outil createinstallmedia."""
    if not tool_path.exists():
        _raise_install_error(
            installer_name,
            t("install_media.tool_missing", name=installer_name)
            + " "
            + t("install_media.tool_expected", path=tool_path),
            "install_media.tool_missing",
        )

    try:
        stat_info = tool_path.stat()
        if not (stat_info.st_mode & EXECUTABLE_PERMISSIONS):
            _raise_install_error(
                installer_name,
                "Outil createinstallmedia non exécutable",
                "install_media.tool_not_executable",
            )
    except OSError:
        _raise_install_error(
            installer_name,
            "Impossible de vérifier les permissions de createinstallmedia",
            "install_media.permission_check_fail",
        )


def _prepare_volume(inst: InstallerInfo) -> Path:
    """Attend et localise le volume cible."""
    print(t("install_media.installing", name=inst["name"]))

    if not wait_for_volume(inst["volume"]):
        _raise_install_error(
            inst["name"],
            t(
                "install_media.timeout_volume",
                volume=inst["volume"],
                seconds=MAX_VOLUME_WAIT_TIME,
            ),
            "install_media.timeout_volume",
            volume=inst["volume"],
            seconds=MAX_VOLUME_WAIT_TIME,
        )

    try:
        vol_path = find_volume_path(inst["volume"], inst["name"])
        logger.info(t("install_media.volume_found", vol_path=vol_path))
    except FileNotFoundError:
        error_msg = t("install_media.volume_not_found", expected=inst["volume"])
        print(t("install_media.error_for_installer", msg=error_msg, name=inst["name"]))
        raise InstallationError(inst["name"], error_msg)

    if not vol_path.exists() or not vol_path.is_dir():
        _raise_install_error(
            inst["name"],
            t(
                "install_media.volume_not_accessible",
                vol_path=vol_path,
                name=inst["name"],
            ),
            "install_media.volume_not_accessible",
            vol_path=vol_path,
        )

    return vol_path


def _execute_createinstallmedia(
    tool_path: Path, app_path: Path, vol_path: Path, inst: InstallerInfo
) -> None:
    """Execute createinstallmedia avec gestion de la progression."""
    flash_cmd = [
        str(tool_path),
        "--volume",
        str(vol_path),
        "--applicationpath",
        str(app_path),
        "--nointeraction",
    ]

    logger.info(t("install_media.tool_executable", {inst["name"]}))

    progress_rules = [
        ("erasing", 5, t("progress.erasing_volume")),
        ("formatting", 5, t("progress.erasing_volume")),
        ("copying", 20, t("progress.copying_files")),
        ("install", 40, t("progress.installing")),
        ("base system", 60, t("progress.installing_base_system")),
        ("basesystem", 60, t("progress.installing_base_system")),
        ("packages", 75, t("progress.installing_packages")),
        ("complete", 100, t("progress.done")),
        ("done", 100, t("progress.done")),
        ("success", 100, t("progress.done")),
    ]

    try:
        process, output_lines, progress_bar = run_command_with_progress(
            flash_cmd,
            t("progress.installation"),
            progress_rules,
            time_estimate_seconds=1200,
        )

        process.wait()
        progress_bar.stop()
        read_remaining_output(process, output_lines)

        if process.returncode != 0:
            raise subprocess.CalledProcessError(
                process.returncode, flash_cmd, "\n".join(output_lines)
            )

        _log_command_output(output_lines, inst["name"])

    except subprocess.CalledProcessError as e:
        _handle_subprocess_error(e, output_lines, inst["name"])


def _verify_and_confirm_installation(vol_path: Path, installer_name: str) -> None:
    """Vérifie que l'installation s'est bien déroulée."""
    logger.debug(t("install_media.installation_waiting"))
    time.sleep(2)

    if _verify_installation_success(vol_path):
        print(t("install_media.success", name=installer_name))
        return

    logger.debug(t("install_media.installation_verify_fail"))
    time.sleep(3)

    if _verify_installation_success(vol_path):
        print(t("install_media.success", name=installer_name))
        return

    _report_verification_failure(vol_path, installer_name)


def _log_command_output(output_lines: List[str], installer_name: str) -> None:
    """Log la sortie de createinstallmedia de manière intelligente."""
    if not output_lines:
        return

    output = "\n".join(output_lines)
    logger.debug({output})

    keywords = [
        "error",
        "fail",
        "success",
        "complete",
        "done",
        "copying",
        "erasing",
        "creating",
        "warning",
    ]

    important_lines = [
        line for line in output_lines if any(kw in line.lower() for kw in keywords)
    ]

    logger.info(t("install_media.tool_exit", installer_name=installer_name))

    if important_lines:
        for line in important_lines[:10]:
            logger.info(line)
    else:
        for line in output_lines[-5:]:
            logger.info(line)


def _handle_subprocess_error(
    error: subprocess.CalledProcessError, output_lines: List[str], installer_name: str
) -> None:
    """Gère les erreurs subprocess de manière structurée."""
    error_output = "\n".join(output_lines) if output_lines else ""
    error_msg = error.returncode

    help_messages = {
        -9: ("(SIGKILL - processus tué)", "install_media.sigkill_help"),
        1: ("", "install_media.check_mounted_help"),
    }

    suffix, help_key = help_messages.get(error.returncode, ("", ""))
    error_msg += f" {suffix}" if suffix else ""

    if error_output:
        error_msg += f": {error_output}"

    print(t("install_media.fail", name=installer_name, error=error.returncode))

    if help_key:
        print(t(help_key))

    if error_output:
        print(t("install_media.error_output", error_output=error_output))

    raise InstallationError(installer_name, error_msg) from error


def _report_verification_failure(vol_path: Path, installer_name: str) -> None:
    """Rapporte l'échec de vérification avec diagnostic."""
    try:
        actual_items = (
            [item.name for item in vol_path.iterdir()] if vol_path.exists() else []
        )
        error_msg = t("install_media.seems_failed")
        print(
            t("install_media.error_for_installer", msg=error_msg, name=installer_name)
        )
        print(
            t(
                "install_media.current_content",
                content=(actual_items if actual_items else t("common.empty")),
            )
        )
        print(t("install_media.volume_path", path=vol_path))
        print(t("install_media.check_manually", path=vol_path))
        raise InstallationError(installer_name, error_msg)
    except Exception as error_msg:
        print(
            t("install_media.error_for_installer", msg=error_msg, name=installer_name)
        )
        raise InstallationError(installer_name, error_msg)


def _raise_install_error(
    installer_name: str, error_msg: str, translation_key: str, **kwargs
) -> None:
    """Utilitaire pour lever une InstallationError avec logging cohérent."""
    logger.error(t(translation_key, name=installer_name, **kwargs))
    print(t(translation_key, name=installer_name, **kwargs))
    raise InstallationError(installer_name, error_msg)
