# test-coverage-enforcer

**Auto-invoked when:** Pre-merge coverage validation, detecting coverage gaps, or preventing coverage regression below 95%

**Purpose:** Proactively enforce test coverage requirements across parallel agent development, prevent coverage gaps before merge, and maintain >= 95% coverage threshold

---

## Capabilities

1. **Proactive Coverage Gap Detection**
   - Analyze coverage for each agent branch independently
   - Identify uncovered lines before merge
   - Predict combined coverage across all agents
   - Flag potential regression early

2. **Per-Worktree Coverage Tracking**
   - Run coverage analysis in each agent worktree
   - Track coverage trends over time
   - Compare against baseline (main branch)
   - Detect when agent introduces uncovered code

3. **Pre-Merge Coverage Validation**
   - Validate coverage before allowing merge
   - Simulate combined coverage from multiple agents
   - Ensure 95%+ threshold maintained
   - Block merges that would drop coverage

4. **Automated Test Suggestion Generation**
   - Analyze uncovered code paths
   - Suggest specific test cases needed
   - Generate test templates with fixture patterns
   - Prioritize by complexity and risk

5. **Coverage Regression Prevention**
   - Track coverage baseline from main branch
   - Alert when agent's changes reduce coverage
   - Prevent accidental deletion of tests
   - Validate test quality (not just quantity)

---

## When to Invoke

### Automatically Invoke When:
- Agent completes task (pre-commit validation)
- Before merging agent branch to main
- CI coverage check fails (< 95%)
- Orchestrator detects potential coverage drop
- Agent modifies existing tested code

### Manually Invoke For:
- Auditing current coverage status
- Planning test strategy for new feature
- Investigating coverage regression
- Generating test cases for uncovered code

---

## Input Requirements

Provide one of:
1. **Agent ID** to check (e.g., `1`, `2`, `3`)
2. **Branch name** to validate (e.g., `parallel-dev/agent-1`)
3. **Orchestrator state file** (agent_tracker.json) for multi-agent check
4. **Coverage report** from previous run

---

## Workflow

### Phase 1: Baseline Analysis
1. Run coverage on main branch
2. Record baseline coverage percentage
3. Identify critical paths (must stay covered)
4. Generate baseline report

### Phase 2: Per-Agent Coverage Check
1. For each agent worktree:
   - Run `uv run pytest --cov --cov-report=json`
   - Parse coverage.json
   - Calculate coverage percentage
   - Identify uncovered lines
2. Compare against baseline
3. Flag regression if coverage < baseline

### Phase 3: Gap Identification
1. For each uncovered line:
   - Determine file and line number
   - Extract code context (function, class)
   - Classify code type (edge case, error handling, etc.)
   - Assess criticality (high/medium/low)
2. Group gaps by file and function
3. Prioritize by risk and complexity

### Phase 4: Test Generation
1. For each gap:
   - Analyze code to understand behavior
   - Identify test fixtures needed
   - Generate test case template
   - Suggest assertions
2. Follow project patterns:
   - Use tempfile for filesystem tests
   - Use pytest fixtures consistently
   - One assertion per test concept
   - Clear test names
3. Output suggested tests

### Phase 5: Pre-Merge Validation
1. If merging multiple agents:
   - Simulate combined coverage
   - Check if >= 95% threshold met
   - Identify overlapping test coverage
   - Flag potential gaps from merge
2. Provide go/no-go recommendation
3. List required tests before merge

### Phase 6: Reporting
1. Coverage summary per agent
2. Combined coverage projection
3. List of uncovered lines
4. Suggested test cases
5. Merge recommendation (go/no-go)

---

## Coverage Analysis Algorithm

### Baseline Calculation
```python
# Run coverage on main branch
baseline_result = run_coverage(branch="main")
baseline_pct = baseline_result.percentage  # e.g., 95.92%

# Identify critical modules (must stay >= 95%)
critical_modules = [
    "ai_asst_mgr/adapters/",
    "ai_asst_mgr/vendors/",
    "ai_asst_mgr/cli/",
]
```

