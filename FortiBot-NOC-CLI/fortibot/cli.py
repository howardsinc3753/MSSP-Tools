"""
FortiBot NOC - Click CLI Entry Point
All commands for FortiBot NOC-BOT.
"""
import json
import sys
import re
import os

# Fix Unicode output on Windows CMD (cp1252 can't render box-drawing chars)
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

from fortibot import __version__
from fortibot.config import (
    get_device,
    list_devices,
    remove_device,
    set_default_device,
    get_default_device_name,
    add_device,
    get_claude_key,
)

console = Console()

BANNER = r"""[bold cyan]
    ╔═══════════════════════════════════════╗
    ║          FortiBot NOC-BOT             ║
    ║    AI-Powered FortiGate Diagnostics   ║
    ║                                       ║
    ║    "I Monitor. And I Know Things."    ║
    ╚═══════════════════════════════════════╝
[/bold cyan]"""


def _get_device_or_exit(device_name: str = None) -> dict:
    """Resolve a device by name (or default) and exit if not found."""
    dev = get_device(device_name)
    if not dev:
        if device_name:
            console.print(f"[bold red]Device '{device_name}' not found.[/bold red]")
        else:
            console.print(
                "[bold red]No device configured.[/bold red] "
                "Run [cyan]fortibot init[/cyan] to set up your first device."
            )
        sys.exit(1)
    return dev


def _print_result(result: dict, title: str = "Result"):
    """Pretty-print a tool result dict using rich."""
    if not result.get("success"):
        console.print(
            Panel(
                f"[bold red]Error:[/bold red] {result.get('error', 'Unknown error')}",
                title=f"[red]{title} - Failed[/red]",
                border_style="red",
                box=box.ROUNDED,
            )
        )
        return

    # Remove 'success' key for display
    display = {k: v for k, v in result.items() if k != "success"}

    # Check for a verdict string
    verdict = display.pop("verdict", None)

    # Display key-value pairs in a table
    if display:
        tbl = Table(show_header=False, box=box.SIMPLE, padding=(0, 2))
        tbl.add_column("Field", style="bold cyan", min_width=20)
        tbl.add_column("Value", style="white")

        for key, value in display.items():
            if isinstance(value, (list, dict)):
                # For complex data, show formatted JSON
                formatted = json.dumps(value, indent=2, default=str)
                if len(formatted) > 2000:
                    formatted = formatted[:2000] + "\n... [truncated]"
                tbl.add_row(key, formatted)
            else:
                tbl.add_row(key, str(value))

        console.print(
            Panel(tbl, title=f"[green]{title}[/green]", border_style="green", box=box.ROUNDED)
        )

    if verdict:
        console.print(
            Panel(verdict, title="[yellow]Verdict[/yellow]", border_style="yellow", box=box.ROUNDED)
        )


# ── CLI Group ───────────────────────────────────────────────────────────

@click.group()
@click.version_option(version=__version__, prog_name="fortibot")
def main():
    """FortiBot NOC-BOT -- AI-Powered FortiGate Diagnostics CLI."""
    pass


# ── Setup Commands ──────────────────────────────────────────────────────

@main.command()
def init():
    """Run the interactive setup wizard."""
    from fortibot.onboard import run_onboarding
    run_onboarding()


@main.command("add-device")
@click.option("--name", prompt="Device nickname")
@click.option("--ip", prompt="FortiGate management IP")
@click.option("--port", prompt="HTTPS port", default=443, type=int)
@click.option("--token", prompt="API token", hide_input=True)
@click.option("--ssh-user", prompt="SSH username (or skip)", default="")
@click.option("--ssh-pass", prompt="SSH password (or skip)", default="", hide_input=True)
@click.option("--ssh-port", default=22, type=int)
def add_device_cmd(name, ip, port, token, ssh_user, ssh_pass, ssh_port):
    """Add a FortiGate device."""
    add_device(
        name=name, ip=ip, port=port, api_token=token,
        ssh_user=ssh_user or None, ssh_pass=ssh_pass or None, ssh_port=ssh_port,
    )
    console.print(f"[green]Device '{name}' added.[/green]")


