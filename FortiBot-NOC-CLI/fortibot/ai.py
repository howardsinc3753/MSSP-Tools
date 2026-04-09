"""
FortiBot NOC - AI Engine (Claude Integration)
Agentic tool-use loop for FortiGate diagnostics with verbose workflow visibility.
"""
import json
import os
import time
from typing import List, Optional, Callable

import anthropic

from fortibot.config import get_claude_key
from fortibot.tool_registry import get_claude_tools, execute_tool

SYSTEM_PROMPT = """\
You are NOC-BOT, an expert AI assistant for Fortinet FortiGate network security appliances.
You work inside a NOC (Network Operations Center) and help engineers diagnose, monitor,
and troubleshoot FortiGate firewalls.

You have access to tools that query a FortiGate device in real time via REST API and SSH.
When asked a question, use the appropriate tools to gather data, then analyze the results
and provide clear, actionable findings.

Guidelines:
- Always start by gathering data using tools before answering questions.
- When diagnosing reachability issues (e.g., "10.1.1.5 can't reach 10.2.2.10"), use
  the reachability_test tool which runs route lookup, interface check, ping, and traceroute.
- When asked about overall health, use health_check first. Add interface_status or
  fortiguard_status if the user wants more detail.
- For VPN issues, use vpn_tunnels. For HA issues, use ha_status.
- For SD-WAN SLA problems, use sdwan_status.
- For performance concerns, consider health_check (CPU/mem), session_table (session count),
  npu_offload (hardware offload), and top_bandwidth (bandwidth hogs).
- Explain your findings in plain English suitable for a NOC engineer.
- Highlight anything that looks abnormal or concerning.
- If a tool returns an error, explain what went wrong and suggest next steps.
- Format output clearly: use bullet points, sections, and summary/verdict where appropriate.
- You can run multiple tools if needed to get a complete picture.
- Never fabricate data. Only report what the tools return.
- Be concise but thorough. NOC engineers are busy.

You are NOC-BOT. You Monitor. And You Know Things.
"""


class ToolExecution:
    """Record of a single tool execution in the workflow."""
    def __init__(self, name: str, args: dict):
        self.name = name
        self.args = args
        self.result = None
        self.success = False
        self.summary = ""
        self.elapsed_ms = 0

    def to_dict(self) -> dict:
        return {
            "tool": self.name,
            "args": self.args,
            "success": self.success,
            "summary": self.summary,
            "elapsed_ms": self.elapsed_ms,
        }


class WorkflowTrace:
    """Tracks the full agentic workflow for verbose display."""
    def __init__(self):
        self.steps: List[ToolExecution] = []
        self.total_iterations = 0
        self.start_time = time.time()

    @property
    def elapsed_s(self) -> float:
        return time.time() - self.start_time

    def add_step(self, execution: ToolExecution):
        self.steps.append(execution)

    def tool_count(self) -> int:
        return len(self.steps)


def _summarize_result(tool_name: str, result: dict) -> str:
    """Generate a short one-line summary of a tool result for verbose output."""
    if not result.get("success", False):
        return f"Error: {result.get('error', 'unknown')}"

    if tool_name == "health_check":
        return (
            f"CPU: {result.get('cpu_percent', '?')}% | "
            f"Mem: {result.get('memory_percent', '?')}% | "
            f"Sessions: {result.get('session_count', '?'):,}"
        )
    elif tool_name == "interface_status":
        return f"{result.get('up', '?')} up, {result.get('down', '?')} down, {result.get('with_errors', '?')} with errors"
    elif tool_name == "routing_table":
        routes = result.get("routes", [])
        return f"{len(routes)} routes returned (total: {result.get('total_routes', '?')})"
    elif tool_name == "vpn_tunnels":
        return f"{result.get('up', '?')} up, {result.get('down', '?')} down of {result.get('tunnel_count', '?')} tunnels"
    elif tool_name == "ha_status":
        return f"Mode: {result.get('ha_mode', '?')} | Sync: {result.get('config_sync', '?')}"
    elif tool_name == "sdwan_status":
        return result.get("output", "SD-WAN data collected")[:80]
    elif tool_name == "firmware_check":
        return f"{result.get('current_version', '?')} | Upgrades: {result.get('upgrades_available', '?')}"
    elif tool_name == "fortiguard_status":
        expired = result.get("expired_count", 0)
        return f"{result.get('total_services', '?')} services, {expired} expired" if expired else f"{result.get('total_services', '?')} services, all active"
    elif tool_name == "session_table":
        return f"{len(result.get('sessions', []))} sessions returned (total: {result.get('total_sessions', '?'):,})"
    elif tool_name == "ssh_command":
        output = result.get("output", "")
        lines = output.strip().split("\n")
        return f"{len(lines)} lines of output"
    elif tool_name == "reachability_test":
        steps = result.get("steps", {})
        ping = steps.get("ping", {})
        finding = ping.get("finding", "")
        return finding if finding else "Reachability data collected"
    elif tool_name == "top_bandwidth":
        consumers = result.get("top_consumers", [])
        return f"{len(consumers)} top bandwidth consumers found"
    elif tool_name == "network_logs":
        entries = result.get("entries", result.get("logs", []))
        return f"{len(entries) if isinstance(entries, list) else '?'} log entries returned"
    elif tool_name == "config_backup":
        return f"Backup: {result.get('backup_size_bytes', 0):,} bytes"
    elif tool_name == "npu_offload":
        return f"NPU family: {result.get('npu_family', '?')}"
    else:
        return "Completed"


