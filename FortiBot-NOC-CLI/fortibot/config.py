"""
FortiBot NOC - Configuration & Credential Store
Stores FortiGate targets and API keys in ~/.fortibot/
"""
import os
import sys
import yaml
from pathlib import Path
from typing import Optional, Dict

CONFIG_DIR = Path.home() / ".fortibot"
CONFIG_FILE = CONFIG_DIR / "config.yaml"


def ensure_config_dir():
    """Create ~/.fortibot/ directory if it doesn't exist."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.touch(exist_ok=True)


def _default_config() -> dict:
    """Return a blank default configuration."""
    return {"claude_api_key": None, "devices": {}, "default_device": None}


def load_config() -> dict:
    """Load the configuration file, returning defaults if empty."""
    ensure_config_dir()
    if CONFIG_FILE.stat().st_size == 0:
        return _default_config()
    with open(CONFIG_FILE) as f:
        data = yaml.safe_load(f)
    return data or _default_config()


def save_config(config: dict):
    """Persist configuration to disk with restricted permissions."""
    ensure_config_dir()
    with open(CONFIG_FILE, "w") as f:
        yaml.dump(config, f, default_flow_style=False)
    # Set owner-only permissions (no-op on Windows, but we try)
    if sys.platform != "win32":
        os.chmod(CONFIG_FILE, 0o600)


# -- Claude API Key ----------------------------------------------------------

def get_claude_key() -> Optional[str]:
    """Return the Anthropic API key from env var or config file."""
    return os.environ.get("ANTHROPIC_API_KEY") or load_config().get("claude_api_key")


def set_claude_key(key: str):
    """Store the Anthropic API key."""
    config = load_config()
    config["claude_api_key"] = key
    save_config(config)


# -- Device Management -------------------------------------------------------

def add_device(
    name: str,
    ip: str,
    port: int,
    api_token: str,
    ssh_user: str = None,
    ssh_pass: str = None,
    ssh_port: int = 22,
):
    """Add (or overwrite) a FortiGate device entry."""
    config = load_config()
    config.setdefault("devices", {})[name] = {
        "ip": ip,
        "port": port,
        "api_token": api_token,
        "ssh_user": ssh_user,
        "ssh_pass": ssh_pass,
        "ssh_port": ssh_port,
    }
    if not config.get("default_device"):
        config["default_device"] = name
    save_config(config)


def get_device(name: str = None) -> Optional[dict]:
    """Return the device dict (with 'name' key injected), or None."""
    config = load_config()
    if name is None:
        name = config.get("default_device")
    if name and name in config.get("devices", {}):
        dev = config["devices"][name].copy()
        dev["name"] = name
        return dev
    return None


def list_devices() -> Dict[str, dict]:
    """Return all configured devices."""
    return load_config().get("devices", {})


def remove_device(name: str) -> bool:
    """Remove a device by name. Returns True if it existed."""
    config = load_config()
    if name in config.get("devices", {}):
        del config["devices"][name]
        if config.get("default_device") == name:
            config["default_device"] = next(iter(config["devices"]), None)
        save_config(config)
        return True
    return False


def get_default_device_name() -> Optional[str]:
    """Return the name of the default device, or None."""
    return load_config().get("default_device")


def set_default_device(name: str):
    """Set the default device by name."""
    config = load_config()
    config["default_device"] = name
    save_config(config)
