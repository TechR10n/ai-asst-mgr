"""Tests for the web dashboard module."""

from __future__ import annotations

import re
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from ai_asst_mgr.web import create_app


def _strip_ansi(text: str) -> str:
    """Remove ANSI escape codes from text."""
    ansi_escape = re.compile(r"\x1b\[[0-9;]*m")
    return ansi_escape.sub("", text)


class TestCreateApp:
    """Tests for the create_app factory function."""

    def test_create_app_returns_fastapi_instance(self) -> None:
        """Test that create_app returns a FastAPI app."""
        from fastapi import FastAPI

        app = create_app()
        assert isinstance(app, FastAPI)

    def test_create_app_has_title(self) -> None:
        """Test that the app has the correct title."""
        app = create_app()
        assert app.title == "AI Assistant Manager"

    def test_create_app_has_version(self) -> None:
        """Test that the app has a version."""
        app = create_app()
        assert app.version == "0.1.0"

    @patch("ai_asst_mgr.web.app.STATIC_DIR")
    def test_create_app_handles_missing_static_dir(self, mock_static_dir: MagicMock) -> None:
        """Test that create_app handles missing static directory gracefully."""
        from pathlib import Path

        # Mock STATIC_DIR to not exist
        mock_path = MagicMock(spec=Path)
        mock_path.exists.return_value = False
        mock_static_dir.__eq__ = lambda self, other: False
        mock_static_dir.exists.return_value = False

        # Create app - should not raise an error
        app = create_app()
        assert app is not None

        # Verify static files were not mounted (no route named "static")
        route_names = [route.name for route in app.routes if hasattr(route, "name")]
        assert "static" not in route_names


class TestPageRoutes:
    """Tests for HTML page routes."""

    @pytest.fixture
    def client(self) -> TestClient:
        """Create a test client."""
        app = create_app()
        return TestClient(app)

    @patch("ai_asst_mgr.web.services.get_installed_vendors")
    @patch("ai_asst_mgr.web.services.get_vendor_adapter")
    def test_dashboard_returns_200(
        self, mock_adapter: MagicMock, mock_vendors: MagicMock, client: TestClient
    ) -> None:
        """Test that dashboard returns 200 OK."""
        mock_vendors.return_value = ["claude"]
        adapter = MagicMock()
        adapter.info.name = "Claude"
        adapter.is_installed.return_value = True
        adapter.info.config_dir = MagicMock(exists=lambda: True)
        mock_adapter.return_value = adapter

        response = client.get("/")
        assert response.status_code == 200

    @patch("ai_asst_mgr.web.services.get_installed_vendors")
    @patch("ai_asst_mgr.web.services.get_vendor_adapter")
    def test_dashboard_contains_title(
        self, mock_adapter: MagicMock, mock_vendors: MagicMock, client: TestClient
    ) -> None:
        """Test that dashboard contains the page title."""
        mock_vendors.return_value = []
        mock_adapter.return_value = None

        response = client.get("/")
        assert b"Dashboard" in response.content

    @patch("ai_asst_mgr.web.services.get_installed_vendors")
    @patch("ai_asst_mgr.web.services.get_vendor_adapter")
    def test_agents_returns_200(
        self, mock_adapter: MagicMock, mock_vendors: MagicMock, client: TestClient
    ) -> None:
        """Test that agents page returns 200 OK."""
        mock_vendors.return_value = ["claude"]
        adapter = MagicMock()
        adapter.is_installed.return_value = True
        adapter.list_agents.return_value = ["agent1", "agent2"]
        mock_adapter.return_value = adapter

        response = client.get("/agents")
        assert response.status_code == 200

    @patch("ai_asst_mgr.web.services.get_installed_vendors")
    @patch("ai_asst_mgr.web.services.get_vendor_adapter")
    def test_agents_contains_title(
        self, mock_adapter: MagicMock, mock_vendors: MagicMock, client: TestClient
    ) -> None:
        """Test that agents page contains the page title."""
        mock_vendors.return_value = []
        mock_adapter.return_value = None

        response = client.get("/agents")
        assert b"Agents" in response.content

    @patch("ai_asst_mgr.web.services.get_installed_vendors")
    @patch("ai_asst_mgr.web.services.get_vendor_adapter")
    def test_review_returns_200(
        self, mock_adapter: MagicMock, mock_vendors: MagicMock, client: TestClient
    ) -> None:
        """Test that weekly review page returns 200 OK."""
        mock_vendors.return_value = ["claude"]
        adapter = MagicMock()
        adapter.info.name = "Claude"
        adapter.is_installed.return_value = True
        mock_adapter.return_value = adapter

        response = client.get("/review")
        assert response.status_code == 200

    @patch("ai_asst_mgr.web.services.get_installed_vendors")
    @patch("ai_asst_mgr.web.services.get_vendor_adapter")
    def test_review_contains_title(
        self, mock_adapter: MagicMock, mock_vendors: MagicMock, client: TestClient
    ) -> None:
        """Test that weekly review page contains the page title."""
        mock_vendors.return_value = []
        mock_adapter.return_value = None

        response = client.get("/review")
        assert b"Weekly Review" in response.content


