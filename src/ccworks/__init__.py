# Source package initialization
from importlib.metadata import PackageNotFoundError, version as _dist_version

try:
    # Read the version from installed distribution metadata rather than keeping a
    # second copy here. pyproject.toml stays the single source of truth; a
    # hardcoded literal is exactly what let v0.1.1 ship while pyproject still
    # said 0.1.0.
    __version__ = _dist_version("ccworks")
except PackageNotFoundError:  # a source tree with no install
    __version__ = "0+unknown"

__all__ = ["__version__"]
