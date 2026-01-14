"""
Gestion de la création des médias d'installation.
"""

import logging
import subprocess
import time
from pathlib import Path
from typing import List

from core.config import (
    EXECUTABLE_PERMISSIONS,
    InstallerInfo,
    MAX_VOLUME_WAIT_TIME,
    MIN_VOLUME_SIZE_BYTES,
)
from disk.detection import find_volume_path, wait_for_volume
from utils.commands import read_remaining_output
from utils.progress import run_command_with_progress

logger = logging.getLogger(__name__)


class InstallationError(Exception):
    """Exception levée lorsqu'une erreur survient lors de l'installation."""

    def __init__(self, installer_name: str, message: str):
        self.installer_name = installer_name
        self.message = message
        super().__init__(
            f"Erreur lors de l'installation de {installer_name}: {message}"
        )


def _verify_installation_success(vol_path: Path) -> bool:
    """
    Vérifie que l'installation a réussi en cherchant des fichiers essentiels sur le volume.

    Args:
        vol_path: Chemin du volume à vérifier

    Returns:
        True si des fichiers d'installation sont trouvés, False sinon
    """
    if not vol_path.exists() or not vol_path.is_dir():
        return False

    expected_items = [
        "Applications",
        "System",
        "Library",
        "BaseSystem.dmg",
        "InstallESD.dmg",
        "Install macOS",
        "Install OS X",
    ]

    try:
        items = [item.name for item in vol_path.iterdir()]

        if not items:
            logger.warning(f"Le volume {vol_path} est vide")
            return False

        found_expected = False
        for expected in expected_items:
            if any(expected.lower() in item.lower() for item in items):
                logger.debug(f"Fichier d'installation trouvé : {expected}")
                found_expected = True
                break

        if found_expected:
            return True

        total_size = 0
        file_count = 0
        try:
            for item in vol_path.iterdir():
                if item.is_file():
                    total_size += item.stat().st_size
                    file_count += 1
                elif item.is_dir():
                    try:
                        for subitem in item.rglob("*"):
                            if subitem.is_file():
                                total_size += subitem.stat().st_size
                                file_count += 1
                                if file_count > 100:
                                    break
                    except (OSError, PermissionError):
                        pass
        except (OSError, PermissionError):
            pass

        if total_size < MIN_VOLUME_SIZE_BYTES:
            min_size_mb = MIN_VOLUME_SIZE_BYTES / (1024 * 1024)
            logger.error(
                f"Volume {vol_path} trop petit ({total_size / (1024*1024):.1f} MB). "
                f"Attendu au moins {min_size_mb} MB. Fichiers: {items}"
            )
            print(
                f"   ❌ Volume trop petit : {total_size / (1024*1024):.1f} MB (attendu au moins {min_size_mb} MB)"
            )
            print(f"   Fichiers présents : {items}")
            return False

        logger.warning(
            f"Structure du volume {vol_path} non standard. Taille: {total_size / (1024*1024):.1f} MB, Fichiers: {items[:5]}"
        )
        return True
    except (OSError, PermissionError) as e:
        logger.warning(f"Impossible de vérifier le contenu du volume {vol_path}: {e}")
        return False


