# Parallel Development Playbook

**Version:** 1.0
**Last Updated:** 2025-11-24
**Lessons From:** Phase 3 CLI implementation (3 parallel agents)

---

## 🎯 When to Use Parallel Development

### ✅ Good Candidates for Parallel

- **Independent Features** - Commands, endpoints, utilities with minimal interaction
- **Vertical Slices** - Complete features (UI + logic + tests) per agent
- **Known Patterns** - Repeating similar work across different modules
- **High-Value Work** - 6+ hours of sequential work → 37% time savings
- **Clear Boundaries** - Well-defined interfaces between components

### ❌ Poor Candidates for Parallel

- **Tightly Coupled Code** - Shared state, complex dependencies
- **Unclear Requirements** - Needs exploration and iteration
- **Refactoring** - Touching same code for restructuring
- **Critical Path Work** - One task blocks all others
- **Experimental Work** - High uncertainty, frequent pivots

---

## 📊 Decision Matrix

| Criteria | Sequential | Parallel (2 agents) | Parallel (3 agents) |
|----------|-----------|--------------------|--------------------|
| **Est. Time** | < 4 hours | 4-8 hours | 8+ hours |
| **Task Independence** | N/A | High | Very High |
| **File Overlap** | N/A | < 20% | < 10% |
| **Complexity** | Any | Low-Medium | Low |
| **Risk Tolerance** | Low | Medium | High |

---

## 🏗️ Task Assignment Strategies

### Strategy 1: Vertical Slicing (Recommended for Features)

**Assign:** Complete feature per agent

**Example (Phase 3):**
- Agent 1: `status` command + helpers + tests
- Agent 2: `health` command + helpers + tests
- Agent 3: `doctor` command + helpers + tests

**Pros:**
- Each agent owns end-to-end functionality
- Easy to test in isolation
- Clear responsibility boundaries

**Cons:**
- All agents touch same files (cli.py, test_cli.py)
- Merge conflicts inevitable
- Requires coordination on file organization

**Best For:**
- Adding multiple commands/endpoints
- Plugin-style architectures
- Microservices-like modules

---

### Strategy 2: Horizontal Slicing

**Assign:** By architectural layer

**Example:**
- Agent 1: API/CLI layer
- Agent 2: Business logic layer
- Agent 3: Data access layer

**Pros:**
- Different files per agent
- Minimal merge conflicts
- Clear layer boundaries

**Cons:**
- Agents depend on each other
- Integration testing complex
- Requires API contracts upfront

**Best For:**
- Greenfield architectures
- When APIs are well-defined
- Refactoring existing code

---

### Strategy 3: Hybrid (Staged)

**Assign:** Foundation first, then parallel features

**Example:**
- **Stage 1:** Agent 1 creates shared infrastructure
- **Stage 2:** Agent 2 + Agent 3 build features using infrastructure

**Pros:**
- Manages dependencies
- Reduces conflicts
- Quality foundation

**Cons:**
- Not fully parallel
- Time savings reduced
- Requires staging coordination

**Best For:**
- Complex features with shared components
- When foundation is unclear
- Risk-averse projects

---

### Strategy 4: File-Based

**Assign:** By file or module

**Example:**
- Agent 1: `src/module_a.py`
- Agent 2: `src/module_b.py`
- Agent 3: `src/module_c.py`

**Pros:**
- Zero merge conflicts
- Maximum parallelism
- Simple coordination

**Cons:**
- Requires modular architecture
- May not balance workload
- Integration testing needed

**Best For:**
- Microservices
- Plugin architectures
- Independent modules

---

## 🔀 Merge Strategies

### Sequential Merge (Recommended)

**Process:**
1. Merge Agent 1 → main
2. Merge Agent 2 → main (resolve conflicts)
3. Merge Agent 3 → main (resolve conflicts)

**Order Priority:**
1. **Foundation first** - Base classes, types, utilities
2. **Least conflicts** - Agent with fewest file changes
3. **Dependencies** - Consumers after providers

**Example (Phase 3):**
```
Agent 1 (status - foundation types) → main ✅ Clean merge
Agent 2 (health - uses types) → main ⚠️ Conflicts in cli.py
Agent 3 (doctor - complex) → main ⚠️ Conflicts in cli.py + tests
```

---

### Rebase Strategy (Advanced)

**Process:**
1. Agent 1 → main
2. Agent 2 rebases on main (includes Agent 1)
3. Agent 2 → main
4. Agent 3 rebases on main (includes Agent 1 + 2)
5. Agent 3 → main

