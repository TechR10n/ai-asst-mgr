# parallel-task-decomposer

**Auto-invoked when:** Planning parallel development work, assigning tasks to agents, or optimizing multi-agent workload distribution

**Purpose:** Intelligently decompose complex features into parallelizable tasks, analyze dependencies, assign work optimally across 3 agents, and minimize merge conflicts

---

## Capabilities

1. **Task Dependency Analysis**
   - Parse task requirements and identify dependencies
   - Build dependency graph (which tasks must complete first)
   - Detect circular dependencies
   - Find parallelizable task clusters

2. **Optimal Worktree Assignment**
   - Assign tasks to agents to minimize conflicts
   - Balance workload across 3 agents
   - Consider agent strengths/specializations
   - Maximize parallel execution

3. **Load Balancing**
   - Distribute hours evenly across agents
   - Prevent bottlenecks (one agent blocking others)
   - Rebalance if agent completes early
   - Track utilization per agent

4. **Conflict-Free Task Partitioning**
   - Identify tasks that modify same files
   - Assign conflicting tasks to same agent OR sequence them
   - Minimize file-level conflicts
   - Predict merge complexity

5. **Task Completion Estimation**
   - Estimate hours per task based on complexity
   - Predict total parallel execution time
   - Calculate theoretical speedup (3x possible)
   - Identify critical path (longest sequence)

---

## When to Invoke

### Automatically Invoke When:
- Starting new development phase (e.g., Phase 4)
- Planning large feature spanning multiple issues
- Orchestrator needs to assign 3+ tasks
- Rebalancing work mid-sprint

### Manually Invoke For:
- Estimating parallel development feasibility
- Planning optimal task breakdown
- Analyzing dependency complexity
- Optimizing assignment strategy

---

## Input Requirements

Provide one of:
1. **Phase description** (e.g., "Phase 4: Audit System - 7 issues")
2. **List of GitHub issues** with titles and descriptions
3. **Feature requirements** for decomposition
4. **Existing task assignments** for rebalancing

---

## Workflow

### Phase 1: Task Analysis
1. Read task descriptions (from issues or requirements)
2. Extract key attributes:
   - Estimated complexity (small/medium/large)
   - Files likely to be modified
   - Dependencies on other tasks
   - Required skills/knowledge
3. Generate task catalog

### Phase 2: Dependency Mapping
1. For each task, identify dependencies:
   - **Hard dependencies**: "Must complete A before B"
   - **Soft dependencies**: "B benefits from A being done first"
   - **No dependency**: "Can do in parallel"
2. Build directed acyclic graph (DAG)
3. Detect conflicts:
   - Tasks modifying same files
   - Tasks with shared infrastructure
4. Calculate critical path

### Phase 3: Task Clustering
1. Group tasks by:
   - **Dependency levels**: L0 (no deps), L1 (depends on L0), etc.
   - **File proximity**: Tasks touching same modules
   - **Skill requirements**: Frontend vs backend vs infrastructure
2. Identify optimal clusters for 3 agents
3. Ensure each cluster is roughly equal in effort

### Phase 4: Agent Assignment
1. For each cluster:
   - Assign to agent with capacity
   - Consider agent's current workload
   - Ensure no agent has > 40% of total work
   - Minimize conflicts between assignments
2. Generate assignment plan
3. Validate balancing

### Phase 5: Timeline Projection
1. For each agent, calculate serial time:
   - Sum hours for assigned tasks
2. Calculate parallel completion time:
   - Max(agent1_hours, agent2_hours, agent3_hours)
3. Identify critical path:
   - Longest dependency chain
4. Calculate theoretical speedup:
   - Serial time / Parallel time

### Phase 6: Recommendation
1. Output optimal task assignments
2. Provide dependency diagram
3. Show projected timeline
4. Suggest improvements
5. Flag potential issues

---

## Task Dependency Analysis Algorithm

### Dependency Detection
```python
# Analyze task descriptions for dependencies
dependencies = []

for task in tasks:
    # Explicit dependencies (in issue description)
    if "depends on #" in task.description:
        dep_issue = extract_issue_number(task.description)
        dependencies.append((dep_issue, task.number))

    # Implicit dependencies (same module)
    for other_task in tasks:
        if task.module == other_task.module and task != other_task:
            # If one creates and other uses, that's a dependency
            if other_task.action == "create" and task.action == "use":
                dependencies.append((other_task.number, task.number))

# Build DAG
dag = DirectedGraph()
for dep_from, dep_to in dependencies:
    dag.add_edge(dep_from, dep_to)

# Topological sort to find levels
levels = dag.topological_levels()
# Level 0: No dependencies (can start immediately)
# Level 1: Depends only on Level 0
# Level 2: Depends on Level 0 or 1, etc.
```

