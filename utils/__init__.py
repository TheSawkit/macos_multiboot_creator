"""
Module utils - Fonctions utilitaires.
"""

from .commands import (
    CommandError,
    CommandNotFoundError,
    PlistParseError,
    check_root_privileges,
    handle_error_with_disk_info,
    parse_plist,
    prompt_with_retry,
    read_remaining_output,
    run_command,
)
from .progress import ProgressBar, run_command_with_progress
from .size import (
    calculate_partition_size_bytes,
    calculate_size_with_margin,
    format_size_for_diskutil,
    get_directory_size,
)

__all__ = [
    "CommandError",
    "CommandNotFoundError",
    "PlistParseError",
    "ProgressBar",
    "calculate_partition_size_bytes",
    "calculate_size_with_margin",
    "check_root_privileges",
    "format_size_for_diskutil",
    "get_directory_size",
    "handle_error_with_disk_info",
    "parse_plist",
    "prompt_with_retry",
    "read_remaining_output",
    "run_command",
    "run_command_with_progress",
]
