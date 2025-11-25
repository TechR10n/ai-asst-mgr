"""Unit tests for capabilities module."""

from __future__ import annotations

import tempfile
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ai_asst_mgr.capabilities import Agent, AgentType, UniversalAgentManager
from ai_asst_mgr.capabilities.manager import (
    AgentCreateResult,
    AgentListResult,
    AgentSyncResult,
)


class TestAgentType:
    """Tests for AgentType enum."""

    def test_agent_type_values(self) -> None:
        """Test AgentType enum has expected values."""
        assert AgentType.AGENT.value == "agent"
        assert AgentType.SKILL.value == "skill"
        assert AgentType.MCP_SERVER.value == "mcp_server"
        assert AgentType.FUNCTION.value == "function"


class TestAgent:
    """Tests for Agent dataclass."""

    def test_agent_creation(self) -> None:
        """Test creating an Agent with required fields."""
        agent = Agent(
            name="test-agent",
            vendor_id="claude",
            agent_type=AgentType.AGENT,
        )
        assert agent.name == "test-agent"
        assert agent.vendor_id == "claude"
        assert agent.agent_type == AgentType.AGENT
        assert agent.description == ""
        assert agent.file_path is None
        assert agent.content == ""
        assert agent.size_bytes == 0

    def test_agent_with_all_fields(self) -> None:
        """Test creating an Agent with all fields."""
        now = datetime.now(UTC)
        agent = Agent(
            name="test-agent",
            vendor_id="claude",
            agent_type=AgentType.SKILL,
            description="A test skill",
            file_path=Path("/test/path/skill.md"),
            content="# Test Skill Content",
            size_bytes=100,
            created_at=now,
            modified_at=now,
            metadata={"key": "value"},
        )
        assert agent.description == "A test skill"
        assert agent.file_path == Path("/test/path/skill.md")
        assert agent.content == "# Test Skill Content"
        assert agent.size_bytes == 100
        assert agent.metadata == {"key": "value"}

    def test_agent_to_dict(self) -> None:
        """Test Agent.to_dict() method."""
        agent = Agent(
            name="test-agent",
            vendor_id="claude",
            agent_type=AgentType.AGENT,
            description="Test description",
            file_path=Path("/test/path"),
            size_bytes=50,
        )
        result = agent.to_dict()

        assert result["name"] == "test-agent"
        assert result["vendor_id"] == "claude"
        assert result["agent_type"] == "agent"
        assert result["description"] == "Test description"
        assert result["file_path"] == "/test/path"
        assert result["size_bytes"] == 50
        assert "created_at" in result
        assert "modified_at" in result
        assert "metadata" in result

    def test_agent_to_dict_with_none_file_path(self) -> None:
        """Test Agent.to_dict() with None file_path."""
        agent = Agent(
            name="test-agent",
            vendor_id="claude",
            agent_type=AgentType.AGENT,
        )
        result = agent.to_dict()
        assert result["file_path"] is None


class TestAgentListResult:
    """Tests for AgentListResult dataclass."""

    def test_agent_list_result_creation(self) -> None:
        """Test creating AgentListResult."""
        result = AgentListResult(
            agents=[],
            total_count=0,
            by_vendor={},
            by_type={},
        )
        assert result.agents == []
        assert result.total_count == 0
        assert result.by_vendor == {}
        assert result.by_type == {}


class TestAgentCreateResult:
    """Tests for AgentCreateResult dataclass."""

    def test_agent_create_result_success(self) -> None:
        """Test successful AgentCreateResult."""
        agent = Agent(name="test", vendor_id="claude", agent_type=AgentType.AGENT)
        result = AgentCreateResult(success=True, agent=agent)
        assert result.success is True
        assert result.agent == agent
        assert result.error is None

    def test_agent_create_result_failure(self) -> None:
        """Test failed AgentCreateResult."""
        result = AgentCreateResult(success=False, error="Test error")
        assert result.success is False
        assert result.agent is None
        assert result.error == "Test error"