@main.command()
def devices():
    """List configured devices."""
    devs = list_devices()
    default = get_default_device_name()

    if not devs:
        console.print("[yellow]No devices configured.[/yellow] Run [cyan]fortibot init[/cyan].")
        return

    tbl = Table(title="Configured Devices", box=box.ROUNDED)
    tbl.add_column("Name", style="cyan")
    tbl.add_column("IP", style="white")
    tbl.add_column("Port", style="white")
    tbl.add_column("SSH", style="white")
    tbl.add_column("Default", style="green")

    for name, dev in devs.items():
        is_default = ">>>" if name == default else ""
        ssh_status = "Yes" if dev.get("ssh_user") else "No"
        tbl.add_row(name, dev.get("ip", ""), str(dev.get("port", 443)), ssh_status, is_default)

    console.print(tbl)


@main.command("remove-device")
@click.argument("name")
def remove_device_cmd(name):
    """Remove a device by name."""
    if remove_device(name):
        console.print(f"[green]Device '{name}' removed.[/green]")
    else:
        console.print(f"[red]Device '{name}' not found.[/red]")


@main.command()
@click.argument("name")
def use(name):
    """Set the default device."""
    dev = get_device(name)
    if dev:
        set_default_device(name)
        console.print(f"[green]Default device set to '{name}'.[/green]")
    else:
        console.print(f"[red]Device '{name}' not found.[/red]")


# ── AI Commands ─────────────────────────────────────────────────────────

def _setup_engine(dev: dict, verbose: bool = False):
    """Create an AIEngine with rich workflow callbacks."""
    from fortibot.ai import AIEngine

    engine = AIEngine(dev, verbose=verbose)

    def on_tool_start(step_num, tool_name, args):
        args_str = ""
        if args:
            filtered = {k: v for k, v in args.items() if v is not None and v != ""}
            if filtered:
                args_str = f" [dim]({', '.join(f'{k}={v}' for k, v in filtered.items())})[/dim]"
        console.print(f"  [bold cyan]>[/bold cyan] [white]Step {step_num}:[/white] Running [bold yellow]{tool_name}[/bold yellow]{args_str}")

    def on_tool_done(step_num, tool_name, success, summary, elapsed_ms):
        icon = "[bold green]✓[/bold green]" if success else "[bold red]✗[/bold red]"
        time_str = f"[dim]{elapsed_ms}ms[/dim]"
        console.print(f"    {icon} {summary}  {time_str}")

    def on_thinking(iteration):
        if iteration == 1:
            console.print(f"\n  [bold cyan]⚡ NOC-BOT Workflow[/bold cyan] [dim]— analyzing your question...[/dim]\n")

    engine.on_tool_start = on_tool_start
    engine.on_tool_done = on_tool_done
    engine.on_thinking = on_thinking

    return engine


def _print_workflow_summary(engine):
    """Print a summary of the agentic workflow after completion."""
    trace = engine.last_trace
    if not trace or not trace.steps:
        return

    console.print()
    summary_items = []
    for step in trace.steps:
        icon = "[green]✓[/green]" if step.success else "[red]✗[/red]"
        summary_items.append(f"  {icon} [cyan]{step.name}[/cyan] → {step.summary} [dim]({step.elapsed_ms}ms)[/dim]")

    workflow_text = "\n".join(summary_items)
    total_time = f"{trace.elapsed_s:.1f}s"

    console.print(
        Panel(
            f"{workflow_text}\n\n[dim]Tools: {trace.tool_count()} | Iterations: {trace.total_iterations} | Total: {total_time}[/dim]",
            title="[bold yellow]⚡ Workflow Trace[/bold yellow]",
            border_style="yellow",
            box=box.ROUNDED,
        )
    )


