"""A Galaxy GA4GH WES client and CLI built on BioBlend's client layer.

The sibling ``gxy-wes`` project demonstrates the WES wire protocol with a
dependency-light ``requests`` wrapper. This project demonstrates the same flow
the way a production application would: by layering the WES endpoints on top of
BioBlend's :class:`~bioblend.galaxy.GalaxyInstance`, reusing its API-key
handling, request plumbing, and upload/history/job abstractions.

    uvx gxy-wes-bioblend service-info --galaxy-url http://localhost:8080
"""

__version__ = "0.2.0.dev0"

PROJECT_NAME = "gxy-wes-bioblend"
PROJECT_OWNER = "galaxyproject"

from .client import (  # noqa: E402
    connect,
    detect_workflow_type,
    WesClient,
    WesError,
)

__all__ = (
    "WesClient",
    "WesError",
    "connect",
    "detect_workflow_type",
    "__version__",
)