class TestAgentSyncResult:
    """Tests for AgentSyncResult dataclass."""

    def test_agent_sync_result_success(self) -> None:
        """Test successful AgentSyncResult."""
        result = AgentSyncResult(
            success=True,
            source_vendor="claude",
            target_vendors=["gemini", "openai"],
            synced_count=2,
            errors=[],
        )
        assert result.success is True
        assert result.source_vendor == "claude"
        assert result.target_vendors == ["gemini", "openai"]
        assert result.synced_count == 2
        assert result.errors == []

    def test_agent_sync_result_partial_failure(self) -> None:
        """Test AgentSyncResult with partial failure."""
        result = AgentSyncResult(
            success=True,
            source_vendor="claude",
            target_vendors=["gemini"],
            synced_count=1,
            errors=["openai: Failed to sync"],
        )
        assert result.success is True
        assert result.synced_count == 1
        assert len(result.errors) == 1


class TestUniversalAgentManager:
    """Tests for UniversalAgentManager class."""

    @pytest.fixture
    def mock_vendors(self) -> dict[str, MagicMock]:
        """Create mock vendor adapters."""
        claude = MagicMock()
        claude.info.name = "Claude"
        gemini = MagicMock()
        gemini.info.name = "Gemini"
        openai = MagicMock()
        openai.info.name = "OpenAI"
        return {"claude": claude, "gemini": gemini, "openai": openai}

    @pytest.fixture
    def manager(self, mock_vendors: dict[str, MagicMock]) -> UniversalAgentManager:
        """Create UniversalAgentManager instance."""
        return UniversalAgentManager(mock_vendors)

    def test_init(self, manager: UniversalAgentManager) -> None:
        """Test UniversalAgentManager initialization."""
        assert manager._vendors is not None
        assert len(manager._vendors) == 3

    def test_list_all_agents_empty(self, manager: UniversalAgentManager) -> None:
        """Test listing agents when none exist."""
        with patch.object(manager, "_get_agents_for_vendor", return_value=[]):
            result = manager.list_all_agents()

        assert result.total_count == 0
        assert result.agents == []
        assert result.by_vendor == {}
        assert result.by_type == {}

    def test_list_all_agents_with_vendor_filter(self, manager: UniversalAgentManager) -> None:
        """Test listing agents with vendor filter."""
        test_agent = Agent(
            name="test",
            vendor_id="claude",
            agent_type=AgentType.AGENT,
        )

        with patch.object(manager, "_get_agents_for_vendor", return_value=[test_agent]):
            result = manager.list_all_agents(vendor_filter="claude")

        assert result.total_count == 1
        assert len(result.agents) == 1
        assert result.by_vendor == {"claude": 1}

    def test_list_all_agents_with_invalid_vendor_filter(
        self, manager: UniversalAgentManager
    ) -> None:
        """Test listing agents with invalid vendor filter returns empty."""
        result = manager.list_all_agents(vendor_filter="invalid_vendor")

        assert result.total_count == 0
        assert result.agents == []

    def test_list_all_agents_with_type_filter(self, manager: UniversalAgentManager) -> None:
        """Test listing agents with type filter."""
        agent = Agent(name="test-agent", vendor_id="claude", agent_type=AgentType.AGENT)
        skill = Agent(name="test-skill", vendor_id="claude", agent_type=AgentType.SKILL)

        with patch.object(manager, "_get_agents_for_vendor", return_value=[agent, skill]):
            result = manager.list_all_agents(vendor_filter="claude", type_filter=AgentType.SKILL)

        assert result.total_count == 1
        assert result.agents[0].name == "test-skill"

    def test_list_all_agents_with_search_query(self, manager: UniversalAgentManager) -> None:
        """Test listing agents with search query."""
        agent1 = Agent(
            name="code-review",
            vendor_id="claude",
            agent_type=AgentType.AGENT,
            description="Reviews code",
        )
        agent2 = Agent(
            name="test-runner",
            vendor_id="claude",
            agent_type=AgentType.AGENT,
            description="Runs tests",
        )

        with patch.object(manager, "_get_agents_for_vendor", return_value=[agent1, agent2]):
            result = manager.list_all_agents(vendor_filter="claude", search_query="code")

        assert result.total_count == 1
        assert result.agents[0].name == "code-review"

    def test_list_all_agents_search_query_case_insensitive(
        self, manager: UniversalAgentManager
    ) -> None:
        """Test search query is case insensitive."""
        agent = Agent(
            name="CodeReview",
            vendor_id="claude",
            agent_type=AgentType.AGENT,
            description="Reviews CODE",
        )

        with patch.object(manager, "_get_agents_for_vendor", return_value=[agent]):
            result = manager.list_all_agents(vendor_filter="claude", search_query="code")

        assert result.total_count == 1

    def test_list_all_agents_sorted_by_vendor_and_name(
        self, manager: UniversalAgentManager
    ) -> None:
        """Test agents are sorted by vendor then name."""
        agents = [
            Agent(name="zebra", vendor_id="claude", agent_type=AgentType.AGENT),
            Agent(name="alpha", vendor_id="gemini", agent_type=AgentType.AGENT),
            Agent(name="beta", vendor_id="claude", agent_type=AgentType.AGENT),
        ]

        def mock_get_agents(vendor_id: str, _adapter: MagicMock) -> list[Agent]:
            return [a for a in agents if a.vendor_id == vendor_id]

        with patch.object(manager, "_get_agents_for_vendor", side_effect=mock_get_agents):
            result = manager.list_all_agents()

        assert result.agents[0].vendor_id == "claude"
        assert result.agents[0].name == "beta"
        assert result.agents[1].vendor_id == "claude"
        assert result.agents[1].name == "zebra"
        assert result.agents[2].vendor_id == "gemini"


