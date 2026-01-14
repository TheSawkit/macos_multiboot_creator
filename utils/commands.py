"""
Fonctions utilitaires pour l'exécution de commandes shell.
"""

import os
import plistlib
import subprocess
import sys
from typing import Any, Callable, Dict, List, Optional, Tuple, Union


class CommandError(Exception):
    """Exception levée lorsqu'une commande shell échoue."""

    def __init__(self, cmd: List[str], returncode: int, stderr: Optional[str] = None):
        self.cmd = cmd
        self.returncode = returncode
        self.stderr = stderr
        super().__init__(f"Commande échouée: {' '.join(cmd)} (code: {returncode})")


class CommandNotFoundError(Exception):
    """Exception levée lorsqu'une commande n'est pas trouvée."""

    def __init__(self, cmd: str):
        self.cmd = cmd
        super().__init__(f"Commande introuvable: {cmd}")


class PlistParseError(Exception):
    """Exception levée lorsqu'une erreur survient lors du parsing PLIST."""

    def __init__(self, error: Exception):
        self.original_error = error
        super().__init__(f"Erreur de parsing PLIST: {error}")


def prompt_with_retry(
    prompt_text: str,
    validator: Callable[[str], Tuple[bool, Any]],
    error_message: str = "Choix invalide.",
    max_retries: int = 3,
) -> Any:
    """
    Demande une entrée à l'utilisateur avec possibilité de retry.

    Args:
        prompt_text: Texte à afficher à l'utilisateur
        validator: Fonction qui prend la valeur et retourne (success: bool, value: Any)
        error_message: Message d'erreur à afficher
        max_retries: Nombre maximum de tentatives

    Returns:
        La valeur validée

    Raises:
        SystemExit: Si toutes les tentatives échouent
    """
    for attempt in range(max_retries):
        try:
            choice = input(prompt_text)
            success, value = validator(choice)
            if success:
                return value
            print(error_message)
        except (ValueError, TypeError) as e:
            print(f"{error_message} ({e})")

    print(f"❌ Trop de tentatives échouées. Arrêt.")
    sys.exit(1)


def parse_plist(plist_data: Union[str, bytes]) -> Dict[str, Any]:
    """
    Parse une chaîne PLIST en dictionnaire Python.

    Args:
        plist_data: Données PLIST sous forme de string ou bytes

    Returns:
        Dictionnaire Python contenant les données PLIST

    Raises:
        PlistParseError: Si le parsing échoue
    """
    try:
        if isinstance(plist_data, str):
            return plistlib.loads(plist_data.encode("utf-8"))
        else:
            return plistlib.loads(plist_data)
    except (plistlib.InvalidFileException, ValueError, TypeError) as e:
        raise PlistParseError(e) from e


def run_command(cmd: List[str], capture: bool = True) -> Optional[str]:
    """
    Exécute une commande shell et retourne la sortie.

    Args:
        cmd: Liste des arguments de la commande
        capture: Si True, capture la sortie. Si False, affiche en direct.

    Returns:
        La sortie de la commande si capture=True, None sinon.

    Raises:
        CommandError: Si la commande échoue
        CommandNotFoundError: Si la commande n'est pas trouvée
    """
    try:
        result = subprocess.run(
            cmd,
            check=True,
            stdout=subprocess.PIPE if capture else None,
            stderr=subprocess.PIPE if capture else None,
            text=True,
        )
        return result.stdout.strip() if capture else None
    except subprocess.CalledProcessError as e:
        error_output = ""
        if capture:
            if e.stdout:
                error_output += e.stdout
            if e.stderr:
                if error_output:
                    error_output += "\n"
                error_output += e.stderr
        stderr = error_output.strip() if error_output else None
        raise CommandError(cmd, e.returncode, stderr) from e
    except FileNotFoundError as e:
        raise CommandNotFoundError(cmd[0]) from e


def check_root_privileges() -> None:
    """Vérifie que le script est exécuté avec les privilèges root."""
    import logging

    logger = logging.getLogger(__name__)
    if os.geteuid() != 0:
        logger.error("Le script doit être lancé avec sudo")
        print("🔒 Ce script doit être lancé avec 'sudo'.")
        print("Exemple : sudo python3 main.py [--debug]\n")
        sys.exit(1)


def handle_error_with_disk_info(
    error: Optional[Exception], target_disk: Optional[str]
) -> None:
    """
    Affiche un message d'erreur avec des informations sur l'état du disque.

    Args:
        error: L'exception qui s'est produite (optionnel, non utilisé actuellement)
        target_disk: Chemin du disque (peut être None si pas encore sélectionné)
    """
    if target_disk:
        print(f"⚠️  Le disque {target_disk} peut être dans un état partiel.")
        print(f"   Vérifiez l'état avec : diskutil list {target_disk}")
    else:
        print("⚠️  Vérifiez l'état avec : diskutil list")


def read_remaining_output(
    process: subprocess.Popen, output_lines: List[str], timeout: float = 1.0
) -> None:
    """
    Lit les lignes restantes de la sortie d'un processus après wait().

    Args:
        process: Processus subprocess.Popen
        output_lines: Liste où ajouter les lignes lues
        timeout: Timeout en secondes pour la communication
    """
    if not output_lines:
        try:
            remaining, _ = process.communicate(timeout=timeout)
            if remaining:
                for line in remaining.split("\n"):
                    if line.strip():
                        output_lines.append(line.strip())
        except subprocess.TimeoutExpired:
            pass
