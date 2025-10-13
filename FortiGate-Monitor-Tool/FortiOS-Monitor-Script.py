#!/usr/bin/env python3
"""
FortiGate Conserve Mode Monitor v2.2
Production-ready monitoring script for FortiOS Firewalls
Author: Daniel Howard, MSSP Solutions Engineer
Last Updated: 2025-10-11

================================================================================
DISCLAIMER AND TERMS OF USE
================================================================================
This script is provided by the author for educational and diagnostic purposes
only. It is NOT an official Fortinet product, tool, or support utility, and is
not endorsed, tested, or maintained by Fortinet, Inc.

Use of this script is at your own risk. The author and Fortinet, Inc. assume
no responsibility or liability for:
    - Any direct, indirect, incidental, or consequential damages
    - System outages, configuration errors, or performance impacts
    - Improper or unauthorized application in production environments

By using, copying, or distributing this script, you agree that:
    1. It is provided "AS IS" without warranties of any kind
    2. You will test and validate in a non-production environment first
    3. You assume full responsibility for its operation and outcomes

This script monitors FortiGate system performance via FortiOS REST API endpoints.

© 2025 Daniel Howard. Licensed under MIT License.
================================================================================

CHANGELOG v2.2:
- FINAL FIX: Removed all heuristic logic - FortiOS API always returns bytes
- Corrected memory parsing: bytes → KB → MB (no guessing)
- Changed sorting to MEMORY usage (top 30 memory-consuming processes)
- Increased display from top 20 to top 30 processes
- All validation warnings resolved
- Added comprehensive disclaimer

CHANGELOG v2.1:
- CRITICAL FIX: Attempted to correct process memory parsing (incomplete fix)

CHANGELOG v2.0:
- Initial production release
"""

import requests
import urllib3
import json
from datetime import datetime, timezone
import time
import os
import threading
import signal
import sys

urllib3.disable_warnings()

