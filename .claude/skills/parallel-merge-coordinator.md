# parallel-merge-coordinator

**Auto-invoked when:** Merging multiple parallel agent branches, resolving merge conflicts, or validating combined code quality

**Purpose:** Intelligently coordinate and resolve multi-agent merge conflicts with semantic analysis and automated resolution where possible

---

## Capabilities

1. **Semantic Conflict Detection**
   - Analyze actual code changes, not just file names
   - Identify overlapping line ranges
   - Detect function/class naming collisions
   - Find import conflicts

2. **Automated Conflict Resolution**
   - Combine imports intelligently
   - Preserve all functionality
   - Merge helper functions without collision
   - Integrate test suites

3. **Optimal Merge Ordering**
   - Calculate best merge sequence based on dependencies
   - Identify foundation code vs consumers
   - Minimize conflict complexity

4. **Pre-Merge Validation**
   - Dry-run merges before committing
   - Run combined test suites
   - Validate combined coverage
   - Check quality gates on merged code

5. **Coverage Gap Detection**
   - Predict combined coverage before merge
   - Identify lines that will lose coverage
   - Suggest test cases to add

---

## When to Invoke

### Automatically Invoke When:
- Orchestrator detects file-level conflicts between agents
- About to merge parallel agent branches
- CI shows coverage dropped below 95% after merge
- Integration tests fail after merge

### Manually Invoke For:
- Planning merge strategy before starting
- Reviewing complex merge conflicts
- Validating multi-agent code quality
- Post-merge troubleshooting

---

## Input Requirements

Provide one of:
1. **Agent branch names** to merge (e.g., `parallel-dev/agent-1`, `parallel-dev/agent-2`)
2. **Conflict description** from git merge attempt
3. **Coverage gap report** from CI failure
4. **Orchestrator state file** (agent_tracker.json)

---

## Workflow

### Phase 1: Analysis
1. Read orchestrator state to understand agent assignments
2. Analyze git diffs for each agent branch
3. Detect semantic conflicts (not just file-level)
4. Calculate optimal merge order

### Phase 2: Pre-Merge Validation
1. For each agent (in optimal order):
   - Dry-run merge with main
   - Identify conflicts
   - Classify conflict types (imports, functions, tests)
2. Predict combined test coverage
3. Identify potential integration issues

### Phase 3: Merge Execution
1. Merge agents sequentially in optimal order
2. For each merge:
   - Resolve conflicts automatically where possible
   - Flag conflicts needing manual review
   - Run combined tests
   - Validate coverage hasn't dropped
3. After all merges:
   - Run full test suite
   - Check combined coverage
   - Verify quality gates

### Phase 4: Gap Filling
1. If coverage < 95%:
   - Identify uncovered lines
   - Determine which agent's code needs tests
   - Generate or suggest test cases
   - Add tests and re-validate

### Phase 5: Reporting
1. Summary of merges performed
2. Conflicts resolved (automated vs manual)
3. Final coverage report
4. Quality gate status
5. Recommendations for future parallel work

---

## Semantic Conflict Detection Algorithm

### Import Conflicts
```python
# Agent 1 adds:
from ai_asst_mgr.adapters.base import VendorStatus

# Agent 2 adds:
from ai_asst_mgr.vendors import VendorRegistry

# Resolution: Combine and alphabetize
from ai_asst_mgr.adapters.base import VendorStatus
from ai_asst_mgr.vendors import VendorRegistry
```

### Function Overlaps
```python
# Detect if agents define same function name
if function_name_in_both_agents:
    if function_signatures_identical:
        # Agents implemented same helper - use one
        resolution = "deduplicate"
    else:
        # Name collision - needs renaming
        resolution = "rename_one"

# Detect if agents modify same existing function
if same_function_modified_by_both:
    # Complex - needs manual review
    resolution = "manual_merge"
```

### Line Range Analysis
```python
# Agent 1 modifies lines 100-150
# Agent 2 modifies lines 140-200
# Overlap: lines 140-150 → potential conflict

overlap = range_intersection(agent1_lines, agent2_lines)
if overlap:
    analyze_overlap_context()  # What's being changed?
```

---

## Automated Resolution Patterns

### Pattern 1: Non-Overlapping Additions
```python
# Agent 1 adds function at line 100
# Agent 2 adds function at line 200
# Resolution: Keep both, no conflict
```

### Pattern 2: Import Merging
```python
# Combine all imports from both agents
# Remove duplicates
# Alphabetize
# Group by: stdlib, third-party, local
```

### Pattern 3: Helper Function Grouping
```python
# Group helpers by command
# status helpers
def _get_status_display(): ...  # Agent 1

# health helpers
def _format_health_status(): ...  # Agent 2

# doctor helpers
def _check_python_version(): ...  # Agent 3
```

### Pattern 4: Test Class Merging
```python
# Keep test classes separate
class TestStatusCommand:  # Agent 1 tests
    ...

class TestHealthCommand:  # Agent 2 tests
    ...
```

---

## Quality Gates for Merged Code

After each merge, verify:
- [ ] All tests passing
- [ ] Combined coverage >= 95%
- [ ] mypy --strict passes
- [ ] ruff check passes
- [ ] bandit passes
- [ ] No duplicate code introduced
- [ ] Imports properly organized
- [ ] Documentation updated

