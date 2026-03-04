# Agentic AI Block Stacking Workflow Framework

**Version:** 1.1.0
**Created:** 2026-01-20
**Updated:** 2026-01-22

## Overview

The **Agentic AI Block Stacking Workflow** is an architectural pattern for orchestrating complex multi-step AI workflows.

> **⚠️ EXECUTION MODEL UPDATE (v1.1.0)**
>
> The original sub-agent dispatch pattern described in this document has been **deprecated** for MCP-based workflows.
>
> **Current Policy:** Use **single-agent sequential execution** as specified in `Skills.md`.
>
> **Reason:** Sub-agents lose MCP tool context and default to Bash commands, bypassing the certified tool infrastructure.
>
> The block file structure remains valid for organizing workflow phases, but blocks are now executed directly by the main agent rather than dispatched to sub-agents.

### Key Principles

1. **Master Document** - Single source of truth containing full workflow orchestration
2. **Block Files** - Extracted sub-agent briefings with isolated, focused context
3. **Context Efficiency** - Sub-agents only receive the context they need
4. **Parallel Capability** - Independent blocks can execute concurrently
5. **Failure Isolation** - One block's failure doesn't corrupt other blocks
6. **Structured Communication** - Defined inputs, outputs, and reporting formats

---

## Architecture

```
workflows/add-sdwan-site/
├── manifest.yaml          # MASTER - Full orchestration document
├── Skills.md              # AI routing guide for Master agent
├── FRAMEWORK.md           # This document
├── blocks/
│   ├── BLOCK_1_PROVISION.yaml
│   ├── BLOCK_2_LICENSE.yaml
│   ├── BLOCK_3_CONFIGURE.yaml
│   └── BLOCK_4_VERIFY.yaml
└── state/                 # Runtime state (optional)
    └── execution_state.yaml
```

---

## Master vs Block Files

### Master Document (`manifest.yaml`)

- **Purpose:** Complete workflow definition and orchestration
- **Contains:** All phases, parameters, guardrails, tool access
- **Used by:** Master orchestrating agent
- **Size:** Can be large (800+ lines)

### Block Files (`blocks/BLOCK_X_*.yaml`)

- **Purpose:** Sub-agent briefing with isolated context
- **Contains:** Single block's goal, inputs, outputs, tools, error handling
- **Used by:** Specialized sub-agents
- **Size:** ~200-300 lines (focused)

---

## Block File Schema

```yaml
# Required Header
block_id: string           # Unique identifier (e.g., "provision")
block_number: integer      # Execution order (1, 2, 3...)
name: string              # Human-readable name
version: string           # Semantic version

# Dependencies
depends_on:               # Blocks that must complete first
  - block: BLOCK_X
    required_outputs: [...]

# Sub-Agent Briefing
goal: string              # What the sub-agent must achieve

inputs:                   # Data provided to sub-agent
  required: [...]
  optional: [...]
  from_previous_blocks: [...]

success_criteria:         # How to verify completion
  - id: string
    description: string
    verification: {...}
    critical: boolean

outputs:                  # What sub-agent reports back
  required: [...]
  optional: [...]

# Execution Details
tools: [...]              # Available tools for this block
tool_gaps: [...]          # Known issues and workarounds
execution_steps: [...]    # Step-by-step guide
error_handling: [...]     # What-if scenarios

# Constraints
constraints:
  max_duration_minutes: int
  max_retries: int

# Reporting
report_format: string     # Template for sub-agent response
```

---

## Sub-Agent Dispatch Pattern

> **⚠️ DEPRECATED:** The sub-agent dispatch pattern below is preserved for reference only.
> For MCP workflows, use single-agent sequential execution per `Skills.md`.

### Master Agent Dispatches Sub-Agent (DEPRECATED)

```python
# Pseudocode for Master agent dispatching Block 1
sub_agent_prompt = f"""
You are a specialized sub-agent for Block {block.number}: {block.name}.

## Your Goal
{block.goal}

## Inputs Provided
{yaml.dump(block.inputs)}

## Success Criteria
{yaml.dump(block.success_criteria)}

## Required Outputs
Report back these values upon completion:
{yaml.dump(block.outputs.required)}

## Available Tools
{yaml.dump(block.tools)}

## Error Handling
If you encounter issues, check these scenarios:
{yaml.dump(block.error_handling)}

## IMPORTANT
- Do NOT proceed to other blocks
- Report SUCCESS, FAILURE, or BLOCKED with structured output
- Include all required outputs in your response
"""

result = dispatch_sub_agent(prompt=sub_agent_prompt)
```

### Sub-Agent Reports Back

```yaml
# Structured response from sub-agent
block_id: provision
status: SUCCESS
execution_time_seconds: 245

outputs:
  management_ip: "192.168.209.36"
  vm_name: "FortiGate-sdwan-spoke-03"
  vnc_port: 5903
  admin_password: "FG@dm!n2026!"
  serial_number: "FGVM64-KVM"

errors: []
warnings:
  - "DHCP took 90 seconds to assign IP"

ready_for_next_block: true
```