class TestAPIRoutes:
    """Tests for JSON API routes."""

    @pytest.fixture
    def client(self) -> TestClient:
        """Create a test client."""
        app = create_app()
        return TestClient(app)

    @patch("ai_asst_mgr.web.services.get_installed_vendors")
    @patch("ai_asst_mgr.web.services.get_vendor_adapter")
    def test_api_stats_returns_json(
        self, mock_adapter: MagicMock, mock_vendors: MagicMock, client: TestClient
    ) -> None:
        """Test that /api/stats returns JSON."""
        mock_vendors.return_value = ["claude"]
        adapter = MagicMock()
        adapter.is_installed.return_value = True
        adapter.list_agents.return_value = ["agent1"]
        mock_adapter.return_value = adapter

        response = client.get("/api/stats")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"

    @patch("ai_asst_mgr.web.services.get_installed_vendors")
    @patch("ai_asst_mgr.web.services.get_vendor_adapter")
    def test_api_stats_contains_expected_fields(
        self, mock_adapter: MagicMock, mock_vendors: MagicMock, client: TestClient
    ) -> None:
        """Test that /api/stats contains expected fields."""
        mock_vendors.return_value = ["claude"]
        adapter = MagicMock()
        adapter.is_installed.return_value = True
        adapter.list_agents.return_value = ["agent1"]
        mock_adapter.return_value = adapter

        response = client.get("/api/stats")
        data = response.json()
        assert "total_vendors" in data
        assert "installed_vendors" in data
        assert "total_agents" in data
        assert "timestamp" in data

    @patch("ai_asst_mgr.web.services.get_installed_vendors")
    @patch("ai_asst_mgr.web.services.get_vendor_adapter")
    def test_api_vendors_returns_json(
        self, mock_adapter: MagicMock, mock_vendors: MagicMock, client: TestClient
    ) -> None:
        """Test that /api/vendors returns JSON."""
        mock_vendors.return_value = ["claude"]
        adapter = MagicMock()
        adapter.info.name = "Claude"
        adapter.is_installed.return_value = True
        adapter.info.config_dir = MagicMock(exists=lambda: True)
        mock_adapter.return_value = adapter

        response = client.get("/api/vendors")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"

    @patch("ai_asst_mgr.web.services.get_installed_vendors")
    @patch("ai_asst_mgr.web.services.get_vendor_adapter")
    def test_api_vendors_contains_vendor_list(
        self, mock_adapter: MagicMock, mock_vendors: MagicMock, client: TestClient
    ) -> None:
        """Test that /api/vendors contains vendor list."""
        mock_vendors.return_value = ["claude"]
        adapter = MagicMock()
        adapter.info.name = "Claude"
        adapter.is_installed.return_value = True
        adapter.info.config_dir = MagicMock(exists=lambda: True)
        mock_adapter.return_value = adapter

        response = client.get("/api/vendors")
        data = response.json()
        assert "vendors" in data
        assert "count" in data
        assert len(data["vendors"]) == 1

    @patch("ai_asst_mgr.web.services.get_installed_vendors")
    @patch("ai_asst_mgr.web.services.get_vendor_adapter")
    def test_api_agents_returns_json(
        self, mock_adapter: MagicMock, mock_vendors: MagicMock, client: TestClient
    ) -> None:
        """Test that /api/agents returns JSON."""
        mock_vendors.return_value = ["claude"]
        adapter = MagicMock()
        adapter.is_installed.return_value = True
        adapter.list_agents.return_value = ["agent1", "agent2"]
        mock_adapter.return_value = adapter

        response = client.get("/api/agents")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"

    @patch("ai_asst_mgr.web.services.get_installed_vendors")
    @patch("ai_asst_mgr.web.services.get_vendor_adapter")
    def test_api_agents_contains_expected_fields(
        self, mock_adapter: MagicMock, mock_vendors: MagicMock, client: TestClient
    ) -> None:
        """Test that /api/agents contains expected fields."""
        mock_vendors.return_value = ["claude"]
        adapter = MagicMock()
        adapter.is_installed.return_value = True
        adapter.list_agents.return_value = ["agent1", "agent2"]
        mock_adapter.return_value = adapter

        response = client.get("/api/agents")
        data = response.json()
        assert "agents_by_vendor" in data
        assert "total_agents" in data

    @patch("ai_asst_mgr.web.services.get_installed_vendors")
    @patch("ai_asst_mgr.web.services.get_coach")
    def test_api_coaching_returns_json(
        self, mock_coach: MagicMock, mock_vendors: MagicMock, client: TestClient
    ) -> None:
        """Test that /api/coaching returns JSON."""
        mock_vendors.return_value = ["claude"]
        coach = MagicMock()
        coach.get_insights.return_value = []
        mock_coach.return_value = coach

        response = client.get("/api/coaching")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"


class TestServices:
    """Tests for web service functions."""

    @patch("ai_asst_mgr.web.services.get_installed_vendors")
    @patch("ai_asst_mgr.web.services.get_vendor_adapter")
    def test_get_dashboard_data_returns_dict(
        self, mock_adapter: MagicMock, mock_vendors: MagicMock
    ) -> None:
        """Test that get_dashboard_data returns a dictionary."""
        from ai_asst_mgr.web.services import get_dashboard_data

        mock_vendors.return_value = []
        mock_adapter.return_value = None

        data = get_dashboard_data()
        assert isinstance(data, dict)
        assert "title" in data
        assert "vendors" in data

    @patch("ai_asst_mgr.web.services.get_installed_vendors")
    @patch("ai_asst_mgr.web.services.get_vendor_adapter")
    def test_get_agents_data_returns_dict(
        self, mock_adapter: MagicMock, mock_vendors: MagicMock
    ) -> None:
        """Test that get_agents_data returns a dictionary."""
        from ai_asst_mgr.web.services import get_agents_data

        mock_vendors.return_value = []
        mock_adapter.return_value = None

        data = get_agents_data()
        assert isinstance(data, dict)
        assert "title" in data
        assert "agents_by_vendor" in data

    @patch("ai_asst_mgr.web.services.get_installed_vendors")
    @patch("ai_asst_mgr.web.services.get_vendor_adapter")
    def test_get_weekly_review_data_returns_dict(
        self, mock_adapter: MagicMock, mock_vendors: MagicMock
    ) -> None:
        """Test that get_weekly_review_data returns a dictionary."""
        from ai_asst_mgr.web.services import get_weekly_review_data

        mock_vendors.return_value = []
        mock_adapter.return_value = None

        data = get_weekly_review_data()
        assert isinstance(data, dict)
        assert "title" in data
        assert "vendors" in data

    @patch("ai_asst_mgr.web.services.get_installed_vendors")
    @patch("ai_asst_mgr.web.services.get_vendor_adapter")
    def test_get_stats_data_returns_dict(
        self, mock_adapter: MagicMock, mock_vendors: MagicMock
    ) -> None:
        """Test that get_stats_data returns a dictionary."""
        from ai_asst_mgr.web.services import get_stats_data

        mock_vendors.return_value = []
        mock_adapter.return_value = None

        data = get_stats_data()
        assert isinstance(data, dict)
        assert "total_vendors" in data
        assert "installed_vendors" in data

    @patch("ai_asst_mgr.web.services.get_installed_vendors")
    @patch("ai_asst_mgr.web.services.get_vendor_adapter")
    def test_get_vendors_data_returns_dict(
        self, mock_adapter: MagicMock, mock_vendors: MagicMock
    ) -> None:
        """Test that get_vendors_data returns a dictionary."""
        from ai_asst_mgr.web.services import get_vendors_data

        mock_vendors.return_value = []
        mock_adapter.return_value = None

        data = get_vendors_data()
        assert isinstance(data, dict)
        assert "vendors" in data
        assert "count" in data

    @patch("ai_asst_mgr.web.services.get_installed_vendors")
    @patch("ai_asst_mgr.web.services.get_coach")
    def test_get_coaching_data_returns_dict(
        self, mock_coach: MagicMock, mock_vendors: MagicMock
    ) -> None:
        """Test that get_coaching_data returns a dictionary."""
        from ai_asst_mgr.web.services import get_coaching_data

        mock_vendors.return_value = []
        mock_coach.return_value = None

        data = get_coaching_data()
        assert isinstance(data, dict)
        assert "coaching" in data
        assert "timestamp" in data