---

## Example Usage

### Scenario 1: Merge 3 Parallel Agent Branches

```bash
# User invokes skill
# Skill reads orchestrator state
# Analyzes agent-1, agent-2, agent-3 branches

# Output:
Optimal merge order:
  1. agent-1 (foundation code, fewest conflicts)
  2. agent-2 (builds on agent-1 types)
  3. agent-3 (most complex, benefits from 1+2 merged)

Predicted conflicts:
  - agent-2 vs agent-1: 2 import conflicts (auto-resolvable)
  - agent-3 vs main: 5 function additions (no conflicts)

Merging agent-1... ✅ Clean merge
Merging agent-2... ⚠️ Conflicts detected
  - src/ai_asst_mgr/cli.py: Import conflict (auto-resolved)
  - tests/unit/test_cli.py: Test class additions (auto-merged)
Merging agent-3... ⚠️ Conflicts detected
  - src/ai_asst_mgr/cli.py: Function additions (auto-resolved)

Running combined tests... ✅ 256 tests passing
Checking combined coverage... ⚠️ 94.89% (below 95%)

Identifying coverage gaps...
  - Lines 304-314: Python version check (agent-3 code)
  - Lines 335-344: Missing dependency path (agent-3 code)

Suggested tests:
  1. test_doctor_command_python_version_too_low()
  2. test_doctor_command_missing_dependency()

Adding suggested tests... ✅
Re-running coverage... ✅ 96.30%

✅ All merges complete and validated!
```

---

## Configuration

Optional settings in orchestrator state or environment:

```json
{
  "merge_strategy": "sequential",  // or "rebase", "octopus"
  "conflict_resolution": "auto",   // or "manual", "interactive"
  "coverage_threshold": 95.0,
  "auto_fix_gaps": true,
  "dry_run": false
}
```

---

## Integration with Orchestrator

Enhance `orchestrator.py` to call this skill:

```python
# After detecting conflicts
if orchestrator.detect_conflicts():
    # Invoke parallel-merge-coordinator skill
    result = invoke_skill("parallel-merge-coordinator", {
        "agent_branches": ["parallel-dev/agent-1", "parallel-dev/agent-2"],
        "target_branch": "main",
        "coverage_threshold": 95.0
    })
```

---

## Success Metrics

Track these for continuous improvement:

1. **Conflict Resolution Rate**
   - Auto-resolved: X%
   - Manual review needed: Y%
   - Target: 80%+ auto-resolved

2. **Merge Time**
   - Time from start to completion
   - Phase 3 baseline: 30 minutes
   - Target: < 5 minutes

3. **Coverage Gap Prevention**
   - Gaps detected pre-merge: X
   - Gaps requiring fixes post-merge: Y
   - Target: 100% pre-detection

4. **CI Pass Rate**
   - First attempt pass rate
   - Phase 3 baseline: 50% (1/2 attempts)
   - Target: 100% (pass on first try)

---

## Error Handling

### Unresolvable Conflicts
```
⚠️ Manual review required for:
  - src/ai_asst_mgr/cli.py lines 150-200
  - Both agents modified same function logic

Pausing merge. Please resolve manually:
  1. Review conflict markers
  2. Preserve all functionality
  3. Run tests after resolution
  4. Resume: orchestrator.py resume-merge
```

### Coverage Drop
```
⚠️ Coverage dropped to 94.5% after merge

Attempting auto-fix...
  - Added test_function_a(): ✅ +0.3%
  - Added test_function_b(): ✅ +0.4%
  - Coverage now: 95.2% ✅

Manual fixes needed for:
  - Lines 500-510: Complex edge case
  Suggestion: Add test_edge_case_x()
```

### Test Failures
```
❌ 3 tests failing after merge:
  - test_integration_a() - Agents have conflicting assumptions
  - test_integration_b() - Import error
  - test_integration_c() - Mock conflict

Aborting merge. Recommendations:
  1. Agents should coordinate on shared mocks
  2. Define integration contract upfront
  3. Run cross-agent integration tests before merge
```

---

## Future Enhancements

### v1.1: Machine Learning-Based Conflict Prediction
- Train on historical conflicts
- Predict conflict probability
- Suggest optimal task assignments upfront

### v1.2: Interactive Merge Mode
- Step-by-step merge with user confirmation
- Show diffs before applying changes
- Undo/redo capability

### v1.3: Parallel Test Execution
- Run tests for each agent simultaneously during merge
- Faster validation
- Early conflict detection

### v1.4: Coverage-Driven Test Generation
- Use LLM to generate tests for uncovered lines
- Automatically add to test suite
- Validate generated tests work

---

## Related Skills

- **test-coverage-enforcer** - Validates coverage requirements
- **parallel-task-decomposer** - Optimizes task assignment to prevent conflicts
- **code-organization-architect** - Designs structure for parallelizability

---

## Implementation Notes

This skill requires:
- Git operations (merge, diff, conflict detection)
- Python AST parsing (for semantic analysis)
- Test execution (pytest)
- Coverage analysis (coverage.py)
- Quality gate validation (mypy, ruff, bandit)

Tools available: Bash, Read, Write, Edit, Grep, Glob

---

**Invoke this skill anytime you need intelligent multi-agent merge coordination!**
