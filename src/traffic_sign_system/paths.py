"""Repository-relative paths used by scripts and package modules."""

from pathlib import Path
from typing import Union


PACKAGE_ROOT = Path(__file__).resolve().parent
SRC_ROOT = PACKAGE_ROOT.parent
PROJECT_ROOT = SRC_ROOT.parent
DEFAULT_CONFIG_PATH = PACKAGE_ROOT / "config" / "config.yaml"


def project_path(path: Union[str, Path]) -> Path:
    """Resolve a config path from the project root unless it is already absolute."""
    candidate = Path(path)
    return candidate if candidate.is_absolute() else PROJECT_ROOT / candidate