class TestErrorHandling:
    """Tests for error handling."""

    @pytest.fixture
    def client(self) -> TestClient:
        """Create a test client."""
        app = create_app()
        return TestClient(app)

    def test_404_for_unknown_page(self, client: TestClient) -> None:
        """Test that unknown pages return 404."""
        response = client.get("/unknown-page")
        assert response.status_code == 404

    def test_404_for_unknown_api_endpoint(self, client: TestClient) -> None:
        """Test that unknown API endpoints return 404 JSON."""
        response = client.get("/api/unknown")
        assert response.status_code == 404
        assert response.headers["content-type"] == "application/json"

    def test_404_page_returns_html_error(self, client: TestClient) -> None:
        """Test that 404 for regular pages returns HTML with error message."""
        response = client.get("/unknown-page")
        assert response.status_code == 404
        assert b"404" in response.content
        assert b"Page not found" in response.content

    def test_404_api_returns_json_error(self, client: TestClient) -> None:
        """Test that 404 for API endpoints returns JSON error details."""
        response = client.get("/api/unknown-endpoint")
        assert response.status_code == 404
        data = response.json()
        assert data["error"] == "Not found"
        assert "/api/unknown-endpoint" in data["path"]

    @patch("ai_asst_mgr.web.routes.api.get_github_commits_data")
    def test_500_api_error_returns_json(self, mock_commits: MagicMock) -> None:
        """Test that 500 errors for API endpoints return JSON."""
        # Make the API endpoint raise an exception
        mock_commits.side_effect = Exception("Database error")

        # Create a client that doesn't raise server exceptions
        app = create_app()
        client = TestClient(app, raise_server_exceptions=False)

        response = client.get("/api/github/commits")
        assert response.status_code == 500
        assert response.headers["content-type"] == "application/json"
        data = response.json()
        assert data["error"] == "Internal server error"

    @patch("ai_asst_mgr.web.routes.pages.get_github_commits_data")
    def test_500_page_error_returns_html(self, mock_commits: MagicMock) -> None:
        """Test that 500 errors for regular pages return HTML."""
        # Make the page route raise an exception
        mock_commits.side_effect = Exception("Database error")

        # Create a client that doesn't raise server exceptions
        app = create_app()
        client = TestClient(app, raise_server_exceptions=False)

        response = client.get("/github")
        assert response.status_code == 500
        assert b"500" in response.content
        assert b"Internal server error" in response.content


class TestCLIServeCommand:
    """Tests for the serve CLI command."""

    def test_serve_command_exists(self) -> None:
        """Test that the serve command exists."""
        from typer.testing import CliRunner

        from ai_asst_mgr.cli import app

        runner = CliRunner()
        result = runner.invoke(app, ["serve", "--help"])
        output = _strip_ansi(result.output)
        assert result.exit_code == 0
        assert "Start the web dashboard server" in output

    def test_serve_command_has_host_option(self) -> None:
        """Test that serve command has --host option."""
        from typer.testing import CliRunner

        from ai_asst_mgr.cli import app

        runner = CliRunner()
        result = runner.invoke(app, ["serve", "--help"])
        output = _strip_ansi(result.output)
        assert "--host" in output

    def test_serve_command_has_port_option(self) -> None:
        """Test that serve command has --port option."""
        from typer.testing import CliRunner

        from ai_asst_mgr.cli import app

        runner = CliRunner()
        result = runner.invoke(app, ["serve", "--help"])
        output = _strip_ansi(result.output)
        assert "--port" in output

    def test_serve_command_has_reload_option(self) -> None:
        """Test that serve command has --reload option."""
        from typer.testing import CliRunner

        from ai_asst_mgr.cli import app

        runner = CliRunner()
        result = runner.invoke(app, ["serve", "--help"])
        output = _strip_ansi(result.output)
        assert "--reload" in output


class TestSessionRoutes:
    """Tests for session-related routes."""

    @pytest.fixture
    def client(self) -> TestClient:
        """Create a test client."""
        app = create_app()
        return TestClient(app)

    @patch("ai_asst_mgr.web.services._get_db")
    def test_sessions_page_returns_200(self, mock_db: MagicMock, client: TestClient) -> None:
        """Test that sessions page returns 200 OK."""
        mock_db.return_value = None  # No database initialized
        response = client.get("/sessions")
        assert response.status_code == 200

    @patch("ai_asst_mgr.web.services._get_db")
    def test_sessions_page_shows_not_initialized_message(
        self, mock_db: MagicMock, client: TestClient
    ) -> None:
        """Test that sessions page shows message when DB not initialized."""
        mock_db.return_value = None
        response = client.get("/sessions")
        assert b"Database Not Initialized" in response.content

    @patch("ai_asst_mgr.web.services._get_db")
    @patch("ai_asst_mgr.web.services.get_sync_status")
    def test_sessions_page_with_data(
        self,
        mock_sync_status: MagicMock,
        mock_db: MagicMock,
        client: TestClient,
    ) -> None:
        """Test sessions page with database data."""
        mock_db_instance = MagicMock()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        # Set up cursor returns for the queries
        mock_cursor.fetchall.side_effect = [
            [("/project1",), ("/project2",)],  # projects query
            [("sess1", "/project1", "2025-01-01", "2025-01-01", 100, 5)],  # sessions
        ]
        mock_cursor.fetchone.return_value = (10,)  # count query
        mock_conn.execute.return_value = mock_cursor
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_db_instance._connection.return_value = mock_conn
        mock_db.return_value = mock_db_instance

        mock_sync_status.return_value = {
            "database_sessions": 10,
            "database_events": 50,
            "last_synced_datetime": "2025-01-01T00:00:00",
        }

        response = client.get("/sessions")
        assert response.status_code == 200
        assert b"Session History" in response.content