### Conflict Prediction
```python
# Detect file-level conflicts
conflicts = []

for task1, task2 in combinations(tasks, 2):
    # Predict which files each task will modify
    files1 = predict_modified_files(task1)
    files2 = predict_modified_files(task2)

    # Check overlap
    overlap = files1 & files2
    if overlap:
        conflicts.append({
            "task1": task1.number,
            "task2": task2.number,
            "files": overlap,
            "severity": len(overlap)  # More files = worse conflict
        })

# Sort by severity
conflicts.sort(key=lambda x: x["severity"], reverse=True)
```

### Load Balancing
```python
# Assign tasks to agents to balance load
agents = {1: [], 2: [], 3: []}
agent_hours = {1: 0.0, 2: 0.0, 3: 0.0}

# Sort tasks by dependency level (do L0 first, then L1, etc.)
sorted_tasks = sort_by_level(tasks)

for task in sorted_tasks:
    # Find agent with least work
    min_agent = min(agent_hours, key=agent_hours.get)

    # Check if assigning to this agent creates conflicts
    conflict_score = calculate_conflict_score(task, agents[min_agent])

    # If high conflict, try next agent
    if conflict_score > THRESHOLD:
        # Try second-least-loaded agent
        agents_by_load = sorted(agent_hours, key=agent_hours.get)
        min_agent = agents_by_load[1] if conflict_score_ok(task, agents_by_load[1]) else agents_by_load[2]

    # Assign
    agents[min_agent].append(task)
    agent_hours[min_agent] += task.estimated_hours

# Validate balance
max_hours = max(agent_hours.values())
min_hours = min(agent_hours.values())
imbalance = (max_hours - min_hours) / max_hours

if imbalance > 0.3:  # More than 30% imbalance
    # Rebalance by moving tasks
    rebalance_assignments(agents, agent_hours)
```

---

## Task Assignment Patterns

### Pattern 1: Sequential Dependencies
```
Task A (foundation) → Task B (builds on A) → Task C (builds on B)

Assignment:
  - Agent 1: Task A (2h)
  - Agent 2: Task B (2h) - waits for A
  - Agent 3: Task C (2h) - waits for B

Timeline:
  0-2h: Agent 1 works (Agents 2,3 idle)
  2-4h: Agent 2 works (Agents 1,3 idle)
  4-6h: Agent 3 works (Agents 1,2 idle)
  Total: 6 hours (no speedup - fully sequential)

⚠️ Avoid this pattern - poor parallelization!
```

### Pattern 2: Parallel Independent Tasks
```
Task A (CLI command 1)
Task B (CLI command 2)
Task C (CLI command 3)

Assignment:
  - Agent 1: Task A (2h)
  - Agent 2: Task B (2h)
  - Agent 3: Task C (2h)

Timeline:
  0-2h: All agents work in parallel
  Total: 2 hours (3x speedup!)

✅ Ideal pattern - maximize parallelization!
```

### Pattern 3: Mixed Dependencies
```
Task A (foundation) → Task B, C, D (build on A)

Assignment:
  - Agent 1: Task A (2h)
  - Agent 2: Task B (2h) - waits for A
  - Agent 3: Task C (2h) - waits for A

Timeline:
  0-2h: Agent 1 works on A (Agents 2,3 idle)
  2-4h: Agents 2,3 work on B,C in parallel (Agent 1 idle)
  Total: 4 hours (1.5x speedup)

✅ Acceptable - some parallelization after foundation
```

### Pattern 4: Conflict Avoidance
```
Task A modifies: cli.py, test_cli.py
Task B modifies: cli.py, test_cli.py
Task C modifies: adapters.py, test_adapters.py

Assignment:
  - Agent 1: Task A + Task B (4h) - Same files, assign to one agent
  - Agent 2: Task C (2h)
  - Agent 3: (available for other work)

Rationale:
  - Assigning A and B to different agents would cause merge conflicts
  - Better to serialize A→B on one agent
  - Agent 3 can work on independent tasks

✅ Conflict-aware assignment
```

---

## Example Task Decomposition

### Scenario: Phase 4 - Audit System (7 issues)

