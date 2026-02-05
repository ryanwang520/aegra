"""Unit tests for noop auth user_id extraction from headers"""

import sys

import pytest


def reload_auth_module():
    """Helper to reload the auth module with environment variables"""
    # Remove the module from sys.modules to force reload
    modules_to_remove = [
        key for key in sys.modules if key.startswith("agent_server.auth")
    ]
    for module in modules_to_remove:
        del sys.modules[module]

    # Reload the module
    import agent_server.auth as auth_module

    return auth_module


class TestNoopAuthUserIdExtraction:
    """Test user_id extraction from headers in noop authentication mode"""

    @pytest.mark.asyncio
    async def test_anonymous_user_without_headers(self, monkeypatch):
        """Test that anonymous user is returned when no X-User-ID header is present"""
        monkeypatch.setenv("AUTH_TYPE", "noop")

        auth_module = reload_auth_module()

        # Call the authenticate function
        headers = {}
        result = await auth_module.auth._authenticate_handler(headers)

        assert result["identity"] == "anonymous"
        assert result["display_name"] == "Anonymous User"
        assert result["is_authenticated"] is True

    @pytest.mark.asyncio
    async def test_user_id_from_header_lowercase(self, monkeypatch):
        """Test user_id extraction from x-user-id header (lowercase)"""
        monkeypatch.setenv("AUTH_TYPE", "noop")

        auth_module = reload_auth_module()

        headers = {"x-user-id": "user-12345"}
        result = await auth_module.auth._authenticate_handler(headers)

        assert result["identity"] == "user-12345"
        assert result["display_name"] == "user-12345"
        assert result["is_authenticated"] is True

    @pytest.mark.asyncio
    async def test_user_id_from_header_uppercase(self, monkeypatch):
        """Test user_id extraction from X-User-ID header (uppercase)"""
        monkeypatch.setenv("AUTH_TYPE", "noop")

        auth_module = reload_auth_module()

        headers = {"X-User-ID": "user-67890"}
        result = await auth_module.auth._authenticate_handler(headers)

        assert result["identity"] == "user-67890"
        assert result["display_name"] == "user-67890"
        assert result["is_authenticated"] is True

    @pytest.mark.asyncio
    async def test_user_id_from_bytes_header(self, monkeypatch):
        """Test user_id extraction from bytes headers"""
        monkeypatch.setenv("AUTH_TYPE", "noop")

        auth_module = reload_auth_module()

        headers = {b"x-user-id": b"user-bytes-123"}
        result = await auth_module.auth._authenticate_handler(headers)

        assert result["identity"] == "user-bytes-123"
        assert result["display_name"] == "user-bytes-123"
        assert result["is_authenticated"] is True

    @pytest.mark.asyncio
    async def test_empty_user_id_header(self, monkeypatch):
        """Test that empty user_id header falls back to anonymous"""
        monkeypatch.setenv("AUTH_TYPE", "noop")

        auth_module = reload_auth_module()

        headers = {"x-user-id": ""}
        result = await auth_module.auth._authenticate_handler(headers)

        # Empty string is falsy, should return anonymous
        assert result["identity"] == "anonymous"
        assert result["display_name"] == "Anonymous User"
        assert result["is_authenticated"] is True

    @pytest.mark.asyncio
    async def test_saas_user_id_scenario(self, monkeypatch):
        """Test realistic SaaS scenario with external user_id"""
        monkeypatch.setenv("AUTH_TYPE", "noop")

        auth_module = reload_auth_module()

        # Simulate a SaaS application passing user context
        headers = {
            "x-user-id": "saas-user-uuid-abcd-1234",
            "content-type": "application/json",
        }
        result = await auth_module.auth._authenticate_handler(headers)

        assert result["identity"] == "saas-user-uuid-abcd-1234"
        assert result["display_name"] == "saas-user-uuid-abcd-1234"
        assert result["is_authenticated"] is True

    @pytest.mark.asyncio
    async def test_header_priority_lowercase_first(self, monkeypatch):
        """Test that lowercase header is checked first"""
        monkeypatch.setenv("AUTH_TYPE", "noop")

        auth_module = reload_auth_module()

        # Both lowercase and uppercase present - should use first match
        headers = {"x-user-id": "user-lowercase", "X-User-ID": "user-uppercase"}
        result = await auth_module.auth._authenticate_handler(headers)

        # Should match whichever is found first in the iteration
        assert result["identity"] in ["user-lowercase", "user-uppercase"]
        assert result["is_authenticated"] is True

    @pytest.mark.asyncio
    async def test_additional_headers_ignored(self, monkeypatch):
        """Test that other headers don't interfere with user_id extraction"""
        monkeypatch.setenv("AUTH_TYPE", "noop")

        auth_module = reload_auth_module()

        headers = {
            "x-user-id": "user-999",
            "authorization": "Bearer some-token",
            "content-type": "application/json",
            "x-custom-header": "custom-value",
        }
        result = await auth_module.auth._authenticate_handler(headers)

        assert result["identity"] == "user-999"
        assert result["display_name"] == "user-999"
        assert result["is_authenticated"] is True