### Per-Agent Coverage Check
```python
for agent_id in [1, 2, 3]:
    worktree_path = get_worktree_path(agent_id)

    # Run coverage in agent worktree
    result = run_coverage_in_worktree(worktree_path)

    # Check threshold
    if result.percentage < 95.0:
        flag_agent_coverage_gap(agent_id, result)

    # Check regression vs baseline
    if result.percentage < baseline_pct - 0.5:  # Allow 0.5% tolerance
        flag_coverage_regression(agent_id, baseline_pct, result.percentage)
```

### Combined Coverage Prediction
```python
# Merge coverage data from all agents
combined_lines_covered = set()
combined_lines_total = set()

for agent_id in [1, 2, 3]:
    coverage_data = load_coverage_json(agent_id)
    combined_lines_covered.update(coverage_data.covered_lines)
    combined_lines_total.update(coverage_data.total_lines)

predicted_coverage = len(combined_lines_covered) / len(combined_lines_total) * 100

if predicted_coverage < 95.0:
    # Generate tests to fill gap
    gap = 95.0 - predicted_coverage
    tests_needed = estimate_tests_for_gap(gap)
```

### Gap Prioritization
```python
# Classify uncovered lines by criticality
for line in uncovered_lines:
    context = get_code_context(line)

    if "raise" in context or "Error" in context:
        priority = "high"  # Error handling must be tested
    elif "if" in context or "else" in context:
        priority = "high"  # Branch coverage critical
    elif "return" in context:
        priority = "medium"  # Return paths important
    else:
        priority = "low"  # Simple statements

    gaps.append({"line": line, "priority": priority, "context": context})

# Sort by priority
gaps.sort(key=lambda x: {"high": 0, "medium": 1, "low": 2}[x["priority"]])
```

---

## Automated Test Generation Patterns

### Pattern 1: Error Handling Tests
```python
# Uncovered: Line 304 - raise ValueError("Invalid config")

# Generated test:
def test_function_name_raises_value_error_on_invalid_config() -> None:
    """Test function_name raises ValueError for invalid config."""
    with pytest.raises(ValueError, match="Invalid config"):
        function_name(invalid_input)
```

### Pattern 2: Edge Case Tests
```python
# Uncovered: Line 150 - if len(items) == 0: return []

# Generated test:
def test_function_name_returns_empty_list_for_empty_input() -> None:
    """Test function_name returns empty list when items is empty."""
    result = function_name([])
    assert result == []
```

### Pattern 3: Branch Coverage Tests
```python
# Uncovered: Line 200 - if config.get("debug"): log.debug(...)

# Generated test:
def test_function_name_logs_debug_when_debug_enabled() -> None:
    """Test function_name logs debug info when debug is True."""
    config = {"debug": True}
    with pytest.raises(LogCapture) as log:
        function_name(config)
    assert "debug message" in log.records
```

### Pattern 4: Integration Tests
```python
# Uncovered: Lines 300-310 - Complex workflow

# Generated test:
def test_workflow_integration_happy_path() -> None:
    """Test complete workflow executes successfully."""
    # Setup
    with tempfile.TemporaryDirectory() as temp_dir:
        # Execute workflow
        result = execute_workflow(temp_dir)

        # Verify end-to-end
        assert result.success is True
        assert result.output_file.exists()
```

---

## Quality Gates for Coverage

### Agent-Level Gates
- [ ] Coverage >= 95% for agent's code
- [ ] No regression vs baseline (within 0.5% tolerance)
- [ ] Critical modules >= 95%
- [ ] All error paths tested
- [ ] Branch coverage >= 90%

### Pre-Merge Gates
- [ ] Combined coverage >= 95%
- [ ] No uncovered critical code
- [ ] No test deletions without replacement
- [ ] Integration tests cover agent interactions
- [ ] Coverage trend positive (not declining)

### Post-Merge Gates
- [ ] Main branch coverage >= 95%
- [ ] CI coverage check passes
- [ ] No coverage gaps introduced
- [ ] Coverage report generated and stored

---

## Example Usage