**Pros:**
- Cleaner history
- Each agent resolves own conflicts
- Linear commit graph

**Cons:**
- More complex
- Agents need to retest after rebase
- Requires git expertise

---

### Octopus Merge (Experimental)

**Process:**
1. Merge all 3 agents simultaneously
2. Resolve all conflicts at once

**Pros:**
- Single merge commit
- Fastest process

**Cons:**
- Complex conflict resolution
- High cognitive load
- Risky for large changes

**When to Use:** Only for trivial conflicts (different files)

---

## 🛡️ Conflict Prevention

### 1. File Organization Conventions

**Commands in CLI Files:**
```python
# ❌ Don't insert randomly
def command_a(): ...
def new_command(): ...  # Agent 1 adds here
def command_b(): ...

# ✅ Do append at end
def command_a(): ...
def command_b(): ...
def new_command_c(): ...  # Agent 1 adds here
def new_command_d(): ...  # Agent 2 adds here
def new_command_e(): ...  # Agent 3 adds here
```

**Helper Functions:**
```python
# ✅ Group by command
# status command
def _get_status_display(): ...
def _get_notes_for_status(): ...

# health command
def _format_health_status(): ...
def _format_issues(): ...

# doctor command
def _check_python_version(): ...
def _check_dependencies(): ...
```

**Imports:**
```python
# ✅ Alphabetize to reduce conflicts
from pathlib import Path
import platform
import shutil
import sys
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ai_asst_mgr.adapters.base import VendorStatus
from ai_asst_mgr.vendors import VendorRegistry
```

**Tests:**
```python
# ✅ Class-based organization
class TestStatusCommand:
    """All status command tests."""
    def test_status_all_vendors(self): ...
    def test_status_single_vendor(self): ...

class TestHealthCommand:
    """All health command tests."""
    def test_health_all_vendors(self): ...
    def test_health_with_issues(self): ...

class TestDoctorCommand:
    """All doctor command tests."""
    def test_doctor_no_issues(self): ...
    def test_doctor_with_fix_flag(self): ...
```

---

### 2. Pre-Coordination Checklist

Before assigning tasks:

- [ ] Analyze which files each agent will modify
- [ ] Identify shared utilities needed
- [ ] Define file organization strategy
- [ ] Agree on naming conventions
- [ ] Establish test organization pattern
- [ ] Set up shared fixtures/utilities
- [ ] Document coordination points

---

### 3. Work-in-Progress Communication

Use orchestrator comments:
```bash
# Agent 1 reserves space
orchestrator.py comment 1 "Adding _get_status_display() helper at line 70"

# Agent 2 sees this, adjusts
orchestrator.py comment 2 "Adding _format_health_status() helper at line 150"
```

---

## 🧪 Testing Strategy

### Per-Agent Testing

Each agent must:
1. ✅ Run full test suite in their worktree
2. ✅ Achieve 95%+ coverage independently
3. ✅ Pass all quality gates (mypy, ruff, bandit)
4. ✅ Verify no regressions in existing tests

**Command:**
```bash
cd /path/to/agent-worktree
uv run pytest -v --cov=ai_asst_mgr --cov-fail-under=95
uv run mypy src/ tests/ --strict
uv run ruff check src/ tests/
uv run bandit -r src/
```

---

### Combined Testing (Pre-Merge)

Before merging, validate combined code:

```bash
# Dry-run merge
git merge --no-commit --no-ff parallel-dev/agent-2

# Run combined tests
uv run pytest -v --cov=ai_asst_mgr --cov-fail-under=95

# If passes, complete merge
git commit -m "merge: integrate agent-2 changes"

# If fails, abort and fix
git merge --abort
```

---

### Integration Testing

After all merges, test interactions:

```python
def test_status_and_health_consistency():
    """Ensure status and health commands show consistent vendor info."""
    # Both should use same VendorRegistry
    # Both should show same vendors

def test_doctor_validates_status_requirements():
    """Ensure doctor checks align with status expectations."""
    # Doctor should check for same config files status uses
```

---

## 📈 Quality Gates

### Per-Agent Gates

Before marking task complete:
- [ ] All new code has docstrings (Google style)
- [ ] All functions have type hints
- [ ] Test coverage >= 95%
- [ ] mypy --strict passes
- [ ] ruff check passes
- [ ] bandit security check passes
- [ ] pre-commit hooks pass
- [ ] Documentation updated