@main.command()
@click.argument("question")
@click.option("--device", "-d", default=None, help="Device name to query.")
@click.option("--verbose", "-v", is_flag=True, default=True, help="Show workflow steps (default: on).")
@click.option("--quiet", "-q", is_flag=True, default=False, help="Hide workflow steps, show only the answer.")
@click.option("--json-output", is_flag=True, default=False, help="Output raw JSON (for scripting/automation).")
def ask(question, device, verbose, quiet, json_output):
    """Ask NOC-BOT an AI-powered question about your FortiGate."""
    dev = _get_device_or_exit(device)
    console.print(BANNER)
    console.print(f"  [dim]Device: {dev['name']} ({dev['ip']}:{dev.get('port', 443)})[/dim]")
    console.print(f"  [dim]Question: {question}[/dim]\n")

    try:
        engine = _setup_engine(dev, verbose=not quiet)

        if json_output or quiet:
            engine.on_tool_start = None
            engine.on_tool_done = None
            engine.on_thinking = None

        if quiet and not json_output:
            with console.status("[bold cyan]NOC-BOT is thinking...", spinner="dots"):
                answer = engine.ask(question)
        else:
            answer = engine.ask(question)

        if json_output:
            import json as _json
            output = {
                "question": question,
                "device": dev["name"],
                "answer": answer,
                "workflow": [s.to_dict() for s in engine.last_trace.steps] if engine.last_trace else [],
            }
            click.echo(_json.dumps(output, indent=2, default=str))
            return

        console.print()
        console.print(
            Panel(
                answer,
                title="[bold cyan]🛡️ NOC-BOT Analysis[/bold cyan]",
                border_style="cyan",
                box=box.ROUNDED,
            )
        )

        if not quiet:
            _print_workflow_summary(engine)

    except ValueError as e:
        console.print(f"[bold red]{e}[/bold red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[bold red]AI error:[/bold red] {e}")
        sys.exit(1)


@main.command()
@click.option("--device", "-d", default=None, help="Device name to query.")
@click.option("--quiet", "-q", is_flag=True, default=False, help="Hide workflow steps.")
def chat(device, quiet):
    """Start an interactive chat session with NOC-BOT."""
    dev = _get_device_or_exit(device)
    console.print(BANNER)
    console.print(f"  [dim]Connected to: {dev['name']} ({dev['ip']}:{dev.get('port', 443)})[/dim]")
    console.print("  [dim]Type 'exit' or 'quit' to end the session.[/dim]")
    console.print("  [dim]Workflow steps shown by default. Use --quiet to hide.[/dim]\n")

    try:
        engine = _setup_engine(dev, verbose=not quiet)
        if quiet:
            engine.on_tool_start = None
            engine.on_tool_done = None
            engine.on_thinking = None
    except ValueError as e:
        console.print(f"[bold red]{e}[/bold red]")
        sys.exit(1)

    while True:
        try:
            question = console.input("[bold green]You:[/bold green] ")
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Session ended.[/dim]")
            break

        if question.strip().lower() in ("exit", "quit", "q"):
            console.print("[dim]Session ended.[/dim]")
            break

        if not question.strip():
            continue

        try:
            if quiet:
                with console.status("[bold cyan]NOC-BOT is thinking...", spinner="dots"):
                    answer = engine.ask(question)
            else:
                answer = engine.ask(question)

            console.print()
            console.print(
                Panel(
                    answer,
                    title="[bold cyan]🛡️ NOC-BOT[/bold cyan]",
                    border_style="cyan",
                    box=box.ROUNDED,
                )
            )

            if not quiet:
                _print_workflow_summary(engine)

            console.print()
        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {e}\n")


# ── Direct Tool Commands ────────────────────────────────────────────────

@main.command("health-check")
@click.option("--device", "-d", default=None, help="Device name.")
def health_check_cmd(device):
    """Run a health check on the FortiGate."""
    dev = _get_device_or_exit(device)
    from fortibot.tools.health_check import run
    with console.status("[bold cyan]Running health check...", spinner="dots"):
        result = run(dev)
    _print_result(result, "Health Check")