### Scenario 1: Check Agent 1 Coverage Before Merge

```bash
# Invoke skill for Agent 1
# Skill runs coverage analysis

Agent 1 Coverage Report:
  Worktree: /path/to/ai-asst-mgr-worktrees/agent-1
  Branch: parallel-dev/agent-1
  Files modified: 3

Coverage Results:
  ✅ Overall: 96.37% (exceeds 95% threshold)
  ✅ Baseline: 95.92% (no regression)

Module Breakdown:
  ✅ ai_asst_mgr/cli/init.py: 97.5%
  ✅ tests/unit/test_init.py: 100%
  ✅ tests/integration/test_init_integration.py: 95.2%

Uncovered Lines (3):
  1. src/ai_asst_mgr/cli/init.py:304 - Edge case: empty config dict
  2. src/ai_asst_mgr/cli/init.py:305 - Return early path
  3. src/ai_asst_mgr/cli/init.py:450 - Debug logging statement

Suggested Tests:
  1. test_init_command_handles_empty_config() -> None
  2. test_init_command_returns_early_when_already_initialized() -> None
  3. (Line 450 is debug logging - low priority)

Merge Recommendation: ✅ GO
  - Coverage exceeds threshold
  - Only minor gaps (debug logging)
  - Regression check passed
```

### Scenario 2: Multi-Agent Pre-Merge Validation

```bash
# Invoke skill for all 3 agents before merge

Combined Coverage Analysis:
  Agents: 1, 2, 3
  Branches: parallel-dev/agent-1, agent-2, agent-3

Individual Coverage:
  ✅ Agent 1: 96.37%
  ✅ Agent 2: 95.83%
  ⚠️  Agent 3: 94.89% (below threshold!)

Combined Prediction:
  ⚠️  Predicted combined: 94.75% (below 95%!)

Coverage Gaps (Agent 3):
  - Lines 304-314: Python version check logic (10 lines)
  - Lines 335-344: Missing dependency detection (10 lines)

Suggested Tests for Agent 3:
  1. test_doctor_command_detects_python_version_too_low() -> None:
     """Test doctor flags Python < 3.14."""
     with mock.patch("sys.version_info", (3, 13, 0)):
         result = doctor_command()
         assert "Python 3.14+" in result.errors

  2. test_doctor_command_detects_missing_dependencies() -> None:
     """Test doctor identifies missing packages."""
     with mock.patch("importlib.import_module", side_effect=ImportError):
         result = doctor_command()
         assert "Missing dependency" in result.warnings

Merge Recommendation: ❌ NO-GO
  - Combined coverage: 94.75% (need 95%)
  - Agent 3 needs 2 additional tests
  - After adding tests, re-validate before merge
```

### Scenario 3: Coverage Regression Detection

```bash
# Agent 2 modifies existing tested code

Agent 2 Coverage Report:
  ⚠️  Coverage: 93.5% (below 95%)
  ❌ Regression: -2.42% vs baseline (95.92%)

Regression Analysis:
  Deleted file: tests/unit/test_vendor_adapter.py
  Impact: Lost 12 tests covering VendorAdapter base class

Root Cause:
  Agent 2 refactored VendorAdapter but deleted old tests
  without adding equivalent new tests.

Action Required:
  1. Restore deleted tests OR
  2. Add equivalent coverage in new test file

Blocking Merge: YES
  - Coverage regression unacceptable
  - Fix required before merge
```

---

## Configuration

Optional settings in `.coveragerc` or orchestrator state:

```ini
[coverage:run]
branch = True
source = ai_asst_mgr

[coverage:report]
precision = 2
fail_under = 95.0
show_missing = True

[coverage:json]
output = coverage.json
```

Orchestrator integration:
```json
{
  "coverage_enforcement": {
    "threshold": 95.0,
    "baseline_tolerance": 0.5,
    "block_merge_on_failure": true,
    "auto_generate_tests": true,
    "critical_modules": [
      "ai_asst_mgr/adapters/",
      "ai_asst_mgr/vendors/",
      "ai_asst_mgr/cli/"
    ]
  }
}
```

