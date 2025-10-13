# FortiGate Conserve Mode Monitor

A production-ready monitoring script for detecting and preventing conserve mode on FortiGate firewalls. Designed for MSSP and enterprise environments managing FortiGate.

## ⚠️ Disclaimer

**This script is provided for partner troubleshooting and diagnostic purposes only.**

- **NOT an official Fortinet product** - Not endorsed, tested, or maintained by Fortinet, Inc.
- **Use at your own risk** - Test in lab environments before production deployment
- **No warranties** - Provided "AS IS" without warranties of any kind
- **No liability** - Neither the author nor Fortinet, Inc. shall be held liable for any damages, outages, or issues resulting from use of this code

By using this script, you agree to validate all outputs independently and assume full responsibility for its operation.

---

## Features

- **Real-time monitoring** of CPU and memory usage via FortiOS REST API
- **Conserve mode detection** with configurable thresholds (79% warning, 88% critical)
- **Top 30 processes** sorted by memory consumption
- **Multi-device support** - Monitor multiple FortiGates simultaneously
- **Automatic logging** - Human-readable logs + JSON exports for analysis
- **Process validation** - Flags unexpected memory usage patterns
- **Graceful shutdown** - Ctrl+C handling with proper cleanup

## Requirements

- Python 3.6 or higher
- Network access to FortiGate management interface
- FortiOS API token with read permissions

### Python Dependencies
```bash
pip install requests urllib3
```

## Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/fortigate-conserve-monitor.git
cd fortigate-conserve-monitor
```

### 2. Create Configuration File
```bash
cat > fortigate_config.txt << EOF
# Format: IP_ADDRESS, API_KEY, NAME
192.168.1.100, your_api_token_here, FW-Primary
192.168.1.101, your_api_token_here, FW-Secondary
EOF
```

### 3. Generate API Token
On your FortiGate:
```
config system api-user
    edit "monitoring"
        set accprofile "prof_admin"
        set vdom "root"
        config trusthost
            edit 1
                set ipv4-trusthost 192.168.1.0/24
            next
        end
    next
end
```

Copy the generated token into `fortigate_config.txt`.

### 4. Run the Monitor
```bash
python3 FortiOS-Monitor-Script.py
```

When prompted:
- Select option **2** (Load from config file)
- Set check interval (default: **30 seconds**)
- Set duration (leave empty for indefinite monitoring)

## Configuration

### Config File Format
```
# Comment lines start with #
IP_ADDRESS, API_KEY, FRIENDLY_NAME
192.168.209.62, fmtXXXXXXXXXXXXXXXXXXXX, Lab-FortiGate
10.0.1.100, fmtYYYYYYYYYYYYYYYYYYYY, Production-FW1
```

### Conserve Mode Thresholds
Edit these values in the script if needed:
```python
RED_THRESHOLD = 88      # Conserve mode activation
YELLOW_THRESHOLD = 79   # Warning level
```

## Output Files

Each monitoring session generates 3 log files:

| File | Purpose | Format |
|------|---------|--------|
| `fortigate_<name>_<timestamp>.log` | Human-readable summary | Text |
| `fortigate_<name>_<timestamp>_raw.jsonl` | Raw API responses | JSON Lines |
| `fortigate_<name>_<timestamp>_summary.jsonl` | Aggregated snapshots | JSON Lines |

### Example Output
```
Top 30 Processes by Memory Usage (from 129 total):
    PID     Process Name                  CPU            Memory              
    -------------------------------------------------------------------------
   1. 209     node                          0.1%           84.6MB (2.275%)
   2. 419     ipsengine                     0.1%           52.9MB (1.424%)
   3. 418     ipsengine                     0.1%           52.8MB (1.421%)

================================================================================
SYSTEM SUMMARY - Lab-FortiGate
================================================================================
CPU:    0% (NORMAL)
Memory: ✓ NORMAL: Memory at 53.6% - 25.4% margin to warning threshold
Top Memory: node (PID 209) - 84.6MB (2.275%)
================================================================================
```

## Troubleshooting

### Issue: "Connection refused"
**Cause:** Cannot reach FortiGate API  
**Solution:** Verify IP address, network connectivity, and HTTPS management access

### Issue: "Unauthorized" or 401 error
**Cause:** Invalid or expired API token  
**Solution:** Regenerate API token and update config file

### Issue: "Certificate verify failed"
**Cause:** Self-signed certificate (expected)  
**Solution:** Script disables SSL verification by default - no action needed

### Issue: Validation warnings for small processes
**Cause:** Script detects unexpected memory usage  
**Solution:** Review process memory in FortiOS CLI:
```
diagnose sys top
```

### Issue: High memory usage detected
**Cause:** System approaching conserve mode  
**Action:**
1. Review top memory-consuming processes
2. Check for traffic spikes or misconfigurations
3. Consider upgrading memory or optimizing policies

## Tested Platforms

- **FortiOS:** 7.4.x
- **Models:** 71F FortiGate
- **Deployment:**  HA clusters, standalone units

## Support

This is a community tool maintained by the author. For issues:

1. **Script bugs/questions:** Open a GitHub issue
2. **FortiGate API questions:** Consult [FortiOS API Documentation](https://docs.fortinet.com/)
3. **FortiGate product support:** Contact Fortinet TAC (not responsible for this script)

## Contributing

Contributions welcome! Please:
1. Test changes in lab environment
2. Follow existing code style
3. Update documentation as needed
4. Submit pull requests with clear descriptions

## Version History

- **v2.2** (2025-10-11) - Fixed memory parsing bug, added top 30 memory view
- **v2.1** (2025-10-11) - Attempted memory parsing fix (incomplete)
- **v2.0** (2025-10-10) - Initial production release

## Author

**Daniel Howard**  
MSSP Solutions Engineer  
*This is a personal project and not affiliated with Fortinet, Inc.*

## License

MIT License - See [LICENSE](LICENSE) file for details
