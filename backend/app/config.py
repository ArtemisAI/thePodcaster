"""Application-wide configuration loader.

This module should:
1. Parse environment variables (DATABASE_URL, BROKER_URL, etc.).
2. Provide a singleton `Settings` object that other modules import.

Suggested implementation: use Pydantic's `BaseSettings` for type-safe
environment management.
"""

# TODO: implement Settings class using pydantic.BaseSettings
