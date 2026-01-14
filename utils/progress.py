"""
Gestion des barres de progression.
"""

import logging
import subprocess
import sys
import threading
import time
from typing import List, Tuple

logger = logging.getLogger(__name__)

_stdout_lock = threading.Lock()


class ProgressBar:
    """
    Gère une barre de progression animée avec pourcentage et message.
    """

    def __init__(self, operation_name: str, time_estimate_seconds: int = 60):
        """
        Initialise la barre de progression.

        Args:
            operation_name: Nom de l'opération (ex: "Installation", "Partitionnement")
            time_estimate_seconds: Estimation du temps total en secondes pour l'estimation basée sur le temps
        """
        self.operation_name = operation_name
        self.time_estimate = time_estimate_seconds
        self.progress_percent = [0]
        self.progress_message = ["Démarrage..."]
        self.start_time = time.time()
        self.animation_running = threading.Event()
        self.animation_running.set()
        self.progress_thread = None

    def start(self) -> None:
        """Démarre l'animation de progression."""

        def show_progress():
            """Affiche une animation de progression avec pourcentage."""
            chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
            i = 0
            last_length = 0
            while self.animation_running.is_set():
                char = chars[i % len(chars)]
                percent = self.progress_percent[0]
                message = self.progress_message[0]

                elapsed = time.time() - self.start_time
                if percent < 90 and elapsed > 5:
                    time_based_percent = min(
                        int((elapsed / self.time_estimate) * 90), 90
                    )
                    if time_based_percent > percent:
                        percent = time_based_percent
                        if message == "Démarrage...":
                            message = f"{self.operation_name} en cours..."

                display_message = (
                    message
                    if message != "Démarrage..."
                    else f"{self.operation_name} en cours..."
                )
                progress_text = f"   {char} {display_message} {percent}%"

                with _stdout_lock:
                    sys.stdout.write(
                        "\r" + " " * max(last_length, len(progress_text)) + "\r"
                    )
                    sys.stdout.write(progress_text)
                    sys.stdout.flush()
                    last_length = len(progress_text)

                i += 1
                time.sleep(0.1)

            with _stdout_lock:
                sys.stdout.write("\r" + " " * last_length + "\r")
                sys.stdout.flush()

        self.progress_thread = threading.Thread(target=show_progress, daemon=True)
        self.progress_thread.start()

    def stop(self) -> None:
        """Arrête l'animation de progression."""
        self.animation_running.clear()
        if self.progress_thread:
            self.progress_thread.join(timeout=0.5)
            with _stdout_lock:
                sys.stdout.write("\r" + " " * 100 + "\r")
                sys.stdout.flush()

    def update(self, percent: int, message: str) -> None:
        """
        Met à jour le pourcentage et le message de progression.

        Args:
            percent: Pourcentage (0-100)
            message: Message à afficher
        """
        self.progress_percent[0] = max(self.progress_percent[0], percent)
        self.progress_message[0] = message

    def parse_line(self, line: str, progress_rules: List[Tuple[str, int, str]]) -> None:
        """
        Parse une ligne de sortie et met à jour la progression selon les règles.

        Args:
            line: Ligne de sortie à parser
            progress_rules: Liste de tuples (keyword, percent, message) pour détecter les étapes
        """
        line_lower = line.lower()
        for keyword, percent, message in progress_rules:
            if keyword in line_lower:
                self.update(percent, message)
                break


def run_command_with_progress(
    cmd: List[str],
    operation_name: str,
    progress_rules: List[Tuple[str, int, str]],
    time_estimate_seconds: int = 60,
) -> Tuple[subprocess.Popen, List[str], ProgressBar]:
    """
    Exécute une commande avec une barre de progression.

    Args:
        cmd: Commande à exécuter
        operation_name: Nom de l'opération pour l'affichage
        progress_rules: Liste de tuples (keyword, percent, message) pour détecter les étapes
        time_estimate_seconds: Estimation du temps total en secondes

    Returns:
        Tuple contenant (process, output_lines, progress_bar)
    """
    progress_bar = ProgressBar(operation_name, time_estimate_seconds)
    progress_bar.start()

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    output_lines = []

    def read_output():
        """Lit la sortie du processus."""
        try:
            for line in process.stdout:
                if line:
                    line = line.strip()
                    output_lines.append(line)
                    progress_bar.parse_line(line, progress_rules)
        except Exception as e:
            logger.debug(f"Erreur lors de la lecture: {e}")

    output_thread = threading.Thread(target=read_output, daemon=True)
    output_thread.start()

    return process, output_lines, progress_bar