### Combined Gates

After all merges:
- [ ] Combined coverage >= 95%
- [ ] No test failures
- [ ] No quality gate regressions
- [ ] All integration tests pass
- [ ] Documentation complete
- [ ] CHANGELOG updated

---

## 🚨 Common Pitfalls

### Pitfall 1: Assuming Clean Merges
**Problem:** "Different commands won't conflict"
**Reality:** Same files, imports, test fixtures → conflicts

**Solution:** Plan for conflicts, use strategies above

---

### Pitfall 2: Testing in Isolation Only
**Problem:** Each agent tests alone, combined coverage drops
**Reality:** Edge cases emerge when features interact

**Solution:** Pre-merge combined testing

---

### Pitfall 3: No Code Review Between Agents
**Problem:** Duplicate code, inconsistent patterns
**Reality:** Each agent makes independent decisions

**Solution:** Cross-agent code review before merge

---

### Pitfall 4: Ignoring File Organization
**Problem:** Random insertion points, naming collisions
**Reality:** Merge conflicts everywhere

**Solution:** Establish conventions upfront

---

### Pitfall 5: Sequential Thinking
**Problem:** "Agent 2 needs Agent 1's code"
**Reality:** Blocks parallelism, defeats purpose

**Solution:** Define interfaces first, implement in parallel

---

## 📋 Templates

### Task Assignment Template

```markdown
## Agent X: [Task Name]

**Objective:** [Clear, specific goal]

**Files to Modify:**
- src/[module].py - Add [specific function]
- tests/unit/test_[module].py - Add [test class]

**Coordination Points:**
- Insert new code at line [X] in [file]
- Use naming pattern: `_command_[verb]_[noun]()`
- Share test fixtures: [fixture list]

**Dependencies:**
- Requires: [What Agent X needs from others]
- Provides: [What Agent X creates for others]

**Success Criteria:**
- [ ] Feature implemented
- [ ] 95%+ test coverage
- [ ] All quality gates pass
- [ ] Documentation updated
```

---

### Merge Checklist Template

```markdown
## Merge Agent X → main

**Pre-Merge:**
- [ ] Agent X tests pass in isolation
- [ ] Agent X coverage >= 95%
- [ ] Agent X quality gates pass
- [ ] Dry-run merge attempted
- [ ] Conflicts identified

**During Merge:**
- [ ] Preserve all functionality
- [ ] Combine all imports
- [ ] Keep all helper functions
- [ ] Integrate all tests
- [ ] Resolve conflicts semantically

**Post-Merge:**
- [ ] Combined tests pass
- [ ] Combined coverage >= 95%
- [ ] No quality gate regressions
- [ ] Integration verified
- [ ] Commit message clear
```

---

## 🎓 Learning Resources

### Phase 3 Case Study

**Task:** Implement 3 CLI commands (status, health, doctor)
**Strategy:** Vertical slicing (one command per agent)
**Outcome:** ✅ Success with lessons learned
**Time:** 7h work in ~4.5h real time (37% savings)
**Challenges:** Merge conflicts, coverage gaps
**Solutions:** See retrospective in `.claude/analysis/phase3-retrospective.md`

---

### Recommended Reading

1. **scripts/parallel-dev/README.md** - Infrastructure guide
2. **.claude/DEVELOPMENT_STANDARDS.md** - Quality requirements
3. **.claude/analysis/phase3-retrospective.md** - Lessons learned
4. **Git worktrees documentation** - https://git-scm.com/docs/git-worktree

---

## 🔄 Continuous Improvement

After each parallel session:

1. **Retrospective**
   - What went well?
   - What could be improved?
   - Specific pain points?

2. **Update Playbook**
   - Add new strategies
   - Document solutions
   - Refine templates

3. **Enhance Tools**
   - Orchestrator improvements
   - New skills creation
   - Automation opportunities

4. **Measure Success**
   - Time savings
   - Conflict resolution time
   - CI pass rate
   - Coverage metrics

---

## 📞 When to Ask for Help

Invoke `parallel-merge-coordinator` skill when:
- Merge conflicts are complex
- Combined coverage drops
- Integration tests fail
- Unsure about merge order

Invoke `parallel-task-decomposer` skill when:
- Planning new parallel work
- Uncertain about task boundaries
- Want conflict prediction

---

**Remember:** Parallel development is a skill. It gets easier with practice and better tools.
