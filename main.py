#!/usr/bin/env python3
"""
Script pour créer une clé USB multiboot macOS.
Permet d'installer plusieurs versions de macOS sur un seul disque externe.
"""
import logging
import sys
from typing import Callable, Optional

from locales import init_i18n, t
from core import parse_arguments, setup_logging
from disk import (
    check_disk_space,
    confirm_disk_erasure,
    list_external_disks,
    partition_disk,
    restore_disk,
    select_disk,
    unmount_disk,
    verify_disk_safety,
)
from installer import (
    InstallationError,
    calculate_total_space_needed,
    create_install_media,
    display_size_summary,
    find_installers,
)
from utils import (
    CommandError,
    CommandNotFoundError,
    PlistParseError,
    check_root_privileges,
    handle_error_with_disk_info,
)

logger = logging.getLogger(__name__)


def _handle_error(
    error: Exception,
    error_type: str,
    target_disk: Optional[str],
    partitioning_started: bool,
    cleanup_func: Callable[[], None],
) -> None:
    """
    Gère les erreurs de manière centralisée.

    Args:
        error: L'exception qui s'est produite
        error_type: Type d'erreur pour le message
        target_disk: Chemin du disque cible (peut être None)
        partitioning_started: Si True, le partitionnement a commencé
        cleanup_func: Fonction de nettoyage à appeler si nécessaire
    """
    print(t("main.error", error_type=error_type, error=error))

    if isinstance(error, CommandError) and error.stderr:
        print(t("main.error_details", details=error.stderr))

    if partitioning_started:
        cleanup_func()

    if isinstance(error, InstallationError) and target_disk:
        print(t("main.disk_partial_state"))
        print(t("main.disk_partial_state_more"))

    handle_error_with_disk_info(error, target_disk)


def main():
    """Fonction principale du script."""
    init_i18n()
    args = parse_arguments()
    setup_logging(debug=args.debug)
    check_root_privileges()

    target_disk: Optional[str] = None
    installers = []
    partitioning_started = False

    def cleanup_disk_if_needed():
        """Nettoie le disque si le partitionnement a commencé."""
        if partitioning_started and target_disk:
            restore_disk(target_disk)

    try:
        logger.info(t("main.start"))
        installers = find_installers(app_dir=args.app_dir)
        logger.info(t("main.installers_found", count=len(installers)))

        disks = list_external_disks()
        target_disk = select_disk(disks)
        verify_disk_safety(target_disk)

        total_needed_bytes = calculate_total_space_needed(installers)
        display_size_summary(installers)
        check_disk_space(target_disk, total_needed_bytes)

        if not confirm_disk_erasure(target_disk, len(installers)):
            sys.exit(0)

        unmount_disk(target_disk)
        partitioning_started = True

        partition_disk(target_disk, installers)
        create_install_media(installers)

        print(t("main.success"))

    except KeyboardInterrupt:
        print(t("main.interrupted"))
        cleanup_disk_if_needed()
        handle_error_with_disk_info(None, target_disk)
        sys.exit(130)
    except (CommandError, CommandNotFoundError) as e:
        _handle_error(
            e, "de commande", target_disk, partitioning_started, cleanup_disk_if_needed
        )
        sys.exit(1)
    except PlistParseError as e:
        _handle_error(
            e,
            "de parsing PLIST",
            target_disk,
            partitioning_started,
            cleanup_disk_if_needed,
        )
        sys.exit(1)
    except ValueError as e:
        _handle_error(
            e,
            "de validation",
            target_disk,
            partitioning_started,
            cleanup_disk_if_needed,
        )
        sys.exit(1)
    except InstallationError as e:
        _handle_error(
            e,
            "d'installation",
            target_disk,
            partitioning_started,
            cleanup_disk_if_needed,
        )
        sys.exit(1)
    except Exception as e:
        logger.error(t("main.error_unexpected", error=e), exc_info=True)
        _handle_error(
            e, "inattendue", target_disk, partitioning_started, cleanup_disk_if_needed
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