---

## Execution Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    MASTER AGENT                              │
│  (Holds full manifest.yaml, orchestrates workflow)           │
└─────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│  SUB-AGENT 1  │   │  SUB-AGENT 2  │   │  SUB-AGENT 3  │
│   BLOCK_1     │──▶│   BLOCK_2     │──▶│   BLOCK_3     │──▶...
│  (provision)  │   │  (license)    │   │  (configure)  │
└───────────────┘   └───────────────┘   └───────────────┘
        │                   │                   │
        ▼                   ▼                   ▼
    [Outputs]           [Outputs]           [Outputs]
        │                   │                   │
        └───────────────────┴───────────────────┘
                            │
                            ▼
                    MASTER COLLECTS
                    TRACKS PROGRESS
                    HANDLES FAILURES
```

---

## Benefits

### 1. Context Efficiency
- Sub-agent for Block 1 doesn't need Block 3's error handling
- Each sub-agent gets ~200 lines vs 800+ lines
- Reduces token usage and improves focus

### 2. Specialization
- Sub-agents become "experts" at their specific block
- Error handling is block-specific and actionable
- Tools listed are only those relevant to the block

### 3. Parallel Execution
- Independent blocks can run concurrently
- Example: Block 1 (VM provision) + Block 1b (license generation)

### 4. Failure Isolation
- Block 2 failure doesn't corrupt Block 1's context
- Each block has clean state boundaries
- Easier retry and recovery

### 5. Testability
- Test individual blocks in isolation
- Validate block files independently
- Mock inputs from previous blocks

### 6. Maintainability
- Changes to Block 3 don't touch Block 1 file
- Version blocks independently
- Clear ownership per block

---

## State Management

### Option 1: In-Memory (Sub-Agent Chain)
- Master holds state between sub-agent calls
- Outputs from Block N become inputs to Block N+1
- Simple but requires Master to stay active

### Option 2: Persistent State File
```yaml
# state/execution_state.yaml
workflow_id: add-sdwan-site-20260120-143022
started_at: 2026-01-20T14:30:22Z

blocks:
  BLOCK_1_PROVISION:
    status: SUCCESS
    completed_at: 2026-01-20T14:34:15Z
    outputs:
      management_ip: "192.168.209.36"
      vm_name: "FortiGate-sdwan-spoke-03"

  BLOCK_2_LICENSE:
    status: IN_PROGRESS
    started_at: 2026-01-20T14:34:20Z

  BLOCK_3_CONFIGURE:
    status: PENDING

  BLOCK_4_VERIFY:
    status: PENDING
```

---

## Error Escalation

Each block defines escalation paths:

```yaml
error_handling:
  - condition: "vm_boot_failure"
    remediation:
      - action: "Check SCSI controller"
      - action: "Verify base image"
    escalation: "Boot failure - escalate to operator with VNC port"
```

Master agent receives escalations and can:
1. Retry the block with different parameters
2. Skip the block (if optional)
3. Escalate to human operator
4. Abort workflow

---

## Usage with Claude Code

> **⚠️ DEPRECATED:** The Task tool dispatch below is preserved for reference only.
> Current execution model: Read each BLOCK file directly and execute using `execute_certified_tool`.

### Single-Agent Execution (CURRENT)
```
1. Read BLOCK_0_BLUEPRINT_WIZARD.yaml
2. Execute wizard using AskUserQuestion tool
3. Read BLOCK_1_PROVISION.yaml
4. Execute tools directly via execute_certified_tool
5. Repeat for each block sequentially
```

### Dispatch Block 1 Sub-Agent (DEPRECATED)
```
Task tool call:
  subagent_type: "general-purpose"
  prompt: |
    Read the block file at:
    workflows/add-sdwan-site/blocks/BLOCK_1_PROVISION.yaml

    Execute Block 1 with these inputs:
    - site_name: sdwan-spoke-03
    - deployment_type: vm
    - hypervisor: rocky-kvm-lab

    Report back with structured output matching the report_format.
```

### Collect Results (DEPRECATED)
Master agent reads sub-agent response and:
1. Parses outputs
2. Updates state
3. Prepares inputs for next block
4. Dispatches Block 2 sub-agent

---

## Future Enhancements

1. **Block Templates** - Reusable block patterns for common operations
2. **Conditional Blocks** - Skip blocks based on conditions
3. **Parallel Block Groups** - Define blocks that can run simultaneously
4. **Rollback Blocks** - Automatic cleanup on failure
5. **Block Metrics** - Track execution time, success rates per block

---

## Summary

The Agentic AI Block Stacking Workflow enables:

- **Scalable** - Add blocks without bloating sub-agent context
- **Maintainable** - Edit blocks independently
- **Efficient** - Sub-agents focus on their specific task
- **Robust** - Isolated failures, clear recovery paths
- **Testable** - Validate blocks in isolation

This pattern transforms monolithic AI workflows into modular, manageable building blocks.