@main.command()
@click.option("--device", "-d", default=None, help="Device name.")
def interfaces(device):
    """Show interface status."""
    dev = _get_device_or_exit(device)
    from fortibot.tools.interface_status import run
    with console.status("[bold cyan]Checking interfaces...", spinner="dots"):
        result = run(dev)

    if result.get("success"):
        tbl = Table(title="Interface Status", box=box.ROUNDED)
        tbl.add_column("Name", style="cyan")
        tbl.add_column("Status", style="white")
        tbl.add_column("IP", style="white")
        tbl.add_column("Speed", style="white")
        tbl.add_column("RX Err", style="red")
        tbl.add_column("TX Err", style="red")

        for iface in result.get("interfaces", []):
            status_color = "green" if iface["link"] else "red"
            tbl.add_row(
                iface["name"],
                Text(iface["status"], style=status_color),
                iface["ip"],
                f"{iface['speed']}M" if iface["speed"] else "-",
                str(iface["rx_errors"]),
                str(iface["tx_errors"]),
            )

        console.print(tbl)
        console.print(
            f"\n[dim]Total: {result['interface_count']} | "
            f"Up: {result['up']} | Down: {result['down']} | "
            f"With errors: {result['with_errors']}[/dim]"
        )
    else:
        _print_result(result, "Interfaces")


@main.command()
@click.option("--device", "-d", default=None, help="Device name.")
def routing(device):
    """Show the routing table."""
    dev = _get_device_or_exit(device)
    from fortibot.tools.routing import run
    with console.status("[bold cyan]Fetching routing table...", spinner="dots"):
        result = run(dev)

    if result.get("success"):
        tbl = Table(title="IPv4 Routing Table", box=box.ROUNDED)
        tbl.add_column("Destination", style="cyan")
        tbl.add_column("Gateway", style="white")
        tbl.add_column("Interface", style="white")
        tbl.add_column("Type", style="white")
        tbl.add_column("Dist", style="white")
        tbl.add_column("Metric", style="white")

        for r in result.get("routes", [])[:100]:
            tbl.add_row(
                r["destination"], r["gateway"], r["interface"],
                r["type"], str(r["distance"]), str(r["metric"]),
            )

        console.print(tbl)
        console.print(f"\n[dim]Total routes: {result['total_routes']} | Shown: {result['returned_count']}[/dim]")
    else:
        _print_result(result, "Routing")


@main.command("vpn")
@click.option("--device", "-d", default=None, help="Device name.")
def vpn_cmd(device):
    """Show VPN tunnel status."""
    dev = _get_device_or_exit(device)
    from fortibot.tools.vpn import run
    with console.status("[bold cyan]Checking VPN tunnels...", spinner="dots"):
        result = run(dev)

    if result.get("success"):
        tbl = Table(title="IPsec VPN Tunnels", box=box.ROUNDED)
        tbl.add_column("Name", style="cyan")
        tbl.add_column("Status", style="white")
        tbl.add_column("Remote GW", style="white")
        tbl.add_column("Interface", style="white")
        tbl.add_column("IKE", style="white")

        for t in result.get("tunnels", []):
            status_color = "green" if t["status"] == "up" else "red"
            tbl.add_row(
                t["name"],
                Text(t["status"], style=status_color),
                t["remote_gw"],
                t["interface"],
                str(t["ike_version"]),
            )

        console.print(tbl)
        console.print(f"\n[dim]Total: {result['tunnel_count']} | Up: {result['up']} | Down: {result['down']}[/dim]")
    else:
        _print_result(result, "VPN")


@main.command("ha")
@click.option("--device", "-d", default=None, help="Device name.")
def ha_cmd(device):
    """Show HA cluster status."""
    dev = _get_device_or_exit(device)
    from fortibot.tools.ha_status import run
    with console.status("[bold cyan]Checking HA status...", spinner="dots"):
        result = run(dev)
    _print_result(result, "HA Status")