---

## Integration with Orchestrator

Enhance `orchestrator.py` to call this skill automatically:

```python
# Before allowing merge
def pre_merge_validation(agent_id: int) -> bool:
    """Validate agent coverage before merge."""
    result = invoke_skill("test-coverage-enforcer", {
        "agent_id": agent_id,
        "mode": "pre_merge"
    })

    if result.coverage < 95.0:
        print(f"❌ Agent {agent_id} coverage: {result.coverage}%")
        print(f"   Need {result.tests_needed} more tests")
        return False

    return True

# Before merging all agents
def validate_combined_coverage(agent_ids: list[int]) -> bool:
    """Validate combined coverage from multiple agents."""
    result = invoke_skill("test-coverage-enforcer", {
        "agent_ids": agent_ids,
        "mode": "combined_prediction"
    })

    return result.predicted_coverage >= 95.0
```

---

## Success Metrics

Track these for continuous improvement:

1. **Coverage Maintenance**
   - Agents >= 95%: X/3
   - Combined >= 95%: Yes/No
   - Target: 100% agents at 95%+

2. **Regression Prevention**
   - Regressions caught pre-merge: X
   - Regressions that reached main: 0
   - Target: 100% pre-merge detection

3. **Test Generation Quality**
   - Generated tests that passed: X%
   - Generated tests that needed modification: Y%
   - Target: 80%+ generated tests work as-is

4. **Merge Blocking**
   - Merges blocked due to coverage: X
   - False positives (shouldn't have blocked): Y
   - Target: < 5% false positive rate

---

## Error Handling

### Coverage Too Low
```
❌ Coverage: 94.5% (below 95% threshold)

Gap Analysis:
  - Need 0.5% more coverage
  - Approximately 3-4 more test cases

Top Priority Gaps:
  1. src/ai_asst_mgr/cli/config.py:204 (error handling)
  2. src/ai_asst_mgr/cli/config.py:215 (edge case)
  3. src/ai_asst_mgr/cli/config.py:230 (branch coverage)

Blocking merge until coverage >= 95%
```

### Regression Detected
```
❌ Coverage regression: 95.92% → 94.5% (-1.42%)

Cause:
  - Deleted tests: tests/unit/test_old_feature.py (8 tests)
  - Added code: src/ai_asst_mgr/new_feature.py (50 lines, 30 uncovered)

Action:
  1. Restore deleted tests OR prove they're obsolete
  2. Add 5-6 tests for new_feature.py

Do not merge until regression resolved.
```

### Missing Coverage Data
```
⚠️  No coverage data found for Agent 2

Possible causes:
  - Coverage not run in worktree
  - coverage.json missing
  - Tests not executed

Action:
  1. cd /path/to/agent-2
  2. uv run pytest --cov --cov-report=json
  3. Verify coverage.json exists
  4. Re-invoke enforcement
```

---

## Future Enhancements

### v1.1: Mutation Testing
- Use mutmut to detect weak tests
- Ensure tests actually validate behavior
- Not just line coverage, but quality coverage

### v1.2: Coverage Trending
- Track coverage over time
- Visualize coverage trends
- Alert on declining trends

### v1.3: AI Test Generation
- Use LLM to generate complete tests
- Not just templates, but working code
- Learn from existing test patterns

### v1.4: Smart Test Prioritization
- Identify highest-value uncovered code
- Prioritize complex logic over simple statements
- Focus on critical paths first

---

## Related Skills

- **parallel-merge-coordinator** - Uses coverage data during merge
- **parallel-task-decomposer** - Considers coverage when assigning tasks
- **code-quality-enforcer** - Validates test quality beyond coverage

---

## Implementation Notes

This skill requires:
- pytest with coverage plugin
- coverage.py for analysis
- JSON parsing for coverage data
- Git operations (checkout, diff)
- AST analysis for code context

Tools available: Bash, Read, Write, Edit, Grep, Glob

---

**Invoke this skill to proactively enforce 95%+ coverage and prevent coverage regression!**
