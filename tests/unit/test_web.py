"""Tests for the web dashboard module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from ai_asst_mgr.web import create_app


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


class TestCLIServeCommand:
    """Tests for the serve CLI command."""

    def test_serve_command_exists(self) -> None:
        """Test that the serve command exists."""
        from typer.testing import CliRunner

        from ai_asst_mgr.cli import app

        runner = CliRunner()
        result = runner.invoke(app, ["serve", "--help"])
        assert result.exit_code == 0
        assert "Start the web dashboard server" in result.output

    def test_serve_command_has_host_option(self) -> None:
        """Test that serve command has --host option."""
        from typer.testing import CliRunner

        from ai_asst_mgr.cli import app

        runner = CliRunner()
        result = runner.invoke(app, ["serve", "--help"])
        assert "--host" in result.output

    def test_serve_command_has_port_option(self) -> None:
        """Test that serve command has --port option."""
        from typer.testing import CliRunner

        from ai_asst_mgr.cli import app

        runner = CliRunner()
        result = runner.invoke(app, ["serve", "--help"])
        assert "--port" in result.output

    def test_serve_command_has_reload_option(self) -> None:
        """Test that serve command has --reload option."""
        from typer.testing import CliRunner

        from ai_asst_mgr.cli import app

        runner = CliRunner()
        result = runner.invoke(app, ["serve", "--help"])
        assert "--reload" in result.output
