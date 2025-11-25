"""Universal Agent Manager for cross-vendor agent operations.

This module provides a unified interface for managing agents across all
supported AI assistant vendors.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

    from ai_asst_mgr.adapters.base import VendorAdapter


class AgentType(Enum):
    """Type of agent or capability."""

    AGENT = "agent"
    SKILL = "skill"
    MCP_SERVER = "mcp_server"
    FUNCTION = "function"


@dataclass
class Agent:
    """Universal representation of an agent across vendors.

    This dataclass provides a unified view of agents, skills, MCP servers,
    and other capabilities across different AI assistant vendors.
    """

    name: str
    vendor_id: str
    agent_type: AgentType
    description: str = ""
    file_path: Path | None = None
    content: str = ""
    size_bytes: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    modified_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        """Convert agent to dictionary representation.

        Returns:
            Dictionary with agent data.
        """
        return {
            "name": self.name,
            "vendor_id": self.vendor_id,
            "agent_type": self.agent_type.value,
            "description": self.description,
            "file_path": str(self.file_path) if self.file_path else None,
            "size_bytes": self.size_bytes,
            "created_at": self.created_at.isoformat(),
            "modified_at": self.modified_at.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class AgentListResult:
    """Result of listing agents."""

    agents: list[Agent]
    total_count: int
    by_vendor: dict[str, int]
    by_type: dict[str, int]


@dataclass
class AgentCreateResult:
    """Result of creating an agent."""

    success: bool
    agent: Agent | None = None
    error: str | None = None


@dataclass
class AgentSyncResult:
    """Result of syncing an agent across vendors."""

    success: bool
    source_vendor: str = ""
    target_vendors: list[str] = field(default_factory=list)
    synced_count: int = 0
    errors: list[str] = field(default_factory=list)


class UniversalAgentManager:
    """Manages agents across all AI assistant vendors.

    This class provides a unified interface for listing, creating, and
    syncing agents across Claude, Gemini, and OpenAI vendors.
    """

    def __init__(self, vendors: dict[str, VendorAdapter]) -> None:
        """Initialize the agent manager.

        Args:
            vendors: Dictionary mapping vendor IDs to their adapters.
        """
        self._vendors = vendors

    def list_all_agents(
        self,
        vendor_filter: str | None = None,
        type_filter: AgentType | None = None,
        search_query: str | None = None,
    ) -> AgentListResult:
        """List all agents across vendors.

        Args:
            vendor_filter: Optional vendor ID to filter by.
            type_filter: Optional agent type to filter by.
            search_query: Optional search query for name/description.

        Returns:
            AgentListResult with all matching agents.
        """
        all_agents: list[Agent] = []
        by_vendor: dict[str, int] = {}
        by_type: dict[str, int] = {}

        vendors_to_check = self._vendors
        if vendor_filter:
            if vendor_filter in self._vendors:
                vendors_to_check = {vendor_filter: self._vendors[vendor_filter]}
            else:
                return AgentListResult(
                    agents=[],
                    total_count=0,
                    by_vendor={},
                    by_type={},
                )

        for vendor_id, adapter in vendors_to_check.items():
            vendor_agents = self._get_agents_for_vendor(vendor_id, adapter)

            for agent in vendor_agents:
                # Apply type filter
                if type_filter and agent.agent_type != type_filter:
                    continue

                # Apply search filter
                if search_query:
                    query_lower = search_query.lower()
                    if (
                        query_lower not in agent.name.lower()
                        and query_lower not in agent.description.lower()
                    ):
                        continue

                all_agents.append(agent)

                # Update counts
                by_vendor[vendor_id] = by_vendor.get(vendor_id, 0) + 1
                type_key = agent.agent_type.value
                by_type[type_key] = by_type.get(type_key, 0) + 1

        # Sort by vendor, then by name
        all_agents.sort(key=lambda a: (a.vendor_id, a.name))

        return AgentListResult(
            agents=all_agents,
            total_count=len(all_agents),
            by_vendor=by_vendor,
            by_type=by_type,
        )

    def _get_agents_for_vendor(self, vendor_id: str, adapter: VendorAdapter) -> list[Agent]:
        """Get all agents for a specific vendor.

        Args:
            vendor_id: The vendor identifier.
            adapter: The vendor adapter.

        Returns:
            List of agents for the vendor.
        """
        agents: list[Agent] = []

        if vendor_id == "claude":
            agents.extend(self._get_claude_agents(adapter))
        elif vendor_id == "gemini":
            agents.extend(self._get_gemini_agents(adapter))
        elif vendor_id == "openai":
            agents.extend(self._get_openai_agents(adapter))

        return agents

    def _get_claude_agents(self, adapter: VendorAdapter) -> list[Agent]:
        """Get agents and skills from Claude.

        Args:
            adapter: The Claude adapter (provides config_dir).

        Returns:
            List of Claude agents and skills.
        """
        agents: list[Agent] = []
        config_dir = adapter.info.config_dir

        # Get agents
        agents_dir = config_dir / "agents"
        if agents_dir.exists():
            for agent_file in agents_dir.glob("*.md"):
                agents.append(
                    self._create_agent_from_file(
                        file_path=agent_file,
                        vendor_id="claude",
                        agent_type=AgentType.AGENT,
                    )
                )

        # Get skills
        skills_dir = config_dir / "skills"
        if skills_dir.exists():
            for skill_file in skills_dir.glob("*.md"):
                agents.append(
                    self._create_agent_from_file(
                        file_path=skill_file,
                        vendor_id="claude",
                        agent_type=AgentType.SKILL,
                    )
                )

        return agents

    def _get_gemini_agents(self, adapter: VendorAdapter) -> list[Agent]:
        """Get MCP servers from Gemini.

        Args:
            adapter: The Gemini adapter (provides config_dir).

        Returns:
            List of Gemini MCP servers as agents.
        """
        agents: list[Agent] = []
        config_dir = adapter.info.config_dir

        # Gemini uses MCP servers instead of native agents
        mcp_dir = config_dir / "mcp_servers"
        if mcp_dir.exists():
            for mcp_file in mcp_dir.glob("*.json"):
                agents.append(
                    self._create_agent_from_file(
                        file_path=mcp_file,
                        vendor_id="gemini",
                        agent_type=AgentType.MCP_SERVER,
                    )
                )

        return agents

    def _get_openai_agents(self, adapter: VendorAdapter) -> list[Agent]:
        """Get agents from OpenAI Codex.

        Args:
            adapter: The OpenAI adapter (provides config_dir).

        Returns:
            List of OpenAI agents.
        """
        agents: list[Agent] = []
        config_dir = adapter.info.config_dir

        # Check AGENTS.md
        agents_md = config_dir / "AGENTS.md"
        if agents_md.exists():
            agents.append(
                self._create_agent_from_file(
                    file_path=agents_md,
                    vendor_id="openai",
                    agent_type=AgentType.AGENT,
                )
            )

        # Check MCP servers
        mcp_dir = config_dir / "mcp_servers"
        if mcp_dir.exists():
            for mcp_file in mcp_dir.glob("*.json"):
                agents.append(
                    self._create_agent_from_file(
                        file_path=mcp_file,
                        vendor_id="openai",
                        agent_type=AgentType.MCP_SERVER,
                    )
                )

        return agents

    def _create_agent_from_file(
        self,
        file_path: Path,
        vendor_id: str,
        agent_type: AgentType,
    ) -> Agent:
        """Create an Agent from a file.

        Args:
            file_path: Path to the agent file.
            vendor_id: The vendor identifier.
            agent_type: Type of agent.

        Returns:
            Agent instance.
        """
        stat = file_path.stat()
        content = ""
        description = ""

        try:
            content = file_path.read_text(encoding="utf-8")
            # Extract description from first non-empty line or heading
            for raw_line in content.split("\n"):
                stripped = raw_line.strip()
                if stripped and not stripped.startswith("#"):
                    description = stripped[:100]
                    break
                if stripped.startswith("# "):
                    description = stripped[2:].strip()[:100]
                    break
        except (OSError, UnicodeDecodeError):
            pass

        return Agent(
            name=file_path.stem,
            vendor_id=vendor_id,
            agent_type=agent_type,
            description=description,
            file_path=file_path,
            content=content,
            size_bytes=stat.st_size,
            created_at=datetime.fromtimestamp(stat.st_ctime, tz=UTC),
            modified_at=datetime.fromtimestamp(stat.st_mtime, tz=UTC),
        )

    def create_agent(
        self,
        name: str,
        vendor_id: str,
        agent_type: AgentType,
        content: str,
        *,
        progress_callback: Callable[[str], None] | None = None,
    ) -> AgentCreateResult:
        """Create a new agent for a vendor.

        Args:
            name: Name of the agent.
            vendor_id: Target vendor ID.
            agent_type: Type of agent to create.
            content: Content of the agent file.
            progress_callback: Optional callback for progress updates.

        Returns:
            AgentCreateResult with success status.
        """
        if vendor_id not in self._vendors:
            return AgentCreateResult(
                success=False,
                error=f"Unknown vendor: {vendor_id}",
            )

        # Determine target directory based on vendor and type
        config_dir = self._get_vendor_config_dir(vendor_id)
        if not config_dir:
            return AgentCreateResult(
                success=False,
                error=f"Could not find config directory for {vendor_id}",
            )

        target_dir = self._get_agent_directory(config_dir, vendor_id, agent_type)
        if not target_dir:
            return AgentCreateResult(
                success=False,
                error=f"Agent type {agent_type.value} not supported for {vendor_id}",
            )

        # Create directory if needed
        target_dir.mkdir(parents=True, exist_ok=True)

        # Determine file extension
        extension = ".md" if agent_type in (AgentType.AGENT, AgentType.SKILL) else ".json"
        file_path = target_dir / f"{name}{extension}"

        if progress_callback:
            progress_callback(f"Creating {file_path}")

        try:
            file_path.write_text(content, encoding="utf-8")
            agent = self._create_agent_from_file(file_path, vendor_id, agent_type)
            return AgentCreateResult(success=True, agent=agent)
        except OSError as e:
            return AgentCreateResult(success=False, error=str(e))

    def _get_vendor_config_dir(self, vendor_id: str) -> Path | None:
        """Get the config directory for a vendor.

        Args:
            vendor_id: The vendor identifier.

        Returns:
            Path to config directory or None.
        """
        config_dirs = {
            "claude": Path.home() / ".claude",
            "gemini": Path.home() / ".gemini",
            "openai": Path.home() / ".codex",
        }
        return config_dirs.get(vendor_id)

    def _get_agent_directory(
        self, config_dir: Path, vendor_id: str, agent_type: AgentType
    ) -> Path | None:
        """Get the directory for storing agents of a given type.

        Args:
            config_dir: The vendor's config directory.
            vendor_id: The vendor identifier.
            agent_type: Type of agent.

        Returns:
            Path to agent directory or None if not supported.
        """
        if vendor_id == "claude":
            if agent_type == AgentType.AGENT:
                return config_dir / "agents"
            if agent_type == AgentType.SKILL:
                return config_dir / "skills"
        elif vendor_id in ("gemini", "openai"):
            if agent_type == AgentType.MCP_SERVER:
                return config_dir / "mcp_servers"
            if agent_type == AgentType.AGENT and vendor_id == "openai":
                return config_dir  # AGENTS.md at root

        return None

    def sync_agent(
        self,
        agent_name: str,
        source_vendor: str,
        target_vendors: list[str] | None = None,
        *,
        progress_callback: Callable[[str], None] | None = None,
    ) -> AgentSyncResult:
        """Sync an agent from one vendor to others.

        Args:
            agent_name: Name of the agent to sync.
            source_vendor: Source vendor ID.
            target_vendors: Target vendor IDs (None = all others).
            progress_callback: Optional callback for progress updates.

        Returns:
            AgentSyncResult with sync status.
        """
        if source_vendor not in self._vendors:
            return AgentSyncResult(
                success=False,
                errors=[f"Unknown source vendor: {source_vendor}"],
            )

        # Find the source agent
        result = self.list_all_agents(vendor_filter=source_vendor)
        source_agent = None
        for agent in result.agents:
            if agent.name == agent_name:
                source_agent = agent
                break

        if not source_agent:
            return AgentSyncResult(
                success=False,
                errors=[f"Agent '{agent_name}' not found in {source_vendor}"],
            )

        # Determine target vendors
        if target_vendors is None:
            target_vendors = [v for v in self._vendors if v != source_vendor]
        else:
            target_vendors = [
                v for v in target_vendors if v in self._vendors and v != source_vendor
            ]

        if not target_vendors:
            return AgentSyncResult(
                success=False,
                errors=["No valid target vendors specified"],
            )

        # Sync to each target
        synced: list[str] = []
        errors: list[str] = []

        for target_vendor in target_vendors:
            if progress_callback:
                progress_callback(f"Syncing to {target_vendor}")

            # Determine appropriate agent type for target vendor
            target_type = self._get_compatible_type(source_agent.agent_type, target_vendor)
            if not target_type:
                errors.append(f"Cannot sync {source_agent.agent_type.value} to {target_vendor}")
                continue

            # Create the agent in target vendor
            create_result = self.create_agent(
                name=source_agent.name,
                vendor_id=target_vendor,
                agent_type=target_type,
                content=source_agent.content,
                progress_callback=progress_callback,
            )

            if create_result.success:
                synced.append(target_vendor)
            else:
                errors.append(f"{target_vendor}: {create_result.error}")

        return AgentSyncResult(
            success=len(synced) > 0,
            source_vendor=source_vendor,
            target_vendors=synced,
            synced_count=len(synced),
            errors=errors,
        )

    def _get_compatible_type(self, source_type: AgentType, target_vendor: str) -> AgentType | None:
        """Get compatible agent type for target vendor.

        Args:
            source_type: Source agent type.
            target_vendor: Target vendor ID.

        Returns:
            Compatible agent type or None if not supported.
        """
        # Vendor type compatibility mapping
        compatibility: dict[str, dict[AgentType, AgentType | None]] = {
            "claude": {
                AgentType.AGENT: AgentType.AGENT,
                AgentType.SKILL: AgentType.SKILL,
                AgentType.MCP_SERVER: AgentType.AGENT,  # Convert MCP to agent
                AgentType.FUNCTION: AgentType.AGENT,
            },
            "gemini": {
                AgentType.MCP_SERVER: AgentType.MCP_SERVER,
                # Gemini only supports MCP servers - others return None
            },
            "openai": {
                AgentType.AGENT: AgentType.AGENT,
                AgentType.SKILL: AgentType.AGENT,
                AgentType.MCP_SERVER: AgentType.MCP_SERVER,
                AgentType.FUNCTION: AgentType.AGENT,
            },
        }

        vendor_map = compatibility.get(target_vendor, {})
        return vendor_map.get(source_type)

    def get_agent(self, name: str, vendor_id: str) -> Agent | None:
        """Get a specific agent by name and vendor.

        Args:
            name: Name of the agent.
            vendor_id: Vendor identifier.

        Returns:
            Agent if found, None otherwise.
        """
        result = self.list_all_agents(vendor_filter=vendor_id)
        for agent in result.agents:
            if agent.name == name:
                return agent
        return None

    def delete_agent(
        self,
        name: str,
        vendor_id: str,
        *,
        progress_callback: Callable[[str], None] | None = None,
    ) -> tuple[bool, str]:
        """Delete an agent.

        Args:
            name: Name of the agent to delete.
            vendor_id: Vendor identifier.
            progress_callback: Optional callback for progress updates.

        Returns:
            Tuple of (success, message).
        """
        agent = self.get_agent(name, vendor_id)
        if not agent:
            return False, f"Agent '{name}' not found in {vendor_id}"

        if not agent.file_path:
            return False, "Agent has no associated file"

        if progress_callback:
            progress_callback(f"Deleting {agent.file_path}")

        try:
            agent.file_path.unlink()
        except OSError as e:
            return False, str(e)
        else:
            return True, f"Deleted {agent.file_path}"
