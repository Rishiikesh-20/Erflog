# backend/auth/__init__.py
"""
Authentication module for Career Flow AI
Handles JWT verification with Supabase
"""

from .dependencies import get_current_user

__all__ = ["get_current_user"]
