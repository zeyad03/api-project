"""Tests for src/core/security.py – passwords, JWT, dependencies, RBAC.

Category: **unit** – pure security-utility logic, no HTTP.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user,
    require_admin,
    require_role,
)
from src.core.exceptions import (
    AdminRequiredError,
    InsufficientRoleError,
    InvalidTokenError,
    TokenRevokedError,
)
from src.models.user import TokenData, UserRole

pytestmark = pytest.mark.unit


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
        data = {"sub": "testuser", "user_id": "abc123", "role": "user", "is_admin": False}
        token = create_access_token(data)
        decoded = decode_token(token)
        assert isinstance(decoded, TokenData)
        assert decoded.sub == "testuser"
        assert decoded.user_id == "abc123"
        assert decoded.role == "user"
        assert decoded.is_admin is False
        assert decoded.jti  # JTI should be populated

    def test_decode_invalid_token_raises(self):
        with pytest.raises(InvalidTokenError):
            decode_token("not.a.valid.jwt")

    def test_create_token_does_not_mutate_input(self):
        data = {"sub": "u", "user_id": "id1", "role": "admin", "is_admin": True}
        create_access_token(data)
        assert "exp" not in data
        assert "jti" not in data

    def test_each_token_has_unique_jti(self):
        data = {"sub": "u", "user_id": "id1", "role": "user", "is_admin": False}
        t1 = decode_token(create_access_token(data))
        t2 = decode_token(create_access_token(data))
        assert t1.jti != t2.jti


# ── Refresh token ────────────────────────────────────────────────────────────
class TestRefreshToken:
    def test_refresh_token_is_opaque_string(self):
        tok = create_refresh_token()
        assert isinstance(tok, str)
        assert len(tok) > 30  # 48-byte urlsafe ≈ 64 chars

    def test_refresh_tokens_are_unique(self):
        t1 = create_refresh_token()
        t2 = create_refresh_token()
        assert t1 != t2


# ── FastAPI dependencies ─────────────────────────────────────────────────────
class TestDependencies:
    @patch("src.core.security.is_token_blacklisted", new_callable=AsyncMock, return_value=False)
    @pytest.mark.asyncio
    async def test_get_current_user_returns_token_data(self, _bl):
        data = {"sub": "testuser", "user_id": "abc123", "role": "user", "is_admin": False}
        token = create_access_token(data)
        request = MagicMock()
        request.app.state.db = MagicMock()
        result = await get_current_user(request, token)
        assert result.sub == "testuser"

    @patch("src.core.security.is_token_blacklisted", new_callable=AsyncMock, return_value=True)
    @pytest.mark.asyncio
    async def test_get_current_user_rejects_blacklisted_token(self, _bl):
        data = {"sub": "testuser", "user_id": "abc123", "role": "user", "is_admin": False}
        token = create_access_token(data)
        request = MagicMock()
        request.app.state.db = MagicMock()
        with pytest.raises(TokenRevokedError):
            await get_current_user(request, token)

    def test_require_admin_passes_for_admin(self):
        admin = TokenData(
            sub="admin", user_id="id", role="admin",
            is_admin=True, jti="j", exp=9999999999.0,
        )
        result = require_admin(admin)
        assert result.is_admin is True

    def test_require_admin_rejects_non_admin(self):
        user = TokenData(
            sub="user", user_id="id", role="user",
            is_admin=False, jti="j", exp=9999999999.0,
        )
        with pytest.raises(AdminRequiredError):
            require_admin(user)


# ── Role-based access control ───────────────────────────────────────────────
class TestRBAC:
    @pytest.mark.asyncio
    async def test_require_role_allows_sufficient_role(self):
        dep = require_role(UserRole.MODERATOR)
        mod = TokenData(
            sub="mod", user_id="id", role="moderator",
            is_admin=False, jti="j", exp=9999999999.0,
        )
        result = await dep(mod)
        assert result.sub == "mod"

    @pytest.mark.asyncio
    async def test_require_role_allows_higher_role(self):
        dep = require_role(UserRole.MODERATOR)
        admin = TokenData(
            sub="admin", user_id="id", role="admin",
            is_admin=True, jti="j", exp=9999999999.0,
        )
        result = await dep(admin)
        assert result.is_admin is True

    @pytest.mark.asyncio
    async def test_require_role_rejects_insufficient_role(self):
        dep = require_role(UserRole.MODERATOR)
        user = TokenData(
            sub="user", user_id="id", role="user",
            is_admin=False, jti="j", exp=9999999999.0,
        )
        with pytest.raises(InsufficientRoleError):
            await dep(user)