class AIEngine:
    """Manages multi-turn conversation with Claude using FortiGate tools."""

    def __init__(self, device: dict, api_key: str = None, verbose: bool = False):
        self.device = device
        self.api_key = api_key or get_claude_key()
        if not self.api_key:
            raise ValueError(
                "Claude API key not configured. Run 'fortibot init' to set it up."
            )
        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.messages: List[dict] = []
        self.model = os.environ.get("FORTIBOT_MODEL", "claude-sonnet-4-20250514")
        self.max_messages = 40  # Prune to prevent token overflow
        self.verbose = verbose
        self.on_tool_start: Optional[Callable] = None   # fn(step_num, tool_name, args)
        self.on_tool_done: Optional[Callable] = None     # fn(step_num, tool_name, success, summary, elapsed_ms)
        self.on_thinking: Optional[Callable] = None      # fn(iteration)
        self.last_trace: Optional[WorkflowTrace] = None  # Last workflow trace for inspection

    def ask(self, question: str) -> str:
        """Send a question through the agentic tool-use loop and return the answer."""
        self.messages.append({"role": "user", "content": question})

        # Prune old messages to prevent token overflow
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[:2] + self.messages[-(self.max_messages - 2):]

        tools = get_claude_tools()
        max_iterations = 10
        trace = WorkflowTrace()
        step_num = 0

        iteration = 0
        while iteration < max_iterations:
            iteration += 1
            trace.total_iterations = iteration

            if self.on_thinking:
                self.on_thinking(iteration)

            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                tools=tools,
                messages=self.messages,
            )

            assistant_content = response.content
            tool_use_blocks = [b for b in assistant_content if b.type == "tool_use"]

            if not tool_use_blocks:
                self.messages.append({"role": "assistant", "content": assistant_content})
                text_parts = [b.text for b in assistant_content if hasattr(b, "text")]
                self.last_trace = trace
                return "\n".join(text_parts) if text_parts else "NOC-BOT completed analysis but had no additional findings."

            self.messages.append({"role": "assistant", "content": assistant_content})

            tool_results = []
            for tool_block in tool_use_blocks:
                step_num += 1
                tool_name = tool_block.name
                tool_input = tool_block.input or {}

                execution = ToolExecution(tool_name, tool_input)

                if self.on_tool_start:
                    self.on_tool_start(step_num, tool_name, tool_input)

                start = time.time()
                result = execute_tool(tool_name, self.device, tool_input)
                elapsed_ms = int((time.time() - start) * 1000)

                execution.result = result
                execution.success = result.get("success", False)
                execution.elapsed_ms = elapsed_ms
                execution.summary = _summarize_result(tool_name, result)
                trace.add_step(execution)

                if self.on_tool_done:
                    self.on_tool_done(step_num, tool_name, execution.success, execution.summary, elapsed_ms)

                result_str = json.dumps(result, indent=2, default=str)
                if len(result_str) > 30000:
                    result_str = result_str[:30000] + "\n... [TRUNCATED]"

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_block.id,
                    "content": result_str,
                })

            self.messages.append({"role": "user", "content": tool_results})

        self.last_trace = trace
        return "NOC-BOT reached maximum tool iterations. Please try a more specific question."

    def reset(self):
        """Clear conversation history."""
        self.messages = []
        self.last_trace = None
