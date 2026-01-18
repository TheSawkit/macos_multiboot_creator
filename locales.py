"""
Internationalisation (FR/EN) du projet.

- Utilisation: `from locales import t, init_i18n`
- `t(key, **vars)` retourne la traduction selon la langue courante.
- La langue est détectée via la locale système (FR/EN), sinon fallback EN.
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

Language = str  # "fr" | "en"

_CURRENT_LANG: Language = "en"


def detect_system_language() -> Language:
    """
    Détecte la langue système via les variables d'environnement
    """
    for env_var in ("LC_ALL", "LC_MESSAGES", "LANG"):
        lang = os.environ.get(env_var)
        if lang:
            lang = lang.lower()
            if lang.startswith("fr"):
                return "fr"
            if lang.startswith("en"):
                return "en"
    return "en"


def set_language(lang: Optional[str]) -> None:
    global _CURRENT_LANG
    if not lang:
        _CURRENT_LANG = "en"
        return
    lang_lc = lang.lower()
    if lang_lc.startswith("fr"):
        _CURRENT_LANG = "fr"
    elif lang_lc.startswith("en"):
        _CURRENT_LANG = "en"
    else:
        _CURRENT_LANG = "en"


def init_i18n() -> Language:
    set_language(detect_system_language())
    return _CURRENT_LANG


def get_language() -> Language:
    return _CURRENT_LANG


TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "fr": {
        "common.empty": "VIDE",
        "progress.restore": "Restauration",
        "progress.partitioning": "Partitionnement",
        "progress.installation": "Installation",
        "progress.unmounting_disk": "Démontage du disque...",
        "progress.creating_partition_table": "Création de la table de partition...",
        "progress.waiting_partitions": "Activation des partitions...",
        "progress.formatting_partitions": "Formatage des partitions...",
        "progress.mounting_volumes": "Montage des volumes...",
        "progress.erasing_partition": "Suppression de la partition...",
        "progress.formatting_disk": "Formatage du disque...",
        "progress.creating_partition": "Création de la partition...",
        "progress.mounting_volume": "Montage du volume...",
        "progress.done": "Terminé !",
        "progress.erasing_volume": "Effacement du volume...",
        "progress.copying_files": "Copie des fichiers...",
        "progress.installing": "Installation en cours...",
        "progress.installing_base_system": "Installation du système de base...",
        "progress.installing_packages": "Installation des packages...",
        # core/cli.py
        "cli.description": "Créer une clé USB multiboot pour macOS",
        "cli.debug_help": "Active le mode debug avec affichage des logs détaillés",
        "cli.app_dir_help": "Répertoire où chercher les installateurs macOS (par défaut: {app_dir})",
        # main.py
        "main.error": "❌ Erreur {error_type} : {error}",
        "main.error_details": "   Détails : {details}",
        "main.disk_partial_state": "\n⚠️  Le disque peut être dans un état partiel.",
        "main.disk_partial_state_more": "   Certaines partitions peuvent avoir été créées mais l'installation a échoué.",
        "main.success": "\n✅ Terminé ! Votre clé USB Multiboot est prête.",
        "main.interrupted": "\n❌ Interruption par l'utilisateur (Ctrl+C)",
        "main.start": "Démarrage du script multiboot macOS",
        "main.installers_found": "{count} installateur(s) trouvé(s)",
        # utils/commands.py
        "utils.invalid_choice": "Choix invalide.",
        "utils.too_many_attempts": "❌ Trop de tentatives échouées. Arrêt.",
        "utils.need_sudo_line1": "🔒 Ce script doit être lancé avec 'sudo'.",
        "utils.need_sudo_line2": "Exemple : sudo python3 main.py [--debug]\n",
        "utils.disk_partial": "⚠️  Le disque {target_disk} peut être dans un état partiel.",
        "utils.check_disk_state": "   Vérifiez l'état avec : diskutil list {target_disk}",
        "utils.check_disk_state_generic": "⚠️  Vérifiez l'état avec : diskutil list",
        # disk/detection.py
        "disk.search_error": "❌ Erreur lors de la recherche des disques : {error}",
        "disk.none_detected": "❌ Aucun disque externe détecté.",
        "disk.available_disks": "\n📀 Disques disponibles :",
        "disk.pick_target": "\n👉 Choisissez le disque cible (1-{max}) : ",
        "disk.invalid_range": "Choix invalide. Veuillez entrer un nombre entre 1 et {max}",
        "disk.warning_small": "\n⚠️  AVERTISSEMENT : Le disque fait {size_gb:.1f} GB",
        "disk.space_needed": "Espace nécessaire : {needed_gb:.1f} GB",
        "disk.space_continue_may_fail": "Le script continuera mais pourrait échouer si l'espace est insuffisant.",
        "disk.space_available": "\nEspace disponible : {size_gb:.1f} GB",
        "disk.space_remaining": "Espace restant : {remaining_gb:.1f} GB",
        "disk.cannot_check_space": "⚠️  Impossible de vérifier l'espace disque : {error}",
        "disk.space_may_be_insufficient": "Le script continuera mais l'espace pourrait être insuffisant.",
        # disk/management.py
        "disk.unmount_fail": "\n❌ Le disque {target_disk} ne peut pas être démonté.",
        "disk.proc_using": "   Le processus '{process_name}' (PID: {process_id}) utilise le disque.",
        "disk.proc_using_generic": "   Un processus utilise le disque.",
        "disk.solutions": "\n💡 Solutions possibles :",
        "disk.solution_1": "   1. Fermez toutes les applications qui utilisent le disque",
        "disk.solution_2": "   2. Fermez Finder si le disque y est ouvert",
        "disk.solution_3": "   3. Éjectez le disque depuis Finder (⌘+E)",
        "disk.solution_4_kill": "   4. Tuez le processus manuellement : sudo kill {process_id}",
        "disk.solution_5_wait": "   5. Attendez quelques secondes et réessayez",
        "disk.partitioning_blocked": "\n⚠️  Le partitionnement ne peut pas continuer tant que le disque est utilisé.",
        "disk.rerun_after_free": "   Après avoir libéré le disque, relancez le script.",
        "disk.unmount_warning": "\n⚠️  Avertissement : Impossible de démonter le disque {target_disk}",
        "disk.unmount_warning_more": "   Le script continuera mais le partitionnement pourrait échouer.",
        "disk.internal_warning": "⚠️ AVERTISSEMENT : Le disque {target_disk} est marqué comme interne.",
        "disk.internal_warning_more": "   Assurez-vous qu'il ne s'agit pas de votre disque système principal.",
        "disk.internal_confirm": "   Continuer quand même ? (tapez 'YES' pour confirmer) : ",
        "common.cancelled": "Annulé.",
        "disk.cannot_check_disk_info": "⚠️  Impossible de vérifier les informations du disque : {error}",
        "disk.cannot_check_disk_info_more": "   Le script continuera mais soyez prudent.",
        "disk.erase_warning": "\n⚠️  ATTENTION : Le disque {target_disk} va être TOTALEMENT EFFACÉ.",
        "disk.erase_warning_more": "   Il sera partitionné en {num_partitions} volumes pour les installateurs.",
        "disk.erase_confirm": "   Tapez 'YES' pour confirmer : ",
        "disk.restore_success": "\n✅ Disque restauré avec succès",
        "disk.restore_fail": "⚠️  Impossible de restaurer le disque : {error}",
        "disk.restore_manual": "Vous pouvez le faire manuellement avec : diskutil eraseDisk ExFAT <nom_du_disque> {target_disk}",
        # disk/partitioning.py
        "disk.partitioning": "\n🔨 Partitionnement du disque...",
        "disk.partition_last_remaining": "   📦 {name}: partition de {remaining}",
        "disk.partition_last_all": "   📦 {name}: partition (prend tout l'espace restant)",
        "disk.partition_size": "   📦 {name}: partition de {size}",
        "disk.partition_fail_in_use": "\n❌ Échec du partitionnement : le disque {target_disk} est utilisé par un processus",
        "disk.partition_fail": "❌ Échec du partitionnement : {error}",
        "disk.partition_error_details": "   Erreur : {details}",
        # installer/finder.py
        "installer.search_installers": "🔍 Recherche des installateurs dans {app_dir}...",
        "installer.dir_missing": "❌ Le répertoire {app_dir} n'existe pas.",
        "installer.not_a_dir": "❌ {app_dir} n'est pas un répertoire.",
        "installer.permission_denied": "❌ Permission refusée pour accéder à {app_dir}",
        "installer.multiple_found": "⚠️ Plusieurs installateurs trouvés pour {name}, utilisation de: {picked}",
        "installer.found": "✅ Trouvé : {name}",
        "installer.invalid_path": "   ⚠️  Chemin invalide pour {name}: {path}",
        "installer.none_found": "❌ Aucun installateur trouvé. Utilisez 'Mist' pour les télécharger d'abord.",
        "installer.download_mist": "\n📥 Télécharger Mist : https://github.com/ninxsoft/Mist/releases",
        "installer.size_summary": "\n📊 Résumé des tailles :",
        "installer.size_summary_line": "   • {name}: {size_gb:.2f} GB (+ {margin_mb} MB marge = {size_with_margin_gb:.2f} GB)",
        # installer/media.py
        "install_media.creating": "\n🚀 Création des médias d'installation...",
        "install_media.duration_hint": "⏳ Cela peut prendre 10-30 minutes selon la version de macOS",
        "install_media.tool_missing": "❌ Outil createinstallmedia introuvable pour {name}",
        "install_media.tool_expected": "   Chemin attendu : {path}",
        "install_media.tool_not_executable": "❌ L'outil createinstallmedia n'est pas exécutable pour {name}",
        "install_media.permission_check_fail": "❌ Impossible de vérifier les permissions de createinstallmedia pour {name}",
        "install_media.installing": "\n Installation de {name}...",
        "install_media.timeout_volume": "❌ Timeout : Le volume {volume} n'est pas monté après {seconds}s",
        "install_media.volume_not_found": "Volume non trouvé (nom attendu: {expected})",
        "install_media.error_for_installer": "❌ {msg} pour {name}",
        "install_media.volume_not_accessible": "❌ Le volume {vol_path} n'est pas accessible pour {name}",
        "install_media.volume_too_small": "   ❌ Volume trop petit : {size_mb:.1f} MB (attendu au moins {min_mb} MB)",
        "install_media.files_present": "   Fichiers présents : {items}",
        "install_media.seems_failed": "L'installation semble avoir échoué : aucun fichier d'installation valide trouvé sur le volume",
        "install_media.current_content": "   Contenu actuel du volume : {content}",
        "install_media.volume_path": "   Chemin du volume : {path}",
        "install_media.check_manually": "   Vérifiez manuellement avec : ls -la {path}",
        "install_media.success": "✅ {name} installé avec succès",
        "install_media.fail": "❌ Échec de l'installation de {name}",
        "install_media.return_code": "   Code de retour : {code}",
        "install_media.error_output": "   Erreur : {error_output}",
        "install_media.sigkill_help": "\n   💡 Causes possibles :\n      • Espace disque insuffisant sur la partition\n      • Volume corrompu ou inaccessible\n      • Problème de permissions\n      • Le processus a été interrompu par le système",
        "install_media.check_mounted_help": "\n   💡 Vérifiez que le volume est correctement monté et accessible",
    },
    "en": {
        "common.empty": "EMPTY",
        "progress.restore": "Restore",
        "progress.partitioning": "Partitioning",
        "progress.installation": "Installation",
        "progress.unmounting_disk": "Unmounting disk...",
        "progress.creating_partition_table": "Creating partition table...",
        "progress.waiting_partitions": "Activating partitions...",
        "progress.formatting_partitions": "Formatting partitions...",
        "progress.mounting_volumes": "Mounting volumes...",
        "progress.erasing_partition": "Erasing partition...",
        "progress.formatting_disk": "Formatting disk...",
        "progress.creating_partition": "Creating partition...",
        "progress.mounting_volume": "Mounting volume...",
        "progress.done": "Done!",
        "progress.erasing_volume": "Erasing volume...",
        "progress.copying_files": "Copying files...",
        "progress.installing": "Installing...",
        "progress.installing_base_system": "Installing base system...",
        "progress.installing_packages": "Installing packages...",
        # core/cli.py
        "cli.description": "Create a multiboot USB drive for macOS",
        "cli.debug_help": "Enable debug mode with detailed logs",
        "cli.app_dir_help": "Directory to search for macOS installers (default: {app_dir})",
        # main.py
        "main.error": "❌ {error_type} error: {error}",
        "main.error_details": "   Details: {details}",
        "main.disk_partial_state": "\n⚠️  The disk may be in a partial state.",
        "main.disk_partial_state_more": "   Some partitions may have been created but the installation failed.",
        "main.success": "\n✅ Done! Your Multiboot USB drive is ready.",
        "main.interrupted": "\n❌ Interrupted by user (Ctrl+C)",
        "main.start": "Starting macOS multiboot script",
        "main.installers_found": "{count} installer(s) found",
        # utils/commands.py
        "utils.invalid_choice": "Invalid choice.",
        "utils.too_many_attempts": "❌ Too many failed attempts. Exiting.",
        "utils.need_sudo_line1": "🔒 This script must be run with 'sudo'.",
        "utils.need_sudo_line2": "Example: sudo python3 main.py [--debug]\n",
        "utils.disk_partial": "⚠️  The disk {target_disk} may be in a partial state.",
        "utils.check_disk_state": "   Check state with: diskutil list {target_disk}",
        "utils.check_disk_state_generic": "⚠️  Check state with: diskutil list",
        # disk/detection.py
        "disk.search_error": "❌ Error while listing disks: {error}",
        "disk.none_detected": "❌ No external disk detected.",
        "disk.available_disks": "\n📀 Available disks:",
        "disk.pick_target": "\n👉 Choose the target disk (1-{max}): ",
        "disk.invalid_range": "Invalid choice. Please enter a number between 1 and {max}",
        "disk.warning_small": "\n⚠️  WARNING: Disk size is {size_gb:.1f} GB",
        "disk.space_needed": "Space needed: {needed_gb:.1f} GB",
        "disk.space_continue_may_fail": "The script will continue but may fail if space is insufficient.",
        "disk.space_available": "\nAvailable space: {size_gb:.1f} GB",
        "disk.space_remaining": "Remaining space: {remaining_gb:.1f} GB",
        "disk.cannot_check_space": "⚠️  Unable to check disk space: {error}",
        "disk.space_may_be_insufficient": "The script will continue but space may be insufficient.",
        # disk/management.py
        "disk.unmount_fail": "\n❌ Disk {target_disk} cannot be unmounted.",
        "disk.proc_using": "   Process '{process_name}' (PID: {process_id}) is using the disk.",
        "disk.proc_using_generic": "   A process is using the disk.",
        "disk.solutions": "\n💡 Possible fixes:",
        "disk.solution_1": "   1. Close any apps that are using the disk",
        "disk.solution_2": "   2. Close Finder if the disk is opened there",
        "disk.solution_3": "   3. Eject the disk from Finder (⌘+E)",
        "disk.solution_4_kill": "   4. Kill the process manually: sudo kill {process_id}",
        "disk.solution_5_wait": "   5. Wait a few seconds and try again",
        "disk.partitioning_blocked": "\n⚠️  Partitioning cannot continue while the disk is in use.",
        "disk.rerun_after_free": "   After freeing the disk, rerun the script.",
        "disk.unmount_warning": "\n⚠️  Warning: Unable to unmount disk {target_disk}",
        "disk.unmount_warning_more": "   The script will continue but partitioning may fail.",
        "disk.internal_warning": "⚠️ WARNING: Disk {target_disk} is marked as internal.",
        "disk.internal_warning_more": "   Make sure this is not your main system disk.",
        "disk.internal_confirm": "   Continue anyway? (type 'YES' to confirm): ",
        "common.cancelled": "Cancelled.",
        "disk.cannot_check_disk_info": "⚠️  Unable to check disk info: {error}",
        "disk.cannot_check_disk_info_more": "   The script will continue, but be careful.",
        "disk.erase_warning": "\n⚠️  WARNING: Disk {target_disk} will be COMPLETELY ERASED.",
        "disk.erase_warning_more": "   It will be partitioned into {num_partitions} volumes for the installers.",
        "disk.erase_confirm": "   Type 'YES' to confirm: ",
        "disk.restore_success": "\n✅ Disk restored successfully",
        "disk.restore_fail": "⚠️  Unable to restore disk: {error}",
        "disk.restore_manual": "You can do it manually with: diskutil eraseDisk ExFAT <disk_name> {target_disk}",
        # disk/partitioning.py
        "disk.partitioning": "\n🔨 Partitioning disk...",
        "disk.partition_last_remaining": "   📦 {name}: partition size {remaining}",
        "disk.partition_last_all": "   📦 {name}: last partition (takes remaining space)",
        "disk.partition_size": "   📦 {name}: partition size {size}",
        "disk.partition_fail_in_use": "\n❌ Partitioning failed: disk {target_disk} is in use by a process",
        "disk.partition_fail": "❌ Partitioning failed: {error}",
        "disk.partition_error_details": "   Error: {details}",
        # installer/finder.py
        "installer.search_installers": "🔍 Searching installers in {app_dir}...",
        "installer.dir_missing": "❌ Directory {app_dir} does not exist.",
        "installer.not_a_dir": "❌ {app_dir} is not a directory.",
        "installer.permission_denied": "❌ Permission denied while accessing {app_dir}",
        "installer.multiple_found": "⚠️ Multiple installers found for {name}, using: {picked}",
        "installer.found": "✅ Found: {name}",
        "installer.invalid_path": "   ⚠️  Invalid path for {name}: {path}",
        "installer.none_found": "❌ No installer found. Use 'Mist' to download them first.",
        "installer.download_mist": "\n📥 Download Mist: https://github.com/ninxsoft/Mist/releases",
        "installer.size_summary": "\n📊 Size summary:",
        "installer.size_summary_line": "   • {name}: {size_gb:.2f} GB (+ {margin_mb} MB margin = {size_with_margin_gb:.2f} GB)",
        # installer/media.py
        "install_media.creating": "\n🚀 Creating installation media...",
        "install_media.duration_hint": "⏳ This can take 10–30 minutes depending on macOS version",
        "install_media.tool_missing": "❌ createinstallmedia tool not found for {name}",
        "install_media.tool_expected": "   Expected path: {path}",
        "install_media.tool_not_executable": "❌ createinstallmedia is not executable for {name}",
        "install_media.permission_check_fail": "❌ Unable to check createinstallmedia permissions for {name}",
        "install_media.installing": "\n Installing {name}...",
        "install_media.timeout_volume": "❌ Timeout: volume {volume} was not mounted after {seconds}s",
        "install_media.volume_not_found": "Volume not found (expected name: {expected})",
        "install_media.error_for_installer": "❌ {msg} for {name}",
        "install_media.volume_not_accessible": "❌ Volume {vol_path} is not accessible for {name}",
        "install_media.volume_too_small": "   ❌ Volume too small: {size_mb:.1f} MB (expected at least {min_mb} MB)",
        "install_media.files_present": "   Files present: {items}",
        "install_media.seems_failed": "Installation seems to have failed: no valid installer files found on the volume",
        "install_media.current_content": "   Current volume content: {content}",
        "install_media.volume_path": "   Volume path: {path}",
        "install_media.check_manually": "   Check manually with: ls -la {path}",
        "install_media.success": "✅ {name} installed successfully",
        "install_media.fail": "❌ Installation failed for {name}",
        "install_media.return_code": "   Return code: {code}",
        "install_media.error_output": "   Error: {error_output}",
        "install_media.sigkill_help": "\n   💡 Possible causes:\n      • Not enough disk space on the partition\n      • Corrupted or inaccessible volume\n      • Permission issue\n      • The process was killed by the system",
        "install_media.check_mounted_help": "\n   💡 Check that the volume is properly mounted and accessible",
    },
}


def t(key: str, **kwargs: Any) -> str:
    """
    Traduit une clé vers la langue courante avec fallback en anglais.
    Supporte le formatage via `.format(**kwargs)`.
    """
    lang = _CURRENT_LANG
    template = TRANSLATIONS.get(lang, {}).get(key) or TRANSLATIONS["en"].get(key) or key
    try:
        return template.format(**kwargs)
    except Exception:
        return template
