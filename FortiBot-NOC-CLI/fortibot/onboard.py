"""
FortiBot NOC - Interactive Onboarding
Beautiful AI-powered FortiGate setup wizard
"""
import sys
import time
import requests
import urllib3
import paramiko

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich.text import Text
from rich import box

from fortibot.config import (
    set_claude_key,
    get_claude_key,
    add_device,
    get_device,
)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

console = Console()

BANNER = r"""
    [bold cyan]
    ╔═══════════════════════════════════════╗
    ║          FortiBot NOC-BOT             ║
    ║    AI-Powered FortiGate Diagnostics   ║
    ║                                       ║
    ║    "I Monitor. And I Know Things."    ║
    ╚═══════════════════════════════════════╝
    [/bold cyan]
"""


def _test_claude_key(api_key: str) -> bool:
    """Validate the Claude API key with a lightweight request."""
    try:
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)
        client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=16,
            messages=[{"role": "user", "content": "ping"}],
        )
        return True
    except Exception:
        return False


def _test_fortigate(ip: str, port: int, token: str) -> dict:
    """Test FortiGate REST API connectivity and return device info."""
    base = f"https://{ip}:{port}"
    headers = {"Authorization": f"Bearer {token}"}
    try:
        resp = requests.get(
            f"{base}/api/v2/monitor/system/status",
            headers=headers,
            verify=False,
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        results = data.get("results", {})
        return {
            "success": True,
            "hostname": results.get("hostname", "Unknown"),
            "serial": data.get("serial", "Unknown"),
            "model": results.get("model_name", results.get("model", "Unknown")),
            "firmware": data.get("version", "Unknown"),
        }
    except requests.exceptions.ConnectionError:
        return {
            "success": False,
            "error": (
                f"Cannot connect to {ip}:{port}. "
                "Check IP address, HTTPS port, and firewall rules."
            ),
        }
    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code == 401:
            return {
                "success": False,
                "error": "API token rejected (401 Unauthorized). Check the token value.",
            }
        return {"success": False, "error": f"HTTP error: {e}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _test_ssh(ip: str, port: int, user: str, password: str) -> dict:
    """Test SSH connectivity and run 'get system status'."""
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            ip,
            port=port,
            username=user,
            password=password,
            timeout=15,
            allow_agent=False,
            look_for_keys=False,
        )
        stdin, stdout, stderr = client.exec_command(
            "get system status", timeout=30
        )
        output = stdout.read().decode("utf-8", errors="replace")
        client.close()
        return {"success": True, "output": output}
    except paramiko.AuthenticationException:
        return {
            "success": False,
            "error": "SSH authentication failed. Check username/password.",
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def run_onboarding():
    """Run the full interactive onboarding wizard."""
    console.print(BANNER)
    console.print(
        Panel(
            "[bold white]Welcome to FortiBot NOC-BOT Setup[/bold white]\n"
            "Let's get you connected to your first FortiGate.",
            border_style="cyan",
            box=box.ROUNDED,
        )
    )
    console.print()

    # ── Step 1: Claude API Key ──────────────────────────────────────────
    existing_key = get_claude_key()
    if existing_key:
        console.print(
            "[green]Claude API key already configured.[/green] "
            "Enter a new one to replace it, or press Enter to keep it."
        )
        api_key = Prompt.ask("Anthropic API key", default="", password=True)
        if not api_key:
            api_key = existing_key
    else:
        api_key = Prompt.ask("Anthropic API key (sk-ant-...)", password=True)

    with console.status("[bold cyan]Testing Claude API key...", spinner="dots"):
        if _test_claude_key(api_key):
            console.print("[bold green]Claude API key validated.[/bold green]")
            set_claude_key(api_key)
        else:
            console.print(
                "[bold red]Claude API key test failed.[/bold red] "
                "You can fix this later with [cyan]fortibot init[/cyan]."
            )
            if not Confirm.ask("Continue without a valid key?", default=False):
                sys.exit(1)

    console.print()

    # ── Step 2: FortiGate Connection ────────────────────────────────────
    console.print(
        Panel(
            "[bold white]FortiGate Connection[/bold white]\n"
            "Provide the management IP and REST API token for your FortiGate.",
            border_style="yellow",
            box=box.ROUNDED,
        )
    )

    fg_ip = Prompt.ask("FortiGate management IP")
    try:
        fg_port = int(Prompt.ask("HTTPS management port", default="443"))
    except ValueError:
        console.print("[yellow]Invalid port, using 443[/yellow]")
        fg_port = 443
    fg_token = Prompt.ask("REST API token", password=True)

    # Test the connection
    with console.status(
        "[bold cyan]Connecting to FortiGate...", spinner="dots"
    ):
        result = _test_fortigate(fg_ip, fg_port, fg_token)

    if result["success"]:
        info_table = Table(
            show_header=False, box=box.SIMPLE, padding=(0, 2)
        )
        info_table.add_column("Field", style="bold cyan")
        info_table.add_column("Value", style="white")
        info_table.add_row("Hostname", result["hostname"])
        info_table.add_row("Serial", result["serial"])
        info_table.add_row("Model", result["model"])
        info_table.add_row("Firmware", result["firmware"])

        console.print(
            Panel(
                info_table,
                title="[bold green]FortiGate Connected[/bold green]",
                border_style="green",
                box=box.ROUNDED,
            )
        )
    else:
        console.print(
            Panel(
                f"[bold red]Connection Failed[/bold red]\n{result['error']}",
                border_style="red",
                box=box.ROUNDED,
            )
        )
        if not Confirm.ask("Continue anyway?", default=False):
            sys.exit(1)

    console.print()

    # ── Step 3: SSH Credentials (optional) ──────────────────────────────
    console.print(
        Panel(
            "[bold white]SSH Credentials (Optional)[/bold white]\n"
            "SSH is needed for advanced CLI diagnostics "
            "(NPU, traceroute, ping, config debug).",
            border_style="yellow",
            box=box.ROUNDED,
        )
    )

    ssh_user = None
    ssh_pass = None
    ssh_port = 22

    if Confirm.ask("Configure SSH access?", default=True):
        ssh_user = Prompt.ask("SSH username", default="admin")
        ssh_pass = Prompt.ask("SSH password", password=True)
        try:
            ssh_port = int(Prompt.ask("SSH port", default="22"))
        except ValueError:
            console.print("[yellow]Invalid port, using 22[/yellow]")
            ssh_port = 22

        with console.status(
            "[bold cyan]Testing SSH connection...", spinner="dots"
        ):
            ssh_result = _test_ssh(fg_ip, ssh_port, ssh_user, ssh_pass)

        if ssh_result["success"]:
            console.print("[bold green]SSH connection verified.[/bold green]")
        else:
            console.print(
                f"[bold red]SSH test failed:[/bold red] {ssh_result['error']}\n"
                "SSH credentials saved anyway -- you can fix them later."
            )

    console.print()

    # ── Step 4: Device Nickname ─────────────────────────────────────────
    default_name = (
        result.get("hostname", "fortigate")
        if result.get("success")
        else "fortigate"
    )
    device_name = Prompt.ask("Device nickname", default=default_name)

    # ── Save ────────────────────────────────────────────────────────────
    add_device(
        name=device_name,
        ip=fg_ip,
        port=fg_port,
        api_token=fg_token,
        ssh_user=ssh_user,
        ssh_pass=ssh_pass,
        ssh_port=ssh_port,
    )

    console.print()
    console.print(
        Panel(
            "[bold green]Setup Complete![/bold green]\n\n"
            f"Device [cyan]{device_name}[/cyan] saved as default.\n\n"
            "[bold white]Try these commands:[/bold white]\n"
            "  [cyan]fortibot health-check[/cyan]          "
            "Quick device health\n"
            "  [cyan]fortibot ask \"How is my firewall?\"[/cyan]  "
            "AI-powered query\n"
            "  [cyan]fortibot chat[/cyan]                   "
            "Interactive AI session\n"
            "  [cyan]fortibot run-all[/cyan]                "
            "Full diagnostic report\n"
            "  [cyan]fortibot man[/cyan]                    "
            "Pilot manual\n",
            title="[bold cyan]NOC-BOT Ready[/bold cyan]",
            border_style="green",
            box=box.DOUBLE,
        )
    )