**Input Tasks:**
1. Issue #22: Create audit framework (3h)
2. Issue #23: Implement ClaudeAuditor (2h)
3. Issue #24: Implement GeminiAuditor (2h)
4. Issue #25: Implement CodexAuditor (2h)
5. Issue #26: Add audit CLI command (2h)
6. Issue #27: Add audit tests (2h)
7. Issue #28: Update documentation (1h)

**Dependency Analysis:**
```
Level 0 (no dependencies):
  - Issue #22 (create framework)

Level 1 (depends on framework):
  - Issue #23 (ClaudeAuditor - uses framework)
  - Issue #24 (GeminiAuditor - uses framework)
  - Issue #25 (CodexAuditor - uses framework)

Level 2 (depends on auditors):
  - Issue #26 (CLI command - uses all auditors)
  - Issue #27 (tests - tests all components)

Level 3 (depends on complete feature):
  - Issue #28 (documentation - documents final feature)
```

**File Conflict Prediction:**
```
Issue #22: src/ai_asst_mgr/audit/framework.py, tests/unit/test_audit_framework.py
Issue #23: src/ai_asst_mgr/audit/claude.py, tests/unit/test_claude_auditor.py
Issue #24: src/ai_asst_mgr/audit/gemini.py, tests/unit/test_gemini_auditor.py
Issue #25: src/ai_asst_mgr/audit/codex.py, tests/unit/test_codex_auditor.py
Issue #26: src/ai_asst_mgr/cli/audit.py, tests/unit/test_audit_cli.py
Issue #27: tests/integration/test_audit_integration.py
Issue #28: docs/audit.md

Conflicts detected:
  - None! Each task modifies different files (ideal)
```

**Optimal Assignment:**
```
Agent 1:
  - Issue #22: Create audit framework (3h) [Level 0]
  - Issue #23: Implement ClaudeAuditor (2h) [Level 1]
  Total: 5h

Agent 2:
  - Issue #24: Implement GeminiAuditor (2h) [Level 1 - waits for #22]
  - Issue #26: Add audit CLI command (2h) [Level 2 - waits for #23, #24, #25]
  Total: 4h

Agent 3:
  - Issue #25: Implement CodexAuditor (2h) [Level 1 - waits for #22]
  - Issue #27: Add audit tests (2h) [Level 2 - waits for all]
  - Issue #28: Update documentation (1h) [Level 3 - waits for all]
  Total: 5h

Load Balance:
  - Agent 1: 5h (35.7%)
  - Agent 2: 4h (28.6%)
  - Agent 3: 5h (35.7%)
  - Imbalance: 7% (acceptable, < 30% threshold)
```

**Timeline Projection:**
```
Phase 0-3h (Agent 1 creates framework):
  ✅ Agent 1: Issue #22 (framework)
  ⏸  Agents 2, 3: Waiting for framework

Phase 3-5h (All agents implement auditors in parallel):
  ✅ Agent 1: Issue #23 (ClaudeAuditor)
  ✅ Agent 2: Issue #24 (GeminiAuditor)
  ✅ Agent 3: Issue #25 (CodexAuditor)

Phase 5-7h (Agents work on CLI and tests):
  ⏸  Agent 1: Done
  ✅ Agent 2: Issue #26 (CLI command)
  ✅ Agent 3: Issue #27 (tests)

Phase 7-8h (Documentation):
  ⏸  Agents 1, 2: Done
  ✅ Agent 3: Issue #28 (docs)

Total Parallel Time: 8 hours
Total Serial Time: 14 hours (sum of all tasks)
Speedup: 1.75x (not quite 3x due to dependencies)
Efficiency: 58% (14h work / 8h time / 3 agents)
```

**Merge Strategy:**
```
Merge Order:
  1. Agent 1 (framework + ClaudeAuditor) - Foundation, must go first
  2. Agent 2 (GeminiAuditor + CLI) - Builds on Agent 1
  3. Agent 3 (CodexAuditor + tests + docs) - Validates everything

Expected Conflicts:
  - None (all different files)

Coverage Validation:
  - Agent 1: Framework + Claude auditor (should have 95%+ coverage)
  - Agent 2: Gemini auditor + CLI (should have 95%+ coverage)
  - Agent 3: Codex auditor + integration tests (boosts combined coverage)
```

---

## Quality Gates for Task Decomposition

### Assignment Quality
- [ ] Load balanced within 30% (max - min / max < 0.3)
- [ ] No agent idle for > 50% of project duration
- [ ] Critical path optimized (shortest possible)
- [ ] File conflicts minimized (< 3 conflict zones)
- [ ] Dependencies respected (no circular deps)