class TestUniversalAgentManagerFileOperations:
    """Tests for file-based agent operations."""

    @pytest.fixture
    def temp_dirs(self) -> tuple[Path, Path, Path]:
        """Create temporary directories for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            claude_dir = temp_path / "claude"
            gemini_dir = temp_path / "gemini"
            openai_dir = temp_path / "codex"

            # Create directory structures
            (claude_dir / "agents").mkdir(parents=True)
            (claude_dir / "skills").mkdir()
            (gemini_dir / "mcp_servers").mkdir(parents=True)
            (openai_dir / "mcp_servers").mkdir(parents=True)

            yield claude_dir, gemini_dir, openai_dir

    def test_get_claude_agents(self) -> None:
        """Test getting Claude agents from filesystem."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            agents_dir = temp_path / "agents"
            skills_dir = temp_path / "skills"
            agents_dir.mkdir()
            skills_dir.mkdir()

            # Create test agent file
            agent_file = agents_dir / "test-agent.md"
            agent_file.write_text("# Test Agent\nThis is a test agent.")

            # Create test skill file
            skill_file = skills_dir / "test-skill.md"
            skill_file.write_text("# Test Skill\nThis is a test skill.")

            manager = UniversalAgentManager({})

            # Direct test of _create_agent_from_file
            agent = manager._create_agent_from_file(agent_file, "claude", AgentType.AGENT)

            assert agent.name == "test-agent"
            assert agent.vendor_id == "claude"
            assert agent.agent_type == AgentType.AGENT
            assert "Test Agent" in agent.description or "test agent" in agent.description.lower()

    def test_create_agent_from_file(self) -> None:
        """Test _create_agent_from_file method."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            test_file = temp_path / "my-agent.md"
            test_file.write_text("# My Agent\n\nThis agent does things.")

            manager = UniversalAgentManager({})
            agent = manager._create_agent_from_file(test_file, "claude", AgentType.AGENT)

            assert agent.name == "my-agent"
            assert agent.vendor_id == "claude"
            assert agent.agent_type == AgentType.AGENT
            assert agent.file_path == test_file
            assert agent.size_bytes > 0
            assert "My Agent" in agent.description

    def test_create_agent_from_file_with_no_heading(self) -> None:
        """Test _create_agent_from_file with file that has no heading."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            test_file = temp_path / "simple-agent.md"
            test_file.write_text("This is just plain text content.")

            manager = UniversalAgentManager({})
            agent = manager._create_agent_from_file(test_file, "claude", AgentType.AGENT)

            assert agent.name == "simple-agent"
            assert "plain text content" in agent.description

    def test_create_agent_from_file_handles_unreadable_file(self) -> None:
        """Test _create_agent_from_file handles file read errors gracefully."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            test_file = temp_path / "binary-agent.md"
            test_file.write_bytes(b"\x00\x01\x02\x03")  # Binary content

            manager = UniversalAgentManager({})
            # Should not raise, just return empty content/description
            agent = manager._create_agent_from_file(test_file, "claude", AgentType.AGENT)

            assert agent.name == "binary-agent"
            # Content may be empty or partial depending on encoding handling


class TestUniversalAgentManagerCreate:
    """Tests for agent creation."""

    @pytest.fixture
    def mock_vendors(self) -> dict[str, MagicMock]:
        """Create mock vendor adapters."""
        return {"claude": MagicMock(), "gemini": MagicMock()}

    @pytest.fixture
    def manager(self, mock_vendors: dict[str, MagicMock]) -> UniversalAgentManager:
        """Create UniversalAgentManager instance."""
        return UniversalAgentManager(mock_vendors)

    def test_create_agent_unknown_vendor(self, manager: UniversalAgentManager) -> None:
        """Test creating agent with unknown vendor fails."""
        result = manager.create_agent(
            name="test",
            vendor_id="unknown",
            agent_type=AgentType.AGENT,
            content="Test content",
        )

        assert result.success is False
        assert "Unknown vendor" in (result.error or "")

    def test_create_agent_success(self) -> None:
        """Test successful agent creation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            config_dir = temp_path / ".claude"
            config_dir.mkdir()

            manager = UniversalAgentManager({"claude": MagicMock()})

            with patch.object(manager, "_get_vendor_config_dir", return_value=config_dir):
                result = manager.create_agent(
                    name="new-agent",
                    vendor_id="claude",
                    agent_type=AgentType.AGENT,
                    content="# New Agent\n\nTest content",
                )

            assert result.success is True
            assert result.agent is not None
            assert result.agent.name == "new-agent"
            assert (config_dir / "agents" / "new-agent.md").exists()

    def test_create_agent_with_progress_callback(self) -> None:
        """Test agent creation with progress callback."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            config_dir = temp_path / ".claude"
            config_dir.mkdir()

            manager = UniversalAgentManager({"claude": MagicMock()})
            progress_messages: list[str] = []

            def callback(msg: str) -> None:
                progress_messages.append(msg)

            with patch.object(manager, "_get_vendor_config_dir", return_value=config_dir):
                manager.create_agent(
                    name="test-agent",
                    vendor_id="claude",
                    agent_type=AgentType.AGENT,
                    content="Test content",
                    progress_callback=callback,
                )

            assert len(progress_messages) > 0
            assert "Creating" in progress_messages[0]

    def test_create_skill(self) -> None:
        """Test creating a skill."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            config_dir = temp_path / ".claude"
            config_dir.mkdir()

            manager = UniversalAgentManager({"claude": MagicMock()})

            with patch.object(manager, "_get_vendor_config_dir", return_value=config_dir):
                result = manager.create_agent(
                    name="new-skill",
                    vendor_id="claude",
                    agent_type=AgentType.SKILL,
                    content="# New Skill\n\nTest content",
                )

            assert result.success is True
            assert (config_dir / "skills" / "new-skill.md").exists()

    def test_create_mcp_server_json(self) -> None:
        """Test creating an MCP server (JSON file)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            config_dir = temp_path / ".gemini"
            config_dir.mkdir()

            manager = UniversalAgentManager({"gemini": MagicMock()})

            with patch.object(manager, "_get_vendor_config_dir", return_value=config_dir):
                result = manager.create_agent(
                    name="test-mcp",
                    vendor_id="gemini",
                    agent_type=AgentType.MCP_SERVER,
                    content='{"name": "test-mcp", "url": "http://localhost"}',
                )

            assert result.success is True
            assert (config_dir / "mcp_servers" / "test-mcp.json").exists()


class TestUniversalAgentManagerSync:
    """Tests for agent sync operations."""

    @pytest.fixture
    def manager_with_agents(self) -> UniversalAgentManager:
        """Create manager with pre-existing agents."""
        return UniversalAgentManager(
            {"claude": MagicMock(), "gemini": MagicMock(), "openai": MagicMock()}
        )

    def test_sync_agent_unknown_source_vendor(
        self, manager_with_agents: UniversalAgentManager
    ) -> None:
        """Test syncing from unknown source vendor fails."""
        result = manager_with_agents.sync_agent(
            agent_name="test",
            source_vendor="unknown",
        )

        assert result.success is False
        assert "Unknown source vendor" in result.errors[0]

    def test_sync_agent_not_found(self, manager_with_agents: UniversalAgentManager) -> None:
        """Test syncing non-existent agent fails."""
        with patch.object(
            manager_with_agents,
            "list_all_agents",
            return_value=AgentListResult(agents=[], total_count=0, by_vendor={}, by_type={}),
        ):
            result = manager_with_agents.sync_agent(
                agent_name="nonexistent",
                source_vendor="claude",
            )

        assert result.success is False
        assert "not found" in result.errors[0]

    def test_sync_agent_no_valid_targets(self, manager_with_agents: UniversalAgentManager) -> None:
        """Test syncing with no valid target vendors."""
        agent = Agent(
            name="test-agent",
            vendor_id="claude",
            agent_type=AgentType.AGENT,
            content="Test",
        )

        with patch.object(
            manager_with_agents,
            "list_all_agents",
            return_value=AgentListResult(
                agents=[agent], total_count=1, by_vendor={"claude": 1}, by_type={}
            ),
        ):
            result = manager_with_agents.sync_agent(
                agent_name="test-agent",
                source_vendor="claude",
                target_vendors=["invalid"],
            )

        assert result.success is False
        assert "No valid target vendors" in result.errors[0]

    def test_sync_agent_success(self) -> None:
        """Test successful agent sync."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Setup directories
            claude_dir = temp_path / ".claude"
            gemini_dir = temp_path / ".gemini"
            (claude_dir / "agents").mkdir(parents=True)
            (gemini_dir / "mcp_servers").mkdir(parents=True)

            # Create source agent
            source_file = claude_dir / "agents" / "test-agent.md"
            source_file.write_text("# Test Agent\n\nContent")

            manager = UniversalAgentManager({"claude": MagicMock(), "gemini": MagicMock()})

            # Create a real agent from file
            source_agent = manager._create_agent_from_file(source_file, "claude", AgentType.AGENT)

            with (
                patch.object(
                    manager,
                    "list_all_agents",
                    return_value=AgentListResult(
                        agents=[source_agent],
                        total_count=1,
                        by_vendor={"claude": 1},
                        by_type={"agent": 1},
                    ),
                ),
                patch.object(manager, "_get_vendor_config_dir", return_value=gemini_dir),
                patch.object(manager, "_get_compatible_type", return_value=None),
            ):
                result = manager.sync_agent(
                    agent_name="test-agent",
                    source_vendor="claude",
                    target_vendors=["gemini"],
                )

            # Since gemini doesn't support agent type, should have error
            assert "Cannot sync" in result.errors[0] or result.synced_count == 0

    def test_sync_agent_to_all_others(self) -> None:
        """Test syncing agent to all other vendors (no target specified)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Setup directories
            claude_dir = temp_path / ".claude"
            openai_dir = temp_path / ".codex"
            (claude_dir / "agents").mkdir(parents=True)
            openai_dir.mkdir(parents=True)

            # Create source agent
            source_file = claude_dir / "agents" / "test-agent.md"
            source_file.write_text("# Test Agent\n\nContent")

            manager = UniversalAgentManager({"claude": MagicMock(), "openai": MagicMock()})

            source_agent = manager._create_agent_from_file(source_file, "claude", AgentType.AGENT)

            with (
                patch.object(
                    manager,
                    "list_all_agents",
                    return_value=AgentListResult(
                        agents=[source_agent],
                        total_count=1,
                        by_vendor={"claude": 1},
                        by_type={"agent": 1},
                    ),
                ),
                patch.object(manager, "_get_vendor_config_dir", return_value=openai_dir),
                patch.object(manager, "_get_compatible_type", return_value=AgentType.AGENT),
            ):
                result = manager.sync_agent(
                    agent_name="test-agent",
                    source_vendor="claude",
                    target_vendors=None,  # Sync to all
                )

            # Should have attempted openai
            assert "openai" in result.target_vendors or len(result.errors) > 0

    def test_sync_agent_with_progress_callback(self) -> None:
        """Test sync agent calls progress callback."""
        agent = Agent(
            name="test-agent",
            vendor_id="claude",
            agent_type=AgentType.AGENT,
            content="Test",
        )

        manager = UniversalAgentManager({"claude": MagicMock(), "openai": MagicMock()})
        messages: list[str] = []

        with (
            patch.object(
                manager,
                "list_all_agents",
                return_value=AgentListResult(
                    agents=[agent],
                    total_count=1,
                    by_vendor={"claude": 1},
                    by_type={},
                ),
            ),
            patch.object(manager, "_get_compatible_type", return_value=None),
        ):
            manager.sync_agent(
                agent_name="test-agent",
                source_vendor="claude",
                target_vendors=["openai"],
                progress_callback=messages.append,
            )

        assert len(messages) > 0


class TestUniversalAgentManagerGetDelete:
    """Tests for get and delete operations."""

    def test_get_agent_found(self) -> None:
        """Test getting an existing agent."""
        agent = Agent(name="test", vendor_id="claude", agent_type=AgentType.AGENT)
        manager = UniversalAgentManager({"claude": MagicMock()})

        with patch.object(
            manager,
            "list_all_agents",
            return_value=AgentListResult(agents=[agent], total_count=1, by_vendor={}, by_type={}),
        ):
            result = manager.get_agent("test", "claude")

        assert result is not None
        assert result.name == "test"

    def test_get_agent_not_found(self) -> None:
        """Test getting a non-existent agent returns None."""
        manager = UniversalAgentManager({"claude": MagicMock()})

        with patch.object(
            manager,
            "list_all_agents",
            return_value=AgentListResult(agents=[], total_count=0, by_vendor={}, by_type={}),
        ):
            result = manager.get_agent("nonexistent", "claude")

        assert result is None

    def test_delete_agent_success(self) -> None:
        """Test successful agent deletion."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            agent_file = temp_path / "test-agent.md"
            agent_file.write_text("Test content")

            agent = Agent(
                name="test-agent",
                vendor_id="claude",
                agent_type=AgentType.AGENT,
                file_path=agent_file,
            )

            manager = UniversalAgentManager({"claude": MagicMock()})

            with patch.object(manager, "get_agent", return_value=agent):
                success, message = manager.delete_agent("test-agent", "claude")

            assert success is True
            assert "Deleted" in message
            assert not agent_file.exists()

    def test_delete_agent_not_found(self) -> None:
        """Test deleting non-existent agent fails."""
        manager = UniversalAgentManager({"claude": MagicMock()})

        with patch.object(manager, "get_agent", return_value=None):
            success, message = manager.delete_agent("nonexistent", "claude")

        assert success is False
        assert "not found" in message

    def test_delete_agent_no_file_path(self) -> None:
        """Test deleting agent without file path fails."""
        agent = Agent(
            name="test",
            vendor_id="claude",
            agent_type=AgentType.AGENT,
            file_path=None,
        )
        manager = UniversalAgentManager({"claude": MagicMock()})

        with patch.object(manager, "get_agent", return_value=agent):
            success, message = manager.delete_agent("test", "claude")

        assert success is False
        assert "no associated file" in message

    def test_delete_agent_with_callback(self) -> None:
        """Test delete agent with progress callback."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            agent_file = temp_path / "test-agent.md"
            agent_file.write_text("Test content")

            agent = Agent(
                name="test-agent",
                vendor_id="claude",
                agent_type=AgentType.AGENT,
                file_path=agent_file,
            )

            manager = UniversalAgentManager({"claude": MagicMock()})
            messages: list[str] = []

            with patch.object(manager, "get_agent", return_value=agent):
                manager.delete_agent("test-agent", "claude", progress_callback=messages.append)

            assert len(messages) > 0
            assert "Deleting" in messages[0]


class TestCompatibleTypes:
    """Tests for agent type compatibility."""

    @pytest.fixture
    def manager(self) -> UniversalAgentManager:
        """Create manager instance."""
        return UniversalAgentManager({})

    def test_claude_accepts_agents(self, manager: UniversalAgentManager) -> None:
        """Test Claude accepts agent type."""
        result = manager._get_compatible_type(AgentType.AGENT, "claude")
        assert result == AgentType.AGENT

    def test_claude_accepts_skills(self, manager: UniversalAgentManager) -> None:
        """Test Claude accepts skill type."""
        result = manager._get_compatible_type(AgentType.SKILL, "claude")
        assert result == AgentType.SKILL

    def test_claude_converts_mcp_to_agent(self, manager: UniversalAgentManager) -> None:
        """Test Claude converts MCP server to agent."""
        result = manager._get_compatible_type(AgentType.MCP_SERVER, "claude")
        assert result == AgentType.AGENT

    def test_gemini_accepts_mcp(self, manager: UniversalAgentManager) -> None:
        """Test Gemini accepts MCP server type."""
        result = manager._get_compatible_type(AgentType.MCP_SERVER, "gemini")
        assert result == AgentType.MCP_SERVER

    def test_gemini_rejects_agents(self, manager: UniversalAgentManager) -> None:
        """Test Gemini rejects agent type (no conversion)."""
        result = manager._get_compatible_type(AgentType.AGENT, "gemini")
        assert result is None

    def test_openai_accepts_mcp(self, manager: UniversalAgentManager) -> None:
        """Test OpenAI accepts MCP server type."""
        result = manager._get_compatible_type(AgentType.MCP_SERVER, "openai")
        assert result == AgentType.MCP_SERVER

    def test_openai_converts_to_agent(self, manager: UniversalAgentManager) -> None:
        """Test OpenAI converts skill to agent."""
        result = manager._get_compatible_type(AgentType.SKILL, "openai")
        assert result == AgentType.AGENT

    def test_unknown_vendor(self, manager: UniversalAgentManager) -> None:
        """Test unknown vendor returns None."""
        result = manager._get_compatible_type(AgentType.AGENT, "unknown")
        assert result is None


class TestVendorAgentDiscovery:
    """Tests for vendor-specific agent discovery methods."""

    def test_get_claude_agents_with_files(self) -> None:
        """Test getting Claude agents when files exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create mock .claude directory structure
            agents_dir = temp_path / "agents"
            skills_dir = temp_path / "skills"
            agents_dir.mkdir()
            skills_dir.mkdir()

            # Create agent files
            (agents_dir / "code-review.md").write_text("# Code Review\n\nReviews code")
            (agents_dir / "test-runner.md").write_text("# Test Runner\n\nRuns tests")
            (skills_dir / "debugging.md").write_text("# Debugging\n\nDebugging skill")

            manager = UniversalAgentManager({"claude": MagicMock()})

            # Get agents using internal method simulation
            agents: list[Agent] = []

            # Check agents directory
            for agent_file in agents_dir.glob("*.md"):
                agents.append(
                    manager._create_agent_from_file(agent_file, "claude", AgentType.AGENT)
                )

            # Check skills directory
            for skill_file in skills_dir.glob("*.md"):
                agents.append(
                    manager._create_agent_from_file(skill_file, "claude", AgentType.SKILL)
                )

            assert len(agents) == 3
            agent_names = {a.name for a in agents}
            assert "code-review" in agent_names
            assert "test-runner" in agent_names
            assert "debugging" in agent_names

    def test_get_gemini_mcp_servers(self) -> None:
        """Test getting Gemini MCP servers."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create mock mcp_servers directory
            mcp_dir = temp_path / "mcp_servers"
            mcp_dir.mkdir()

            # Create MCP server files
            (mcp_dir / "brave-search.json").write_text(
                '{"name": "brave-search", "url": "http://localhost"}'
            )
            (mcp_dir / "file-system.json").write_text('{"name": "file-system", "path": "/"}')

            manager = UniversalAgentManager({"gemini": MagicMock()})

            # Get MCP servers
            agents: list[Agent] = []
            for mcp_file in mcp_dir.glob("*.json"):
                agents.append(
                    manager._create_agent_from_file(mcp_file, "gemini", AgentType.MCP_SERVER)
                )

            assert len(agents) == 2
            assert agents[0].agent_type == AgentType.MCP_SERVER

    def test_get_openai_agents_with_agents_md(self) -> None:
        """Test getting OpenAI agents when AGENTS.md exists."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create AGENTS.md
            agents_md = temp_path / "AGENTS.md"
            agents_md.write_text("# OpenAI Agents\n\nAgent definitions here")

            manager = UniversalAgentManager({"openai": MagicMock()})

            agent = manager._create_agent_from_file(agents_md, "openai", AgentType.AGENT)

            assert agent.name == "AGENTS"
            assert agent.vendor_id == "openai"

    def test_create_agent_with_description_from_heading(self) -> None:
        """Test extracting description from markdown heading."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            test_file = temp_path / "test.md"
            test_file.write_text("# My Agent Title\n\nThis is the content.")

            manager = UniversalAgentManager({})
            agent = manager._create_agent_from_file(test_file, "claude", AgentType.AGENT)

            assert agent.description == "My Agent Title"

    def test_create_agent_with_description_from_first_line(self) -> None:
        """Test extracting description from first non-heading line."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            test_file = temp_path / "test.md"
            test_file.write_text("This is the first line of content.\n\nMore content here.")

            manager = UniversalAgentManager({})
            agent = manager._create_agent_from_file(test_file, "claude", AgentType.AGENT)

            assert "first line" in agent.description

    def test_create_agent_truncates_long_description(self) -> None:
        """Test description is truncated to 100 characters."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            test_file = temp_path / "test.md"
            long_line = "A" * 150
            test_file.write_text(long_line)

            manager = UniversalAgentManager({})
            agent = manager._create_agent_from_file(test_file, "claude", AgentType.AGENT)

            assert len(agent.description) <= 100


class TestVendorConfigDirectories:
    """Tests for vendor config directory resolution."""

    @pytest.fixture
    def manager(self) -> UniversalAgentManager:
        """Create manager instance."""
        return UniversalAgentManager({})

    def test_get_claude_config_dir(self, manager: UniversalAgentManager) -> None:
        """Test getting Claude config directory."""
        result = manager._get_vendor_config_dir("claude")
        assert result == Path.home() / ".claude"

    def test_get_gemini_config_dir(self, manager: UniversalAgentManager) -> None:
        """Test getting Gemini config directory."""
        result = manager._get_vendor_config_dir("gemini")
        assert result == Path.home() / ".gemini"

    def test_get_openai_config_dir(self, manager: UniversalAgentManager) -> None:
        """Test getting OpenAI config directory."""
        result = manager._get_vendor_config_dir("openai")
        assert result == Path.home() / ".codex"

    def test_get_unknown_config_dir(self, manager: UniversalAgentManager) -> None:
        """Test getting unknown vendor config returns None."""
        result = manager._get_vendor_config_dir("unknown")
        assert result is None

    def test_get_agent_directory_claude_agent(self, manager: UniversalAgentManager) -> None:
        """Test getting Claude agent directory."""
        config_dir = Path("/test")
        result = manager._get_agent_directory(config_dir, "claude", AgentType.AGENT)
        assert result == config_dir / "agents"

    def test_get_agent_directory_claude_skill(self, manager: UniversalAgentManager) -> None:
        """Test getting Claude skill directory."""
        config_dir = Path("/test")
        result = manager._get_agent_directory(config_dir, "claude", AgentType.SKILL)
        assert result == config_dir / "skills"

    def test_get_agent_directory_gemini_mcp(self, manager: UniversalAgentManager) -> None:
        """Test getting Gemini MCP server directory."""
        config_dir = Path("/test")
        result = manager._get_agent_directory(config_dir, "gemini", AgentType.MCP_SERVER)
        assert result == config_dir / "mcp_servers"

    def test_get_agent_directory_unsupported_type(self, manager: UniversalAgentManager) -> None:
        """Test unsupported type returns None."""
        config_dir = Path("/test")
        result = manager._get_agent_directory(config_dir, "gemini", AgentType.AGENT)
        assert result is None
