"""
Compatibility ASGI entrypoint.

Keeps older startup commands like `uvicorn app.main:app` working by
re-exporting the multi-tenant FastAPI application.
"""

from app.main_multitenant import app

