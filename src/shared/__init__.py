"""Shared configuration and utilities."""

from .config import (
    APP_PACKAGE_MAPPINGS,
    APP_NAME_TO_PACKAGE,
    get_app_name_from_package,
    get_package_from_app_name,
)

__all__ = [
    "APP_PACKAGE_MAPPINGS",
    "APP_NAME_TO_PACKAGE",
    "get_app_name_from_package",
    "get_package_from_app_name",
]