class TestSessionAPIRoutes:
    """Tests for session API routes."""

    @pytest.fixture
    def client(self) -> TestClient:
        """Create a test client."""
        app = create_app()
        return TestClient(app)

    @patch("ai_asst_mgr.web.services._get_db")
    def test_sessions_api_no_db(self, mock_db: MagicMock, client: TestClient) -> None:
        """Test sessions API when database not initialized."""
        mock_db.return_value = None
        response = client.get("/api/sessions")
        assert response.status_code == 200
        data = response.json()
        assert data["db_initialized"] is False
        assert data["sessions"] == []

    @patch("ai_asst_mgr.web.services._get_db")
    def test_sessions_stats_api_no_db(self, mock_db: MagicMock, client: TestClient) -> None:
        """Test sessions stats API when database not initialized."""
        mock_db.return_value = None
        response = client.get("/api/sessions/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["db_initialized"] is False
        assert data["total_sessions"] == 0

    @patch("ai_asst_mgr.web.services._get_db")
    def test_session_detail_api_no_db(self, mock_db: MagicMock, client: TestClient) -> None:
        """Test session detail API when database not initialized."""
        mock_db.return_value = None
        response = client.get("/api/sessions/some-session-id")
        assert response.status_code == 200
        data = response.json()
        assert data["error"] == "Database not initialized"

    @patch("ai_asst_mgr.web.routes.api.VendorRegistry")
    @patch("ai_asst_mgr.web.routes.api.UniversalAgentManager")
    def test_agent_detail_api(
        self,
        mock_manager_class: MagicMock,
        mock_registry_class: MagicMock,
        client: TestClient,
    ) -> None:
        """Test agent detail API endpoint."""
        mock_registry = MagicMock()
        mock_registry.get_installed_vendors.return_value = {}
        mock_registry_class.return_value = mock_registry

        mock_manager = MagicMock()
        mock_manager.get_agent.return_value = None  # Agent not found
        mock_manager_class.return_value = mock_manager

        response = client.get("/api/agents/claude/test-agent")
        assert response.status_code == 200
        data = response.json()
        assert data["found"] is False


class TestSessionServices:
    """Tests for session-related services."""

    @patch("ai_asst_mgr.web.services._get_db")
    def test_get_sessions_data_no_db(self, mock_db: MagicMock) -> None:
        """Test get_sessions_data when database not initialized."""
        from ai_asst_mgr.web.services import get_sessions_data

        mock_db.return_value = None
        data = get_sessions_data()
        assert data["db_initialized"] is False
        assert data["sessions"] == []
        assert data["total_sessions"] == 0

    @patch("ai_asst_mgr.web.services._get_db")
    def test_get_session_detail_no_db(self, mock_db: MagicMock) -> None:
        """Test get_session_detail when database not initialized."""
        from ai_asst_mgr.web.services import get_session_detail

        mock_db.return_value = None
        data = get_session_detail("session-123")
        assert data["error"] == "Database not initialized"
        assert data["session"] is None

    @patch("ai_asst_mgr.web.services._get_db")
    def test_get_sessions_stats_no_db(self, mock_db: MagicMock) -> None:
        """Test get_sessions_stats when database not initialized."""
        from ai_asst_mgr.web.services import get_sessions_stats

        mock_db.return_value = None
        data = get_sessions_stats()
        assert data["db_initialized"] is False
        assert data["total_sessions"] == 0

    @patch("ai_asst_mgr.web.services._get_db")
    @patch("ai_asst_mgr.web.services.get_sync_status")
    def test_get_sessions_data_with_db(
        self, mock_sync_status: MagicMock, mock_db: MagicMock
    ) -> None:
        """Test get_sessions_data with database."""
        from ai_asst_mgr.web.services import get_sessions_data

        mock_db_instance = MagicMock()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        # Projects, sessions, count
        mock_cursor.fetchall.side_effect = [
            [("/project1",)],  # projects
            [("sess1", "/project1", "2025-01-01", "2025-01-01", 100, 5)],  # sessions
        ]
        mock_cursor.fetchone.return_value = (1,)  # count
        mock_conn.execute.return_value = mock_cursor
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_db_instance._connection.return_value = mock_conn
        mock_db.return_value = mock_db_instance

        mock_sync_status.return_value = {"database_events": 50}

        data = get_sessions_data()
        assert data["db_initialized"] is True
        assert len(data["sessions"]) == 1
        assert data["projects"] == ["/project1"]

    @patch("ai_asst_mgr.web.services._get_db")
    def test_get_session_detail_not_found(self, mock_db: MagicMock) -> None:
        """Test get_session_detail when session not found."""
        from ai_asst_mgr.web.services import get_session_detail

        mock_db_instance = MagicMock()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None  # Session not found
        mock_conn.execute.return_value = mock_cursor
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_db_instance._connection.return_value = mock_conn
        mock_db.return_value = mock_db_instance

        data = get_session_detail("nonexistent-session")
        assert data["error"] == "Session not found"
        assert data["session"] is None

    @patch("ai_asst_mgr.web.services._get_db")
    def test_get_session_detail_found(self, mock_db: MagicMock) -> None:
        """Test get_session_detail when session exists."""
        from ai_asst_mgr.web.services import get_session_detail

        mock_db_instance = MagicMock()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        # First call for session, second for events
        mock_cursor.fetchone.return_value = (
            "sess1",
            "/project1",
            "2025-01-01",
            "2025-01-01",
            100,
            5,
            "gemini",
        )
        mock_cursor.fetchall.return_value = [("message", "user", "{}", "2025-01-01T00:00:00")]
        mock_conn.execute.return_value = mock_cursor
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_db_instance._connection.return_value = mock_conn
        mock_db.return_value = mock_db_instance

        data = get_session_detail("sess1")
        assert data["session"] is not None
        assert data["session"]["session_id"] == "sess1"
        assert data["session"]["vendor_id"] == "gemini"
        assert len(data["events"]) == 1

    @patch("ai_asst_mgr.web.services._get_db")
    @patch("ai_asst_mgr.web.services.get_sync_status")
    def test_get_sessions_data_with_project_filter(
        self, mock_sync_status: MagicMock, mock_db: MagicMock
    ) -> None:
        """Test get_sessions_data with project filter."""
        from ai_asst_mgr.web.services import get_sessions_data

        mock_db_instance = MagicMock()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        # Projects, sessions, count
        mock_cursor.fetchall.side_effect = [
            [("/project1",), ("/project2",)],  # projects
            [("sess1", "/project1", "2025-01-01", "2025-01-01", 100, 5)],  # sessions
        ]
        mock_cursor.fetchone.return_value = (1,)  # count
        mock_conn.execute.return_value = mock_cursor
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_db_instance._connection.return_value = mock_conn
        mock_db.return_value = mock_db_instance

        mock_sync_status.return_value = {"database_events": 50}

        # Call with project filter
        data = get_sessions_data(project_filter="/project1")
        assert data["db_initialized"] is True
        assert data["current_filter"] == "/project1"

    @patch("ai_asst_mgr.web.services._get_db")
    @patch("ai_asst_mgr.web.services.get_sync_status")
    def test_get_sessions_stats_with_db(
        self, mock_sync_status: MagicMock, mock_db: MagicMock
    ) -> None:
        """Test get_sessions_stats with database initialized."""
        from ai_asst_mgr.web.services import get_sessions_stats

        mock_db_instance = MagicMock()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        # projects count, sessions count, events count
        mock_cursor.fetchone.side_effect = [(5,), (10,), (50,)]
        mock_conn.execute.return_value = mock_cursor
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_db_instance._connection.return_value = mock_conn
        mock_db.return_value = mock_db_instance

        mock_sync_status.return_value = {
            "database_sessions": 10,
            "database_events": 50,
            "last_synced_datetime": "2025-01-01T00:00:00",
        }

        # Default is gemini
        data = get_sessions_stats()
        assert data["db_initialized"] is True
        assert data["projects_count"] == 5
        assert data["total_sessions"] == 10
        assert data["total_messages"] == 50


class TestServiceHelpers:
    """Tests for service helper functions."""

    @patch("ai_asst_mgr.web.services.DEFAULT_DB_PATH")
    def test_get_db_path_not_exists(self, mock_path: MagicMock) -> None:
        """Test _get_db returns None when path doesn't exist."""
        from ai_asst_mgr.web.services import _get_db

        mock_path.exists.return_value = False
        result = _get_db()
        assert result is None

    @patch("ai_asst_mgr.web.services.DEFAULT_DB_PATH")
    @patch("ai_asst_mgr.web.services.DatabaseManager")
    def test_get_db_path_exists(self, mock_manager_class: MagicMock, mock_path: MagicMock) -> None:
        """Test _get_db returns DatabaseManager when path exists."""
        from ai_asst_mgr.web.services import _get_db

        mock_path.exists.return_value = True
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager

        result = _get_db()
        assert result is mock_manager
        mock_manager_class.assert_called_once_with(mock_path)

    def test_get_coach_found(self) -> None:
        """Test get_coach returns coach when vendor found."""
        from ai_asst_mgr.web.services import get_coach

        coach = get_coach("claude")
        assert coach is not None
        from ai_asst_mgr.coaches import ClaudeCoach

        assert isinstance(coach, ClaudeCoach)

    def test_get_coach_not_found(self) -> None:
        """Test get_coach returns None for unknown vendor."""
        from ai_asst_mgr.web.services import get_coach

        coach = get_coach("unknown-vendor")
        assert coach is None

    @patch("ai_asst_mgr.web.services.VendorRegistry")
    def test_get_installed_vendors(self, mock_registry_class: MagicMock) -> None:
        """Test get_installed_vendors returns vendor list."""
        from ai_asst_mgr.web.services import get_installed_vendors

        mock_registry = MagicMock()
        mock_registry.get_installed_vendors.return_value = {
            "claude": MagicMock(),
            "gemini": MagicMock(),
        }
        mock_registry_class.return_value = mock_registry

        vendors = get_installed_vendors()
        assert "claude" in vendors
        assert "gemini" in vendors

    @patch("ai_asst_mgr.web.services.VendorRegistry")
    def test_get_vendor_adapter(self, mock_registry_class: MagicMock) -> None:
        """Test get_vendor_adapter returns adapter."""
        from ai_asst_mgr.web.services import get_vendor_adapter

        mock_registry = MagicMock()
        mock_adapter = MagicMock()
        mock_registry.get_vendor.return_value = mock_adapter
        mock_registry_class.return_value = mock_registry

        adapter = get_vendor_adapter("claude")
        assert adapter is mock_adapter


class TestServiceExceptionHandling:
    """Tests for exception handling in services."""

    @patch("ai_asst_mgr.web.services.get_installed_vendors")
    @patch("ai_asst_mgr.web.services.get_vendor_adapter")
    def test_get_dashboard_data_adapter_none(
        self, mock_adapter: MagicMock, mock_vendors: MagicMock
    ) -> None:
        """Test get_dashboard_data when adapter is None."""
        from ai_asst_mgr.web.services import get_dashboard_data

        mock_vendors.return_value = ["unknown"]
        mock_adapter.return_value = None

        data = get_dashboard_data()
        assert len(data["vendors"]) == 0

    @patch("ai_asst_mgr.web.services.get_installed_vendors")
    @patch("ai_asst_mgr.web.services.get_vendor_adapter")
    def test_get_agents_data_adapter_none(
        self, mock_adapter: MagicMock, mock_vendors: MagicMock
    ) -> None:
        """Test get_agents_data when adapter is None."""
        from ai_asst_mgr.web.services import get_agents_data

        mock_vendors.return_value = ["unknown"]
        mock_adapter.return_value = None

        data = get_agents_data()
        assert "unknown" not in data["agents_by_vendor"]

    @patch("ai_asst_mgr.web.services.get_installed_vendors")
    @patch("ai_asst_mgr.web.services.get_vendor_adapter")
    def test_get_agents_data_adapter_not_installed(
        self, mock_adapter: MagicMock, mock_vendors: MagicMock
    ) -> None:
        """Test get_agents_data when adapter is not installed."""
        from ai_asst_mgr.web.services import get_agents_data

        mock_vendors.return_value = ["claude"]
        adapter = MagicMock()
        adapter.is_installed.return_value = False
        mock_adapter.return_value = adapter

        data = get_agents_data()
        assert "claude" not in data["agents_by_vendor"]

    @patch("ai_asst_mgr.web.services.get_installed_vendors")
    @patch("ai_asst_mgr.web.services.get_vendor_adapter")
    def test_get_agents_data_attribute_error(
        self, mock_adapter: MagicMock, mock_vendors: MagicMock
    ) -> None:
        """Test get_agents_data handles AttributeError."""
        from ai_asst_mgr.web.services import get_agents_data

        mock_vendors.return_value = ["claude"]
        adapter = MagicMock()
        adapter.is_installed.return_value = True
        adapter.list_agents.side_effect = AttributeError("No list_agents")
        mock_adapter.return_value = adapter

        data = get_agents_data()
        assert data["agents_by_vendor"]["claude"] == []

    @patch("ai_asst_mgr.web.services.get_installed_vendors")
    @patch("ai_asst_mgr.web.services.get_vendor_adapter")
    def test_get_agents_data_not_implemented(
        self, mock_adapter: MagicMock, mock_vendors: MagicMock
    ) -> None:
        """Test get_agents_data handles NotImplementedError."""
        from ai_asst_mgr.web.services import get_agents_data

        mock_vendors.return_value = ["claude"]
        adapter = MagicMock()
        adapter.is_installed.return_value = True
        adapter.list_agents.side_effect = NotImplementedError("Not supported")
        mock_adapter.return_value = adapter

        data = get_agents_data()
        assert data["agents_by_vendor"]["claude"] == []

    @patch("ai_asst_mgr.web.services.get_installed_vendors")
    @patch("ai_asst_mgr.web.services.get_vendor_adapter")
    def test_get_weekly_review_data_adapter_none(
        self, mock_adapter: MagicMock, mock_vendors: MagicMock
    ) -> None:
        """Test get_weekly_review_data when adapter is None."""
        from ai_asst_mgr.web.services import get_weekly_review_data

        mock_vendors.return_value = ["unknown"]
        mock_adapter.return_value = None

        data = get_weekly_review_data()
        assert len(data["vendors"]) == 0

    @patch("ai_asst_mgr.web.services.get_installed_vendors")
    @patch("ai_asst_mgr.web.services.get_vendor_adapter")
    def test_get_weekly_review_data_adapter_not_installed(
        self, mock_adapter: MagicMock, mock_vendors: MagicMock
    ) -> None:
        """Test get_weekly_review_data when adapter is not installed."""
        from ai_asst_mgr.web.services import get_weekly_review_data

        mock_vendors.return_value = ["claude"]
        adapter = MagicMock()
        adapter.info.name = "Claude"
        adapter.is_installed.return_value = False
        mock_adapter.return_value = adapter

        data = get_weekly_review_data()
        assert len(data["vendors"]) == 0

    @patch("ai_asst_mgr.web.services.get_installed_vendors")
    @patch("ai_asst_mgr.web.services.get_vendor_adapter")
    def test_get_stats_data_adapter_none(
        self, mock_adapter: MagicMock, mock_vendors: MagicMock
    ) -> None:
        """Test get_stats_data when adapter is None."""
        from ai_asst_mgr.web.services import get_stats_data

        mock_vendors.return_value = ["unknown"]
        mock_adapter.return_value = None

        data = get_stats_data()
        assert data["installed_vendors"] == 0
        assert data["total_agents"] == 0

    @patch("ai_asst_mgr.web.services.get_installed_vendors")
    @patch("ai_asst_mgr.web.services.get_vendor_adapter")
    def test_get_stats_data_adapter_not_installed(
        self, mock_adapter: MagicMock, mock_vendors: MagicMock
    ) -> None:
        """Test get_stats_data when adapter is not installed."""
        from ai_asst_mgr.web.services import get_stats_data

        mock_vendors.return_value = ["claude"]
        adapter = MagicMock()
        adapter.is_installed.return_value = False
        mock_adapter.return_value = adapter

        data = get_stats_data()
        assert data["installed_vendors"] == 0
        assert data["total_agents"] == 0

    @patch("ai_asst_mgr.web.services.get_installed_vendors")
    @patch("ai_asst_mgr.web.services.get_vendor_adapter")
    def test_get_stats_data_list_agents_exception(
        self, mock_adapter: MagicMock, mock_vendors: MagicMock
    ) -> None:
        """Test get_stats_data handles list_agents exception."""
        from ai_asst_mgr.web.services import get_stats_data

        mock_vendors.return_value = ["claude"]
        adapter = MagicMock()
        adapter.is_installed.return_value = True
        adapter.list_agents.side_effect = AttributeError("No list_agents")
        mock_adapter.return_value = adapter

        data = get_stats_data()
        assert data["total_agents"] == 0
        assert data["installed_vendors"] == 1

    @patch("ai_asst_mgr.web.services.get_installed_vendors")
    @patch("ai_asst_mgr.web.services.get_vendor_adapter")
    def test_get_vendors_data_adapter_none(
        self, mock_adapter: MagicMock, mock_vendors: MagicMock
    ) -> None:
        """Test get_vendors_data when adapter is None."""
        from ai_asst_mgr.web.services import get_vendors_data

        mock_vendors.return_value = ["unknown"]
        mock_adapter.return_value = None

        data = get_vendors_data()
        assert len(data["vendors"]) == 0

    @patch("ai_asst_mgr.web.services.get_installed_vendors")
    @patch("ai_asst_mgr.web.services.get_coach")
    def test_get_coaching_data_coach_none(
        self, mock_coach: MagicMock, mock_vendors: MagicMock
    ) -> None:
        """Test get_coaching_data when coach is None."""
        from ai_asst_mgr.web.services import get_coaching_data

        mock_vendors.return_value = ["unknown"]
        mock_coach.return_value = None

        data = get_coaching_data()
        assert len(data["coaching"]) == 0

    @patch("ai_asst_mgr.web.services.get_installed_vendors")
    @patch("ai_asst_mgr.web.services.get_coach")
    def test_get_coaching_data_exception(
        self, mock_coach: MagicMock, mock_vendors: MagicMock
    ) -> None:
        """Test get_coaching_data handles coach exception."""
        from ai_asst_mgr.web.services import get_coaching_data

        mock_vendors.return_value = ["claude"]
        coach = MagicMock()
        coach.get_insights.side_effect = AttributeError("No insights")
        mock_coach.return_value = coach

        data = get_coaching_data()
        assert len(data["coaching"]) == 1
        assert data["coaching"][0]["error"] == "Failed to get insights"


class TestAgentDetailAPI:
    """Tests for agent detail API endpoint."""

    @pytest.fixture
    def client(self) -> TestClient:
        """Create a test client."""
        app = create_app()
        return TestClient(app)

    @patch("ai_asst_mgr.web.routes.api.VendorRegistry")
    @patch("ai_asst_mgr.web.routes.api.UniversalAgentManager")
    def test_agent_detail_found(
        self,
        mock_manager_class: MagicMock,
        mock_registry_class: MagicMock,
        client: TestClient,
    ) -> None:
        """Test agent detail API when agent is found."""
        mock_registry = MagicMock()
        mock_registry.get_installed_vendors.return_value = {}
        mock_registry_class.return_value = mock_registry

        # Create mock agent
        from ai_asst_mgr.capabilities.manager import AgentType

        mock_agent = MagicMock()
        mock_agent.name = "test-agent"
        mock_agent.vendor_id = "claude"
        mock_agent.agent_type = AgentType.AGENT
        mock_agent.description = "Test agent"
        mock_agent.file_path = None
        mock_agent.content = "Test content"
        mock_agent.metadata = {}

        mock_manager = MagicMock()
        mock_manager.get_agent.return_value = mock_agent
        mock_manager_class.return_value = mock_manager

        response = client.get("/api/agents/claude/test-agent")
        assert response.status_code == 200
        data = response.json()
        assert data["found"] is True
        assert data["agent"]["name"] == "test-agent"


class TestGitHubPageRoutes:
    """Tests for GitHub page routes."""

    @pytest.fixture
    def client(self) -> TestClient:
        """Create a test client."""
        app = create_app()
        return TestClient(app)

    @patch("ai_asst_mgr.web.routes.pages.get_github_commits_data")
    def test_github_page_returns_200(self, mock_commits: MagicMock, client: TestClient) -> None:
        """Test that GitHub page returns 200 OK."""
        mock_commits.return_value = {
            "db_initialized": True,
            "commits": [],
            "repos": [],
            "stats": {
                "total_commits": 0,
                "ai_commits": 0,
                "ai_percentage": 0.0,
                "repos_tracked": 0,
            },
            "filters": {"vendor_id": None, "repo": None},
        }
        response = client.get("/github")
        assert response.status_code == 200

    @patch("ai_asst_mgr.web.routes.pages.get_github_commits_data")
    def test_github_page_with_vendor_filter(
        self, mock_commits: MagicMock, client: TestClient
    ) -> None:
        """Test GitHub page with vendor filter."""
        mock_commits.return_value = {
            "db_initialized": True,
            "commits": [],
            "repos": [],
            "stats": {
                "total_commits": 0,
                "ai_commits": 0,
                "ai_percentage": 0.0,
                "repos_tracked": 0,
            },
            "filters": {"vendor_id": "claude", "repo": None},
        }
        response = client.get("/github?vendor=claude")
        assert response.status_code == 200
        mock_commits.assert_called_with(vendor_id="claude", repo=None)

    @patch("ai_asst_mgr.web.routes.pages.get_github_commits_data")
    def test_github_page_with_repo_filter(
        self, mock_commits: MagicMock, client: TestClient
    ) -> None:
        """Test GitHub page with repo filter."""
        mock_commits.return_value = {
            "db_initialized": True,
            "commits": [],
            "repos": ["test-repo"],
            "stats": {
                "total_commits": 0,
                "ai_commits": 0,
                "ai_percentage": 0.0,
                "repos_tracked": 1,
            },
            "filters": {"vendor_id": None, "repo": "test-repo"},
        }
        response = client.get("/github?repo=test-repo")
        assert response.status_code == 200
        mock_commits.assert_called_with(vendor_id=None, repo="test-repo")


class TestGitHubServices:
    """Tests for GitHub-related service functions."""

    @patch("ai_asst_mgr.web.services._get_db")
    def test_get_github_summary_no_db(self, mock_db: MagicMock) -> None:
        """Test get_github_summary when database not initialized."""
        from ai_asst_mgr.web.services import get_github_summary

        mock_db.return_value = None
        data = get_github_summary()
        assert data["db_initialized"] is False
        assert data["total_commits"] == 0
        assert data["ai_commits"] == 0
        assert data["claude_commits"] == 0
        assert data["ai_percentage"] == 0.0
        assert data["repos_tracked"] == 0

    @patch("ai_asst_mgr.web.services._get_db")
    def test_get_github_summary_with_db(self, mock_db: MagicMock) -> None:
        """Test get_github_summary with database."""
        from ai_asst_mgr.web.services import get_github_summary

        mock_db_instance = MagicMock()
        mock_stats = MagicMock()
        mock_stats.total_commits = 100
        mock_stats.ai_attributed_commits = 50
        mock_stats.claude_commits = 30
        mock_stats.gemini_commits = 10
        mock_stats.openai_commits = 10
        mock_stats.ai_percentage = 50.0
        mock_stats.repos_tracked = 5
        mock_stats.first_commit = "2025-01-01"
        mock_stats.last_commit = "2025-01-31"
        mock_db_instance.get_github_stats.return_value = mock_stats
        mock_db.return_value = mock_db_instance

        data = get_github_summary()
        assert data["db_initialized"] is True
        assert data["total_commits"] == 100
        assert data["ai_commits"] == 50
        assert data["claude_commits"] == 30
        assert data["gemini_commits"] == 10
        assert data["openai_commits"] == 10
        assert data["ai_percentage"] == 50.0
        assert data["repos_tracked"] == 5
        assert data["first_commit"] == "2025-01-01"
        assert data["last_commit"] == "2025-01-31"

    @patch("ai_asst_mgr.web.services._get_db")
    def test_get_github_commits_data_no_db(self, mock_db: MagicMock) -> None:
        """Test get_github_commits_data when database not initialized."""
        from ai_asst_mgr.web.services import get_github_commits_data

        mock_db.return_value = None
        data = get_github_commits_data()
        assert data["db_initialized"] is False
        assert data["commits"] == []
        assert data["total_commits"] == 0
        assert data["repos"] == []

    @patch("ai_asst_mgr.web.services._get_db")
    def test_get_github_commits_data_with_db(self, mock_db: MagicMock) -> None:
        """Test get_github_commits_data with database."""
        from ai_asst_mgr.web.services import get_github_commits_data

        mock_db_instance = MagicMock()

        # Mock commit object
        mock_commit = MagicMock()
        mock_commit.sha = "abc123def456"
        mock_commit.repo = "test/repo"
        mock_commit.branch = "main"
        mock_commit.message = "Test commit\n\nWith details"
        mock_commit.author_name = "Test Author"
        mock_commit.author_email = "test@example.com"
        mock_commit.vendor_id = "claude"
        mock_commit.committed_at = "2025-01-01T12:00:00"

        mock_db_instance.get_github_commits.return_value = [mock_commit]
        mock_db_instance.get_github_repos.return_value = ["test/repo", "another/repo"]

        mock_stats = MagicMock()
        mock_stats.total_commits = 100
        mock_stats.ai_attributed_commits = 50
        mock_stats.ai_percentage = 50.0
        mock_stats.repos_tracked = 2
        mock_db_instance.get_github_stats.return_value = mock_stats

        mock_db.return_value = mock_db_instance

        data = get_github_commits_data(vendor_id="claude", repo="test/repo", limit=25, offset=10)

        assert data["db_initialized"] is True
        assert len(data["commits"]) == 1
        assert data["commits"][0]["sha"] == "abc123def456"
        assert data["commits"][0]["short_sha"] == "abc123d"
        assert data["commits"][0]["repo"] == "test/repo"
        assert data["commits"][0]["branch"] == "main"
        assert data["commits"][0]["message"] == "Test commit\n\nWith details"
        assert data["commits"][0]["subject"] == "Test commit"
        assert data["commits"][0]["author_name"] == "Test Author"
        assert data["commits"][0]["author_email"] == "test@example.com"
        assert data["commits"][0]["vendor_id"] == "claude"
        assert data["commits"][0]["committed_at"] == "2025-01-01T12:00:00"

        assert data["repos"] == ["test/repo", "another/repo"]
        assert data["stats"]["total_commits"] == 100
        assert data["stats"]["ai_commits"] == 50
        assert data["stats"]["ai_percentage"] == 50.0
        assert data["stats"]["repos_tracked"] == 2

        assert data["filters"]["vendor_id"] == "claude"
        assert data["filters"]["repo"] == "test/repo"

        # Verify the db methods were called with correct parameters
        mock_db_instance.get_github_commits.assert_called_once_with(
            vendor_id="claude", repo="test/repo", limit=25, offset=10
        )
        mock_db_instance.get_github_repos.assert_called_once()
        mock_db_instance.get_github_stats.assert_called_once()


class TestGitHubAPIRoutes:
    """Tests for GitHub API routes."""

    @pytest.fixture
    def client(self) -> TestClient:
        """Create a test client."""
        app = create_app()
        return TestClient(app)

    @patch("ai_asst_mgr.web.routes.api.get_github_summary")
    def test_api_github_stats_returns_200(
        self, mock_summary: MagicMock, client: TestClient
    ) -> None:
        """Test that /api/github/stats returns 200 OK."""
        mock_summary.return_value = {
            "db_initialized": True,
            "total_commits": 100,
            "ai_commits": 50,
            "ai_percentage": 50.0,
            "repos_tracked": 5,
        }
        response = client.get("/api/github/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["total_commits"] == 100
        assert data["ai_percentage"] == 50.0

    @patch("ai_asst_mgr.web.routes.api.get_github_commits_data")
    def test_api_github_commits_returns_200(
        self, mock_commits: MagicMock, client: TestClient
    ) -> None:
        """Test that /api/github/commits returns 200 OK."""
        mock_commits.return_value = {
            "db_initialized": True,
            "commits": [
                {
                    "sha": "abc123",
                    "short_sha": "abc1234",
                    "repo": "test/repo",
                    "message": "Test commit",
                    "vendor_id": "claude",
                }
            ],
            "repos": ["test/repo"],
            "stats": {"total_commits": 1, "ai_commits": 1},
        }
        response = client.get("/api/github/commits")
        assert response.status_code == 200
        data = response.json()
        assert len(data["commits"]) == 1

    @patch("ai_asst_mgr.web.routes.api.get_github_commits_data")
    def test_api_github_commits_with_vendor_filter(
        self, mock_commits: MagicMock, client: TestClient
    ) -> None:
        """Test /api/github/commits with vendor filter."""
        mock_commits.return_value = {
            "db_initialized": True,
            "commits": [],
            "repos": [],
            "stats": {},
        }
        response = client.get("/api/github/commits?vendor=claude")
        assert response.status_code == 200
        mock_commits.assert_called_with(vendor_id="claude", repo=None, limit=50, offset=0)

    @patch("ai_asst_mgr.web.routes.api.get_github_commits_data")
    def test_api_github_commits_with_pagination(
        self, mock_commits: MagicMock, client: TestClient
    ) -> None:
        """Test /api/github/commits with pagination parameters."""
        mock_commits.return_value = {
            "db_initialized": True,
            "commits": [],
            "repos": [],
            "stats": {},
        }
        response = client.get("/api/github/commits?limit=25&offset=50")
        assert response.status_code == 200
        mock_commits.assert_called_with(vendor_id=None, repo=None, limit=25, offset=50)