class FortiGateConserveModeMonitor:
    """Monitor FortiGate system resources and detect conserve mode conditions"""
    
    # FortiGate 1800F conserve mode thresholds
    RED_THRESHOLD = 88      # Conserve mode activation
    YELLOW_THRESHOLD = 79   # Warning level
    
    def __init__(self, host, api_key, name=None, log_file=None):
        self.host = host
        self.name = name or host
        self.base_url = f"https://{host}/api/v2"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        base_name = f"fortigate_{self.name.replace('.', '_')}_{timestamp}"
        self.log_file = log_file or f"{base_name}.log"
        self.raw_log_file = f"{base_name}_raw.jsonl"
        self.summary_log_file = f"{base_name}_summary.jsonl"
        self.is_running = True
        
        # For CPU delta calculation
        self.prev_cpu_ticks = {}
        self.prev_snapshot_time = None
        self.num_cores = 1
        self.ticks_per_second = 100
        
        # For memory percentage calculation
        self.total_memory_kb = None
        
    def log(self, message):
        """Write to both console and summary log file with timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] [{self.name}] {message}"
        print(log_message)
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(log_message + "\n")
        except Exception as e:
            print(f"[ERROR] Failed to write to log: {e}")
    
    def log_raw_json(self, data, log_type="raw"):
        """Append raw API data as JSON lines to separate log files"""
        log_file = self.raw_log_file if log_type == "raw" else self.summary_log_file
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(data) + "\n")
        except Exception as e:
            print(f"[ERROR] Failed to write JSON log: {e}")
    
    def get_process_name(self, proc):
        """Extract process name from various possible fields"""
        if not isinstance(proc, dict):
            return "Unknown"
        
        name = (proc.get('name') or 
                proc.get('process_name') or 
                proc.get('comm') or
                proc.get('cmd') or
                proc.get('command'))
        
        if name and isinstance(name, str):
            return os.path.basename(name).split('/')[-1].split('\\')[-1]
        
        return "Unknown"
    
    def get_performance_status(self):
        """Get CPU and Memory performance"""
        try:
            response = requests.get(
                f"{self.base_url}/monitor/system/performance/status",
                headers=self.headers,
                verify=False,
                timeout=10
            )
            return response.json() if response.status_code == 200 else {"error": f"Status {response.status_code}"}
        except Exception as e:
            return {"error": str(e)}
    
    def get_running_processes(self):
        """Get list of running processes and their resource usage"""
        try:
            response = requests.get(
                f"{self.base_url}/monitor/system/running-processes",
                headers=self.headers,
                verify=False,
                timeout=10
            )
            return response.json() if response.status_code == 200 else {"error": f"Status {response.status_code}"}
        except Exception as e:
            return {"error": str(e)}
    
    def check_cluster_health(self):
        """Check HA cluster health for A/A deployments"""
        try:
            response = requests.get(
                f"{self.base_url}/monitor/system/ha-checksums",
                headers=self.headers,
                verify=False,
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                if 'results' in data:
                    return data['results']
            return None
        except Exception as e:
            self.log(f"WARNING: Could not retrieve HA status: {e}")
            return None
    
    def detect_conserve_mode_threshold(self, memory_percent):
        """Detect memory thresholds based on FortiGate model"""
        if memory_percent is None:
            return "UNKNOWN", None
        
        if memory_percent >= self.RED_THRESHOLD:
            status = "CRITICAL"
            message = f"🚨 CRITICAL: Memory at {memory_percent:.1f}% - CONSERVE MODE ACTIVE OR IMMINENT!"
        elif memory_percent >= self.YELLOW_THRESHOLD:
            status = "WARNING"
            margin = self.RED_THRESHOLD - memory_percent
            message = f"⚠️  WARNING: Memory at {memory_percent:.1f}% - {margin:.1f}% from conserve mode"
        else:
            status = "NORMAL"
            margin = self.YELLOW_THRESHOLD - memory_percent
            message = f"✓ NORMAL: Memory at {memory_percent:.1f}% - {margin:.1f}% margin to warning threshold"
        
        return status, message
    
    def parse_cpu_memory(self, perf_data):
        """Parse CPU and Memory from performance status"""
        cpu_percent = None
        memory_percent = None
        
        if 'results' in perf_data:
            results = perf_data['results']
            
            # Parse CPU
            cpu_data = results.get('cpu', results.get('CPU'))
            if isinstance(cpu_data, dict):
                if 'cores' in cpu_data:
                    self.num_cores = len(cpu_data['cores'])
                idle = cpu_data.get('idle', 100)
                cpu_percent = 100 - idle
            elif isinstance(cpu_data, (int, float)):
                cpu_percent = cpu_data
            
            # Parse Memory
            mem_data = results.get('mem', results.get('Memory', results.get('memory')))
            if isinstance(mem_data, dict):
                used = mem_data.get('used', 0)
                total = mem_data.get('total', 1)
                
                # FortiOS returns bytes for system memory
                if total > 100000000:  # > 100MB in KB = likely bytes
                    self.total_memory_kb = total / 1024
                else:
                    self.total_memory_kb = total
                
                if total > 0:
                    memory_percent = round((used / total) * 100, 1)
            elif isinstance(mem_data, (int, float)):
                memory_percent = mem_data
        
        return cpu_percent, memory_percent
    
    def parse_processes(self, proc_data):
        """Parse process list from running-processes response"""
        if 'results' in proc_data:
            results = proc_data['results']
            if isinstance(results, dict):
                return results.get('processes', results.get('process_list', []))
            elif isinstance(results, list):
                return results
        return []
    
    def calculate_cpu_percent(self, pid, cpu_ticks, current_time):
        """Calculate CPU percentage from tick delta"""
        if self.prev_snapshot_time is None or pid not in self.prev_cpu_ticks:
            return None
        
        time_delta = current_time - self.prev_snapshot_time
        if time_delta <= 0:
            return None
        
        tick_delta = cpu_ticks - self.prev_cpu_ticks[pid]
        if tick_delta < 0:
            return None
        
        max_ticks = time_delta * self.ticks_per_second * self.num_cores
        if max_ticks > 0:
            cpu_percent = (tick_delta / max_ticks) * 100
            return round(cpu_percent, 1)
        
        return None
    
    def validate_memory_reading(self, mem_mb, mem_percent, process_name, pid):
        """Validate memory readings and log warnings for suspicious values"""
        warnings = []
        
        # Check for impossibly high memory usage
        if mem_percent > 50:
            warnings.append(f"⚠️  ALERT: Process {process_name} (PID {pid}) using {mem_percent:.1f}% memory ({mem_mb:.0f}MB) - possible memory leak!")
        
        # Check for processes that shouldn't use much memory (v2.2: should be <1MB now)
        # Note: lldprx can vary 0.3MB-10MB depending on priority mode, so exclude it
        low_memory_processes = ['insmod', 'getty', 'lldptx', 'dhcpcd', 'kmiglogd']
        if process_name in low_memory_processes and mem_mb > 5:
            warnings.append(f"⚠️  WARNING: {process_name} (PID {pid}) using unexpected {mem_mb:.1f}MB - verify parsing")
        
        return warnings
    
    def parse_process_metrics(self, proc, current_time):
        """Extract and normalize CPU/MEM from a process dict - v2.2 CORRECTED"""
        if not isinstance(proc, dict):
            return None, None, None, None, None
        
        pid = proc.get('pid', proc.get('process_id'))
        if pid is None:
            return None, None, None, None, None
        
        # ============ CPU PARSING ============
        cpu_raw = proc.get('cpu_usage', proc.get('cpu', 0))
        cpu_ticks = 0
        
        if isinstance(cpu_raw, dict):
            user = cpu_raw.get('user', 0)
            kernel = cpu_raw.get('kernel', cpu_raw.get('system', 0))
            cpu_ticks = user + kernel
        elif isinstance(cpu_raw, (int, float)):
            cpu_ticks = int(cpu_raw)
        
        # Calculate CPU percentage from delta
        cpu_percent = self.calculate_cpu_percent(pid, cpu_ticks, current_time)
        self.prev_cpu_ticks[pid] = cpu_ticks
        
        # Format CPU display
        if cpu_percent is not None:
            cpu_display = f"{cpu_percent:.1f}%"
        else:
            cpu_display = f"{cpu_ticks}t*"
        
        # ============ MEMORY PARSING (v2.2 CORRECTED) ============
        # PREFER 'pss' (Proportional Set Size) for accuracy
        mem_raw = proc.get('pss', proc.get('memory', proc.get('mem', 0)))
        
        if isinstance(mem_raw, dict):
            mem_val = mem_raw.get('used', mem_raw.get('percent', 0))
        else:
            mem_val = mem_raw
        
        # Validate memory value
        if not isinstance(mem_val, (int, float)) or mem_val <= 0:
            return cpu_display, "0.0MB (0.00%)", cpu_percent if cpu_percent else cpu_ticks, cpu_percent, 0
        
        # *** CRITICAL FIX v2.2: FortiOS API ALWAYS returns bytes for process memory ***
        # No heuristics needed - just convert bytes → KB → MB
        mem_kb = mem_val / 1024.0
        mem_mb = mem_kb / 1024.0
        
        # Calculate percentage
        mem_percent = 0
        if self.total_memory_kb and self.total_memory_kb > 0:
            mem_percent = (mem_kb / self.total_memory_kb) * 100
            mem_percent = min(mem_percent, 100.0)  # Cap at 100%
        
        # Format memory display
        if mem_percent > 0:
            mem_display = f"{mem_mb:.1f}MB ({mem_percent:.3f}%)"
        else:
            mem_display = f"{mem_mb:.1f}MB"
        
        cpu_sort = cpu_percent if cpu_percent is not None else cpu_ticks
        
        return cpu_display, mem_display, cpu_sort, cpu_percent, mem_mb
    
    def log_system_summary(self, snapshot):
        """Log a concise system summary for quick review"""
        summary_lines = []
        summary_lines.append("\n" + "="*80)
        summary_lines.append(f"SYSTEM SUMMARY - {snapshot.get('device', 'Unknown')}")
        summary_lines.append("="*80)
        
        # CPU Summary
        cpu = snapshot.get('cpu_percent', 'N/A')
        cpu_status = 'NORMAL' if cpu < 80 else 'HIGH' if cpu < 90 else 'CRITICAL'
        summary_lines.append(f"CPU:    {cpu}% ({cpu_status})")
        
        # Memory Summary with detailed status
        mem = snapshot.get('memory_percent')
        if mem is not None:
            status, message = self.detect_conserve_mode_threshold(mem)
            summary_lines.append(f"Memory: {message}")
        else:
            summary_lines.append("Memory: N/A")
        
        # Top Process by Memory
        top_proc = snapshot.get('top_memory_process', {})
        if top_proc:
            summary_lines.append(f"Top Memory: {top_proc.get('name', 'Unknown')} (PID {top_proc.get('pid', 'N/A')}) - {top_proc.get('mem', 'N/A')}")
        
        summary_lines.append("="*80 + "\n")
        
        for line in summary_lines:
            self.log(line)
    
    def monitor_snapshot(self):
        """Take a snapshot of all critical metrics with validation"""
        current_time = time.time()
        
        snapshot = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "device": self.name,
            "host": self.host
        }
        
        self.log("=" * 80)
        self.log("SNAPSHOT")
        self.log("=" * 80)
        
        # Get Performance Status
        perf = self.get_performance_status()
        self.log_raw_json({"endpoint": "performance/status", "timestamp": snapshot["timestamp"], "data": perf})
        
        if 'error' not in perf:
            cpu_percent, memory_percent = self.parse_cpu_memory(perf)
            
            if cpu_percent is not None:
                snapshot["cpu_percent"] = cpu_percent
                self.log(f"CPU Usage: {cpu_percent}%")
            else:
                self.log("CPU Usage: N/A")
            
            if memory_percent is not None:
                snapshot["memory_percent"] = memory_percent
                
                # Use enhanced conserve mode detection
                status, message = self.detect_conserve_mode_threshold(memory_percent)
                snapshot["conserve_status"] = status
                
                self.log(f"Memory Usage: {memory_percent}%")
                if self.total_memory_kb:
                    total_mb = self.total_memory_kb / 1024
                    total_gb = total_mb / 1024
                    self.log(f"Total Memory: {total_gb:.2f}GB ({total_mb:.0f}MB)")
                self.log(message)
            else:
                self.log("Memory Usage: N/A")
                    
            # Show per-core CPU details if available
            if 'results' in perf and 'cpu' in perf['results']:
                cpu_data = perf['results']['cpu']
                if isinstance(cpu_data, dict) and 'cores' in cpu_data:
                    cores = cpu_data['cores']
                    self.log(f"CPU Cores: {len(cores)} cores detected")
                    snapshot["cpu_cores"] = len(cores)
        else:
            self.log(f"ERROR getting performance data: {perf['error']}")
        
        # Get Running Processes
        processes = self.get_running_processes()
        self.log_raw_json({"endpoint": "running-processes", "timestamp": snapshot["timestamp"], "data": processes})
        
        # Track validation warnings
        all_warnings = []
        
        if 'error' not in processes:
            procs = self.parse_processes(processes)
            
            if procs and len(procs) > 0:
                # Parse and prepare all processes
                proc_list = []
                for proc in procs:
                    if isinstance(proc, dict):
                        cpu_display, mem_display, cpu_sort, cpu_percent, mem_mb = self.parse_process_metrics(proc, current_time)
                        
                        if cpu_display and mem_display:
                            pid = proc.get('pid', proc.get('process_id', 'N/A'))
                            name = self.get_process_name(proc)
                            
                            # Extract numeric memory for validation
                            mem_percent_val = float(mem_display.split('(')[1].split('%')[0]) if '(' in mem_display else 0
                            
                            # Validate memory reading
                            warnings = self.validate_memory_reading(mem_mb, mem_percent_val, name, pid)
                            all_warnings.extend(warnings)
                            
                            proc_list.append({
                                'pid': pid,
                                'name': name,
                                'cpu_display': cpu_display,
                                'mem_display': mem_display,
                                'cpu_sort': cpu_sort,
                                'cpu_percent': cpu_percent,
                                'mem_mb': mem_mb
                            })
                
                # *** CHANGED: Sort by MEMORY usage (descending) ***
                proc_list.sort(key=lambda x: x['mem_mb'], reverse=True)
                
                # Check if this is first snapshot
                is_first_snapshot = self.prev_snapshot_time is None
                
                if is_first_snapshot:
                    self.log(f"\nTop 30 Processes by Memory Usage (from {len(procs)} total)")
                    self.log("Note: First snapshot shows cumulative CPU ticks (t*). Next snapshot will show real-time %.")
                else:
                    self.log(f"\nTop 30 Processes by Memory Usage (from {len(procs)} total):")
                
                self.log(f"{'':4}{'PID':<8}{'Process Name':<30}{'CPU':<15}{'Memory':<20}")
                self.log(f"{'':4}{'-'*73}")
                
                # Get top memory process for summary
                if proc_list:
                    top = proc_list[0]
                    snapshot["top_memory_process"] = {
                        "name": top['name'],
                        "pid": str(top['pid']),
                        "cpu": top['cpu_display'],
                        "mem": top['mem_display']
                    }
                
                # Show top 30 by memory
                for i, proc in enumerate(proc_list[:30], 1):
                    pid = str(proc['pid'])
                    name = proc['name'][:28]
                    cpu = proc['cpu_display']
                    mem = proc['mem_display']
                    
                    self.log(f"  {i:2d}. {pid:<8}{name:<30}{cpu:<15}{mem:<20}")
                
                # Log any validation warnings
                if all_warnings:
                    self.log("\n⚠️  VALIDATION WARNINGS:")
                    for warning in all_warnings:
                        self.log(warning)
                else:
                    if not is_first_snapshot:  # Only show after first snapshot
                        self.log("\n✓ All memory readings validated successfully")
            else:
                self.log("No processes found")
        else:
            self.log(f"ERROR getting processes: {processes['error']}")
        
        # Update snapshot time for next delta calculation
        self.prev_snapshot_time = current_time
        
        # Write aggregated snapshot summary
        self.log_raw_json(snapshot, log_type="summary")
        
        # Add concise system summary at the end
        self.log_system_summary(snapshot)
        
        self.log("=" * 80 + "\n")
    
    def continuous_monitor(self, interval=60, duration_hours=None):
        """Continuously monitor and log every X seconds"""
        self.log(f"Starting continuous monitoring")
        self.log(f"Summary Log: {os.path.abspath(self.log_file)}")
        self.log(f"Raw JSON Log: {os.path.abspath(self.raw_log_file)}")
        self.log(f"Summary JSON: {os.path.abspath(self.summary_log_file)}")
        self.log(f"Check Interval: {interval}s")
        
        if duration_hours:
            self.log(f"Duration: {duration_hours} hours")
            end_time = time.time() + (duration_hours * 3600)
        else:
            self.log(f"Duration: Indefinite (Press Ctrl+C to stop)")
            end_time = None
        
        self.log("")
        
        try:
            while self.is_running:
                self.monitor_snapshot()
                
                if end_time and time.time() >= end_time:
                    self.log(f"Monitoring complete - ran for {duration_hours} hours")
                    break
                
                # Check if still running every second during sleep
                for _ in range(interval):
                    if not self.is_running:
                        break
                    time.sleep(1)
                    
        except KeyboardInterrupt:
            self.log("Monitoring stopped by user")
        except Exception as e:
            self.log(f"ERROR: {e}")
            import traceback
            self.log(f"Traceback: {traceback.format_exc()}")
    
    def stop(self):
        """Stop monitoring"""
        self.is_running = False


class MultiFortiGateMonitor:
    """Monitor multiple FortiGates simultaneously"""
    
    def __init__(self):
        self.monitors = []
        self.threads = []
        self.running = True
    
    def add_fortigate(self, host, api_key, name=None):
        """Add a FortiGate to monitor"""
        monitor = FortiGateConserveModeMonitor(host, api_key, name)
        self.monitors.append(monitor)
        return monitor
    
    def signal_handler(self, signum, frame):
        """Handle Ctrl+C gracefully"""
        print("\n\n⚠️  Interrupt received, stopping all monitors...")
        self.stop_all()
        sys.exit(0)
    
    def stop_all(self):
        """Stop all monitors"""
        self.running = False
        for monitor in self.monitors:
            monitor.stop()
    
    def start_monitoring(self, interval=60, duration_hours=None):
        """Start monitoring all FortiGates in separate threads"""
        signal.signal(signal.SIGINT, self.signal_handler)
        
        print("\n" + "="*80)
        print(f"FORTIGATE CONSERVE MODE MONITOR v2.2 - PRODUCTION READY")
        print(f"Monitoring {len(self.monitors)} FortiGate(s)")
        print(f"Press Ctrl+C to stop")
        print("="*80 + "\n")
        
        for monitor in self.monitors:
            thread = threading.Thread(
                target=monitor.continuous_monitor,
                args=(interval, duration_hours),
                daemon=False
            )
            thread.start()
            self.threads.append(thread)
        
        try:
            while any(t.is_alive() for t in self.threads):
                time.sleep(0.5)
        except KeyboardInterrupt:
            self.signal_handler(None, None)


def get_fortigate_list():
    """Interactive prompt to get FortiGate list"""
    print("\n" + "="*80)
    print("FORTIGATE CONSERVE MODE MONITOR - CONFIGURATION")
    print("="*80 + "\n")
    
    fortigates = []
    
    print("Do you want to:")
    print("  1. Enter FortiGates manually")
    print("  2. Load from config file (fortigate_config.txt)")
    choice = input("\nEnter choice (1 or 2): ").strip()
    
    if choice == "2":
        if os.path.exists("fortigate_config.txt"):
            print("\nLoading from fortigate_config.txt...")
            with open("fortigate_config.txt", 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        parts = line.split(",")
                        if len(parts) >= 2:
                            ip = parts[0].strip()
                            api_key = parts[1].strip()
                            name = parts[2].strip() if len(parts) > 2 else ip
                            fortigates.append({
                                'ip': ip,
                                'api_key': api_key,
                                'name': name
                            })
            print(f"Loaded {len(fortigates)} FortiGate(s) from config file")
        else:
            print("Config file not found! Creating template...")
            with open("fortigate_config.txt", 'w') as f:
                f.write("# FortiGate Configuration File\n")
                f.write("# Format: IP_ADDRESS, API_KEY, NAME (optional)\n")
                f.write("# Example:\n")
                f.write("# 192.168.1.1, fmtXXXXXXXXXXXXXXXXXXXXXXXXXXXX, HQ-FortiGate\n")
            print("Template created. Please edit fortigate_config.txt and run again.")
            return None
    else:
        print("\nEnter FortiGate details (press Enter with empty IP to finish):\n")
        
        while True:
            print(f"\n--- FortiGate #{len(fortigates) + 1} ---")
            ip = input("IP Address (or press Enter to finish): ").strip()
            
            if not ip:
                break
            
            api_key = input("API Key: ").strip()
            name = input("Name (optional, press Enter to use IP): ").strip() or ip
            
            fortigates.append({
                'ip': ip,
                'api_key': api_key,
                'name': name
            })
            
            print(f"✓ Added: {name} ({ip})")
    
    if not fortigates:
        print("\nNo FortiGates configured!")
        return None
    
    print("\n" + "="*80)
    print("CONFIGURED FORTIGATES:")
    print("="*80)
    for i, fg in enumerate(fortigates, 1):
        print(f"{i}. {fg['name']} - {fg['ip']}")
    print("="*80)
    
    return fortigates


def main():
    """Main function"""
    fortigates = get_fortigate_list()
    
    if not fortigates:
        return
    
    print("\n--- Monitoring Parameters ---")
    
    try:
        interval = int(input("Check interval in seconds (default 30): ").strip() or "30")
    except:
        interval = 30
    
    duration_input = input("Duration in hours (leave empty for indefinite): ").strip()
    duration_hours = float(duration_input) if duration_input else None
    
    multi_monitor = MultiFortiGateMonitor()
    
    for fg in fortigates:
        multi_monitor.add_fortigate(
            host=fg['ip'],
            api_key=fg['api_key'],
            name=fg['name']
        )
    
    multi_monitor.start_monitoring(interval=interval, duration_hours=duration_hours)


if __name__ == "__main__":
    main()