@main.command("sdwan")
@click.option("--device", "-d", default=None, help="Device name.")
def sdwan_cmd(device):
    """Show SD-WAN status (requires SSH)."""
    dev = _get_device_or_exit(device)
    from fortibot.tools.sdwan import run
    with console.status("[bold cyan]Checking SD-WAN...", spinner="dots"):
        result = run(dev)
    _print_result(result, "SD-WAN Status")


@main.command()
@click.option("--device", "-d", default=None, help="Device name.")
def firmware(device):
    """Check firmware version and updates."""
    dev = _get_device_or_exit(device)
    from fortibot.tools.firmware import run
    with console.status("[bold cyan]Checking firmware...", spinner="dots"):
        result = run(dev)
    _print_result(result, "Firmware Check")


@main.command()
@click.option("--device", "-d", default=None, help="Device name.")
def sessions(device):
    """Show active firewall sessions."""
    dev = _get_device_or_exit(device)
    from fortibot.tools.sessions import run
    with console.status("[bold cyan]Fetching sessions...", spinner="dots"):
        result = run(dev)

    if result.get("success"):
        tbl = Table(title="Active Sessions (Top by Bytes)", box=box.ROUNDED)
        tbl.add_column("Src IP", style="cyan")
        tbl.add_column("Dst IP", style="white")
        tbl.add_column("Port", style="white")
        tbl.add_column("Proto", style="white")
        tbl.add_column("In", style="green")
        tbl.add_column("Out", style="yellow")
        tbl.add_column("Policy", style="dim")

        for s in result.get("sessions", [])[:30]:
            tbl.add_row(
                s["src_ip"], s["dst_ip"], str(s["dst_port"]),
                s["proto"],
                f"{s['bytes_in']:,}", f"{s['bytes_out']:,}",
                str(s["policy_id"]),
            )

        console.print(tbl)
        console.print(f"\n[dim]Total sessions on device: {result['total_sessions']:,}[/dim]")
    else:
        _print_result(result, "Sessions")


@main.command()
@click.option("--device", "-d", default=None, help="Device name.")
@click.option("--path", "-p", default=None, help="Directory to save backup.")
def backup(device, path):
    """Download a configuration backup."""
    dev = _get_device_or_exit(device)
    from fortibot.tools.config_backup import run
    with console.status("[bold cyan]Downloading config backup...", spinner="dots"):
        result = run(dev, save_path=path)

    if result.get("success"):
        if result.get("saved_to"):
            console.print(
                Panel(
                    f"[green]Backup saved to:[/green] {result['saved_to']}\n"
                    f"Size: {result['backup_size_bytes']:,} bytes\n"
                    f"Hostname: {result['hostname']} | Serial: {result['serial']}",
                    title="[green]Backup Complete[/green]",
                    border_style="green",
                    box=box.ROUNDED,
                )
            )
        else:
            console.print(
                Panel(
                    f"Size: {result['backup_size_bytes']:,} bytes\n"
                    f"Hostname: {result['hostname']} | Serial: {result['serial']}\n\n"
                    "[dim]Tip: Use --path /dir to save to a file.[/dim]",
                    title="[green]Backup Downloaded[/green]",
                    border_style="green",
                    box=box.ROUNDED,
                )
            )
    else:
        _print_result(result, "Backup")


@main.command()
@click.argument("command")
@click.option("--device", "-d", default=None, help="Device name.")
def ssh(command, device):
    """Execute an SSH CLI command on the FortiGate."""
    dev = _get_device_or_exit(device)
    from fortibot.tools.ssh_cli import run_ssh_command
    with console.status(f"[bold cyan]Running: {command}", spinner="dots"):
        result = run_ssh_command(dev, command)

    if result.get("success"):
        console.print(
            Panel(
                result.get("output", ""),
                title=f"[green]SSH: {command}[/green]",
                border_style="green",
                box=box.ROUNDED,
            )
        )
    else:
        _print_result(result, "SSH")