### Parallelization Quality
- [ ] Speedup >= 1.5x (parallel vs serial time)
- [ ] Efficiency >= 50% (utilization across agents)
- [ ] At least 2 agents working simultaneously > 60% of time
- [ ] No more than 3 dependency levels

### Conflict Prevention
- [ ] Tasks modifying same files assigned to same agent
- [ ] Merge order calculated upfront
- [ ] Coverage impact predicted
- [ ] Integration risks identified

---

## Integration with Orchestrator

Enhance `orchestrator.py` to call this skill for assignment planning:

```python
def plan_phase_assignments(phase_issues: list[dict]) -> dict:
    """Plan optimal task assignments for a development phase.

    Args:
        phase_issues: List of issue dicts with number, title, description.

    Returns:
        Assignment plan with tasks per agent and timeline.
    """
    result = invoke_skill("parallel-task-decomposer", {
        "issues": phase_issues,
        "num_agents": 3
    })

    # Apply assignments to orchestrator
    for agent_id, tasks in result.assignments.items():
        for task in tasks:
            orchestrator.assign_task(
                agent_id=agent_id,
                issue_number=task.number,
                title=task.title,
                estimated_hours=task.hours
            )

    # Store merge order
    orchestrator.state["merge_order"] = result.merge_order
    orchestrator._save_state()

    return result
```

---

## Success Metrics

Track these for continuous improvement:

1. **Speedup Achieved**
   - Parallel time vs serial time
   - Phase 3 actual: 1.86x speedup
   - Target: >= 2.0x speedup

2. **Load Balance Quality**
   - Max imbalance percentage
   - Phase 3 actual: < 10% imbalance
   - Target: < 20% imbalance

3. **Conflict Prediction Accuracy**
   - Predicted conflicts vs actual conflicts
   - Phase 3: 2 predicted, 2 actual (100% accuracy)
   - Target: >= 80% accuracy

4. **Idle Time Minimization**
   - Agent idle time percentage
   - Phase 3: ~40% idle time (agents waiting for foundation)
   - Target: < 30% idle time

---

## Error Handling

### Circular Dependencies Detected
```
❌ Circular dependency detected:
  Issue #10 depends on #11
  Issue #11 depends on #12
  Issue #12 depends on #10

Cannot decompose - fix issue dependencies first.

Suggestion:
  - Review issue #12 - does it really need #10?
  - Consider breaking #12 into two sub-tasks
```

### Unbalanceable Workload
```
⚠️  Cannot balance workload within 30% threshold

Current best assignment:
  - Agent 1: 8h (53%)
  - Agent 2: 4h (27%)
  - Agent 3: 3h (20%)
  - Imbalance: 53%

Recommendation:
  - Break Issue #5 (currently 6h) into 2 smaller tasks
  - This would enable better distribution
```

### High Conflict Risk
```
⚠️  High merge conflict risk detected

Conflicting tasks:
  - Issue #14 and #15 both modify cli.py extensively
  - Issue #16 and #17 both modify adapters/base.py

Assignment strategy:
  ✅ Assigned #14 and #15 to Agent 1 (serialize to avoid conflict)
  ✅ Assigned #16 to Agent 2, #17 to Agent 3 (will require merge coordination)

Recommendation:
  - Use parallel-merge-coordinator skill for #16/#17 merge
  - Agent 2 merges first, then Agent 3
```

---

## Future Enhancements

### v1.1: Machine Learning-Based Estimation
- Train on historical task completion times
- Improve hour estimates based on actual data
- Detect patterns in task complexity

### v1.2: Dynamic Rebalancing
- Monitor agent progress in real-time
- Reassign tasks if agent finishes early
- Optimize for minimal total time

### v1.3: Skill-Based Assignment
- Track agent strengths (frontend, backend, testing)
- Assign tasks to agents with relevant expertise
- Learn from past performance

### v1.4: Dependency Auto-Detection
- Use AST analysis to detect code dependencies
- Automatically infer task dependencies from code structure
- Build dependency graph from codebase analysis

---

## Related Skills

- **parallel-merge-coordinator** - Executes the merge strategy planned here
- **test-coverage-enforcer** - Validates coverage impact predicted here
- **project-planning-assistant** - Higher-level phase planning

---

## Implementation Notes

This skill requires:
- Graph algorithms (topological sort, DAG analysis)
- Load balancing heuristics
- File dependency prediction
- Timeline calculation

Tools available: Bash, Read, Write, Edit, Grep, Glob

---

**Invoke this skill to optimally decompose and assign parallel development tasks!**
