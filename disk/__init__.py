"""
Module disk - Gestion des disques et partitions.
"""

from .detection import (
    check_disk_space,
    find_volume_path,
    get_disk_info,
    list_external_disks,
    select_disk,
    wait_for_volume,
)
from .management import confirm_disk_erasure, restore_disk, unmount_disk, verify_disk_safety
from .partitioning import partition_disk

__all__ = [
    "check_disk_space",
    "confirm_disk_erasure",
    "find_volume_path",
    "get_disk_info",
    "list_external_disks",
    "partition_disk",
    "restore_disk",
    "select_disk",
    "unmount_disk",
    "verify_disk_safety",
    "wait_for_volume",
]
