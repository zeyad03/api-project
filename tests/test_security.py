"""Tests for src/core/security.py – password hashing, JWT, dependencies."""

import pytest
from unittest.mock import MagicMock

from src.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_token,
    get_current_user,
    require_admin,
)
from src.core.exceptions import AdminRequiredError, InvalidTokenError
from src.models.user import TokenData


# ── Password hashing ────────────────────────────────────────────────────────
class TestPasswordHashing:
    def test_hash_returns_bcrypt_string(self):
        hashed = hash_password("password123")
        assert isinstance(hashed, str)
        assert hashed.startswith("$2b$")

    def test_verify_correct_password(self):
        hashed = hash_password("mypassword")
        assert verify_password("mypassword", hashed) is True

    def test_verify_wrong_password(self):
        hashed = hash_password("mypassword")
        assert verify_password("wrongpassword", hashed) is False


# ── JWT helpers ──────────────────────────────────────────────────────────────
class TestJWT:
    def test_create_and_decode_roundtrip(self):
        data = {"sub": "testuser", "user_id": "abc123", "is_admin": False}
        token = create_access_token(data)
        decoded = decode_token(token)
        assert isinstance(decoded, TokenData)
        assert decoded.sub == "testuser"
        assert decoded.user_id == "abc123"
        assert decoded.is_admin is False

    def test_decode_invalid_token_raises(self):
        with pytest.raises(InvalidTokenError):
            decode_token("not.a.valid.jwt")

    def test_create_token_does_not_mutate_input(self):
        data = {"sub": "u", "user_id": "id1", "is_admin": True}
        create_access_token(data)
        assert "exp" not in data  # copy was made internally


# ── FastAPI dependencies ─────────────────────────────────────────────────────
class TestDependencies:
    def test_get_current_user_returns_token_data(self):
        token = create_access_token(
            {"sub": "testuser", "user_id": "abc123", "is_admin": False}
        )
        request = MagicMock()
        result = get_current_user(request, token)
        assert result.sub == "testuser"

    def test_require_admin_passes_for_admin(self):
        admin = TokenData(sub="admin", user_id="id", is_admin=True, exp=9999999999.0)
        result = require_admin(admin)
        assert result.is_admin is True

    def test_require_admin_rejects_non_admin(self):
        user = TokenData(sub="user", user_id="id", is_admin=False, exp=9999999999.0)
        with pytest.raises(AdminRequiredError):
            require_admin(user)