@main.command("run-all")
@click.option("--device", "-d", default=None, help="Device name.")
def run_all(device):
    """Run all diagnostic checks and generate a report."""
    dev = _get_device_or_exit(device)
    console.print(BANNER)
    console.print(f"[bold]Running full diagnostic report for [cyan]{dev['name']}[/cyan] ({dev['ip']})[/bold]\n")

    from fortibot.tools import health_check, interface_status, vpn, ha_status
    from fortibot.tools import firmware as fw_mod, fortiguard as fg_mod

    checks = [
        ("Health Check", health_check.run),
        ("Interface Status", interface_status.run),
        ("VPN Tunnels", vpn.run),
        ("HA Status", ha_status.run),
        ("Firmware", fw_mod.run),
        ("FortiGuard", fg_mod.run),
    ]

    for title, func in checks:
        with console.status(f"[bold cyan]{title}...", spinner="dots"):
            result = func(dev)
        _print_result(result, title)
        console.print()


@main.command()
@click.argument("trace_spec")
@click.option("--device", "-d", default=None, help="Device name.")
def trace(trace_spec, device):
    """Diagnose reachability between two IPs. Format: '10.1.1.5 to 10.2.2.10'"""
    dev = _get_device_or_exit(device)

    # Parse the trace spec
    ip_pattern = r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"
    ips = re.findall(ip_pattern, trace_spec)
    if len(ips) < 2:
        console.print(
            "[bold red]Could not find two IP addresses in your input.[/bold red]\n"
            "Use format: [cyan]fortibot trace '10.1.1.5 to 10.2.2.10'[/cyan]\n"
            "Both must be IPv4 addresses (e.g., 192.168.1.1)."
        )
        sys.exit(1)

    src_ip, dst_ip = ips[0], ips[1]
    console.print(BANNER)
    console.print(
        f"[bold]Diagnosing: [cyan]{src_ip}[/cyan] -> [cyan]{dst_ip}[/cyan] "
        f"via [yellow]{dev['name']}[/yellow][/bold]\n"
    )

    from fortibot.tools.reachability import run as reachability_run
    with console.status("[bold cyan]Running reachability diagnostics...", spinner="dots"):
        result = reachability_run(dev, src_ip, dst_ip)

    if result.get("success"):
        for step_name, step_data in result.get("steps", {}).items():
            title = step_name.replace("_", " ").title()
            if isinstance(step_data, dict):
                _print_result(
                    {**step_data, "success": step_data.get("success", True)},
                    title,
                )
            else:
                console.print(f"[bold]{title}:[/bold] {step_data}")
            console.print()
    else:
        _print_result(result, "Reachability")