def create_install_media(installers: List[InstallerInfo]) -> None:
    """
    Crée les médias d'installation pour chaque installateur sur leur partition respective.

    Args:
        installers: Liste des installateurs à installer
    """
    logger.info("Début de la création des médias d'installation")
    print("\n🚀 Création des médias d'installation...")
    print(f"⏳ Cela peut prendre 10-30 minutes selon la version de macOS")

    for inst in installers:
        app_path = Path(inst["path"])
        create_media_tool = app_path / "Contents/Resources/createinstallmedia"

        if not create_media_tool.exists():
            error_msg = f"Outil createinstallmedia introuvable: {create_media_tool}"
            logger.error(f"{error_msg} pour {inst['name']}")
            print(f"❌ Outil createinstallmedia introuvable pour {inst['name']}")
            print(f"   Chemin attendu : {create_media_tool}")
            raise InstallationError(inst["name"], error_msg)

        try:
            stat_info = create_media_tool.stat()
            if not (stat_info.st_mode & EXECUTABLE_PERMISSIONS):
                error_msg = "Outil createinstallmedia non exécutable"
                logger.error(f"{error_msg} pour {inst['name']}")
                print(
                    f"❌ L'outil createinstallmedia n'est pas exécutable pour {inst['name']}"
                )
                raise InstallationError(inst["name"], error_msg)
        except OSError:
            error_msg = "Impossible de vérifier les permissions de createinstallmedia"
            logger.error(f"{error_msg} pour {inst['name']}")
            print(f"❌ {error_msg} pour {inst['name']}")
            raise InstallationError(inst["name"], error_msg)

        logger.info(f"Installation de {inst['name']} sur {inst['volume']}...")
        print(f"\n Installation de {inst['name']}...")

        if not wait_for_volume(inst["volume"]):
            error_msg = f"Timeout: le volume {inst['volume']} n'est pas monté après {MAX_VOLUME_WAIT_TIME}s"
            logger.error(f"{error_msg} pour {inst['name']}")
            print(
                f"❌ Timeout : Le volume {inst['volume']} n'est pas monté après {MAX_VOLUME_WAIT_TIME}s"
            )
            raise InstallationError(inst["name"], error_msg)

        try:
            vol_path = find_volume_path(inst["volume"], inst["name"])
            logger.info(f"Volume réel trouvé: {vol_path}")
        except FileNotFoundError as e:
            error_msg = f"Volume non trouvé: {e}"
            logger.error(f"{error_msg} pour {inst['name']}")
            print(f"❌ {error_msg} pour {inst['name']}")
            raise InstallationError(inst["name"], error_msg)

        if not vol_path.exists() or not vol_path.is_dir():
            error_msg = f"Le volume {vol_path} n'est pas accessible"
            logger.error(f"{error_msg} pour {inst['name']}")
            print(f"❌ {error_msg} pour {inst['name']}")
            raise InstallationError(inst["name"], error_msg)

        flash_cmd = [
            str(create_media_tool),
            "--volume",
            str(vol_path),
            "--applicationpath",
            str(app_path),
            "--nointeraction",
        ]

        logger.info(f"Exécution de createinstallmedia pour {inst['name']}")

        progress_rules = [
            ("erasing", 5, "Effacement du volume..."),
            ("formatting", 5, "Effacement du volume..."),
            ("copying", 20, "Copie des fichiers..."),
            ("install", 40, "Installation en cours..."),
            ("base system", 60, "Installation du système de base..."),
            ("basesystem", 60, "Installation du système de base..."),
            ("packages", 75, "Installation des packages..."),
            ("complete", 100, "Terminé !"),
            ("done", 100, "Terminé !"),
            ("success", 100, "Terminé !"),
        ]

        try:
            process, output_lines, progress_bar = run_command_with_progress(
                flash_cmd,
                "Installation",
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

            if output_lines:
                output = "\n".join(output_lines)
                logger.debug(f"Sortie complète de createinstallmedia: {output}")
                important_lines = []
                for line in output_lines:
                    line_lower = line.lower()
                    if any(
                        keyword in line_lower
                        for keyword in [
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
                    ):
                        important_lines.append(line)

                if important_lines:
                    logger.info(f"Sortie de createinstallmedia pour {inst['name']}")
                    for line in important_lines[:10]:
                        logger.info(f"{line}")
                else:
                    logger.info(
                        f"Dernières lignes de createinstallmedia pour {inst['name']}"
                    )
                    for line in output_lines[-5:]:
                        logger.info(f"{line}")

            logger.debug("Attente de la synchronisation du système de fichiers...")
            time.sleep(2)

            verification_result = _verify_installation_success(vol_path)

            if not verification_result:
                logger.debug(
                    "Première vérification échouée, nouvelle tentative après 3 secondes..."
                )
                time.sleep(3)
                verification_result = _verify_installation_success(vol_path)

            if not verification_result:
                try:
                    actual_items = (
                        [item.name for item in vol_path.iterdir()]
                        if vol_path.exists()
                        else []
                    )
                    error_msg = f"L'installation semble avoir échoué : aucun fichier d'installation valide trouvé sur le volume"
                    logger.error(f"{error_msg} pour {inst['name']}")
                    print(f"❌ {error_msg} pour {inst['name']}")
                    print(
                        f"   Contenu actuel du volume : {actual_items if actual_items else 'VIDE'}"
                    )
                    print(f"   Chemin du volume : {vol_path}")
                    print(f"   Vérifiez manuellement avec : ls -la {vol_path}")
                    raise InstallationError(inst["name"], error_msg)
                except Exception as e:
                    error_msg = f"Impossible de vérifier le contenu du volume : {e}"
                    logger.error(f"{error_msg} pour {inst['name']}")
                    print(f"❌ {error_msg} pour {inst['name']}")
                    raise InstallationError(inst["name"], error_msg)

            logger.info(f"{inst['name']} installé avec succès pour {inst['volume']}")
            print(f"✅ {inst['name']} installé avec succès")
        except subprocess.CalledProcessError as e:
            error_output = "\n".join(output_lines) if output_lines else ""
            error_msg = f"Code de retour {e.returncode}"

            if e.returncode == -9:
                error_msg += " (SIGKILL - processus tué)"
                help_msg = (
                    "\n   💡 Causes possibles :\n"
                    "      • Espace disque insuffisant sur la partition\n"
                    "      • Volume corrompu ou inaccessible\n"
                    "      • Problème de permissions\n"
                    "      • Le processus a été interrompu par le système"
                )
            elif e.returncode == 1:
                help_msg = "\n   💡 Vérifiez que le volume est correctement monté et accessible"
            else:
                help_msg = ""

            if error_output:
                error_msg += f": {error_output}"

            logger.error(f"Échec de l'installation de {inst['name']}: {error_msg}")
            print(f"❌ Échec de l'installation de {inst['name']}")
            print(f"   Code de retour : {e.returncode}")
            if help_msg:
                print(help_msg)
            if error_output:
                print(f"   Erreur : {error_output}")
            raise InstallationError(inst["name"], error_msg) from e