@main.command()
def doctor():
    """Check that everything is configured and reachable."""
    from fortibot.config import get_claude_key, list_devices, get_default_device_name, get_device

    console.print(BANNER)
    console.print("[bold]Running connectivity checks...[/bold]\n")

    all_ok = True

    # 1. Python version
    py_ver = sys.version.split()[0]
    console.print(f"  [green]\u2713[/green] Python {py_ver}")

    # 2. Required packages
    missing_pkgs = []
    for pkg in ["click", "rich", "anthropic", "paramiko", "requests", "yaml"]:
        try:
            __import__(pkg)
        except ImportError:
            missing_pkgs.append(pkg)
    if missing_pkgs:
        console.print(f"  [red]\u2717[/red] Missing packages: {', '.join(missing_pkgs)}")
        console.print(f"    [dim]Fix: pip install {' '.join(missing_pkgs)}[/dim]")
        all_ok = False
    else:
        console.print("  [green]\u2713[/green] All required packages installed")

    # 3. Claude API key
    api_key = get_claude_key()
    if api_key:
        console.print(f"  [green]\u2713[/green] Claude API key configured (ends ...{api_key[-4:]})")
        # Test it
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)
            client.messages.create(
                model="claude-sonnet-4-20250514", max_tokens=16,
                messages=[{"role": "user", "content": "ping"}],
            )
            console.print("  [green]\u2713[/green] Claude API key is valid")
        except Exception as e:
            console.print(f"  [red]\u2717[/red] Claude API key test failed: {e}")
            all_ok = False
    else:
        console.print("  [red]\u2717[/red] Claude API key not configured")
        console.print("    [dim]Fix: fortibot init  (or set ANTHROPIC_API_KEY env var)[/dim]")
        all_ok = False

    # 4. Devices
    devs = list_devices()
    default_name = get_default_device_name()
    if not devs:
        console.print("  [red]\u2717[/red] No FortiGate devices configured")
        console.print("    [dim]Fix: fortibot init[/dim]")
        all_ok = False
    else:
        console.print(f"  [green]\u2713[/green] {len(devs)} device(s) configured (default: {default_name})")

        # Test each device
        import requests as _req
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        for name, dev in devs.items():
            ip = dev.get("ip", "?")
            port = dev.get("port", 443)
            token = dev.get("api_token", "")
            marker = " [cyan](default)[/cyan]" if name == default_name else ""

            # REST API check
            try:
                resp = _req.get(
                    f"https://{ip}:{port}/api/v2/monitor/system/status",
                    headers={"Authorization": f"Bearer {token}"},
                    verify=False, timeout=10,
                )
                if resp.status_code == 200:
                    info = resp.json().get("results", {})
                    hostname = info.get("hostname", "?")
                    console.print(f"  [green]\u2713[/green] {name}{marker} \u2014 REST API OK ({hostname} @ {ip}:{port})")
                elif resp.status_code == 401:
                    console.print(f"  [red]\u2717[/red] {name}{marker} \u2014 REST API 401 Unauthorized (bad token?)")
                    all_ok = False
                else:
                    console.print(f"  [yellow]![/yellow] {name}{marker} \u2014 REST API HTTP {resp.status_code}")
                    all_ok = False
            except _req.exceptions.ConnectionError:
                console.print(f"  [red]\u2717[/red] {name}{marker} \u2014 Cannot reach {ip}:{port}")
                console.print(f"    [dim]Can you ping {ip}? Is HTTPS admin enabled?[/dim]")
                all_ok = False
            except Exception as e:
                console.print(f"  [red]\u2717[/red] {name}{marker} \u2014 {e}")
                all_ok = False

            # SSH check
            ssh_user = dev.get("ssh_user")
            if ssh_user:
                try:
                    import paramiko
                    client = paramiko.SSHClient()
                    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    client.connect(
                        ip, port=dev.get("ssh_port", 22), username=ssh_user,
                        password=dev.get("ssh_pass", ""), timeout=10,
                        allow_agent=False, look_for_keys=False,
                    )
                    client.close()
                    console.print(f"  [green]\u2713[/green] {name} \u2014 SSH OK (user: {ssh_user})")
                except Exception as e:
                    console.print(f"  [red]\u2717[/red] {name} \u2014 SSH failed: {e}")
                    all_ok = False
            else:
                console.print(f"  [yellow]![/yellow] {name} \u2014 SSH not configured (SD-WAN/NPU/ping tools won't work)")

    console.print()
    if all_ok:
        console.print(
            Panel(
                "[bold green]All checks passed![/bold green]\n"
                "You're ready to go. Try: [cyan]fortibot ask \"Is my firewall healthy?\"[/cyan]",
                border_style="green", box=box.ROUNDED,
            )
        )
    else:
        console.print(
            Panel(
                "[bold yellow]Some checks failed.[/bold yellow]\n"
                "Fix the issues above, then run [cyan]fortibot doctor[/cyan] again.",
                border_style="yellow", box=box.ROUNDED,
            )
        )


@main.command("man")
def man_page():
    """Show the NOC-BOT pilot manual."""
    from pathlib import Path
    man_file = Path(__file__).parent / "docs" / "NOCBOT_Pilot_ManPage.md"
    if man_file.exists():
        from rich.markdown import Markdown
        md = Markdown(man_file.read_text())
        console.print(md)
    else:
        console.print("[yellow]Manual not found.[/yellow] It should be at fortibot/docs/NOCBOT_Pilot_ManPage.md")


if __name__ == "__main__":
    main()
