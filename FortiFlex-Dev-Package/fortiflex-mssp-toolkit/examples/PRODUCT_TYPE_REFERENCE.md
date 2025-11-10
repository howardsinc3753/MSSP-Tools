# FortiFlex Product Type Reference

**Source**: FortiFlex 25.1.0 Administration Guide
**Last Updated**: November 9, 2025
**Version**: Complete Catalog

---

## Table of Contents

- [Overview](#overview)
- [FortiGate Hardware (ID: 101)](#fortigate-hardware-id-101)
- [FortiGate VM (ID: 1)](#fortigate-vm-id-1)
- [FortiAP (ID: 102)](#fortiap-id-102)
- [FortiSwitch (ID: 103)](#fortiswitch-id-103)
- [FortiEDR (ID: 206)](#fortiedr-id-206)
- [FortiSASE (ID: 205)](#fortisase-id-205)
- [FortiManager VM (ID: 2)](#fortimanager-vm-id-2)
- [FortiAnalyzer VM (ID: 7)](#fortianalyzer-vm-id-7)
- [FortiClient EMS (ID: 5)](#forticlient-ems-id-5)
- [Quick Reference Table](#quick-reference-table)

---

## Overview

FortiFlex supports multiple product types, each with specific configuration parameters. This reference provides the complete catalog for building configurations programmatically.

### Product Type IDs

| ID | Product Name | Category |
|----|--------------|----------|
| 1 | FortiGate-VM | Virtual Appliances |
| 2 | FortiManager-VM | Virtual Appliances |
| 7 | FortiAnalyzer-VM | Virtual Appliances |
| 5 | FortiClient-EMS | Cloud Services |
| 101 | FortiGate-Hardware | Physical Hardware |
| 102 | FortiAP-Hardware | Physical Hardware |
| 103 | FortiSwitch-Hardware | Physical Hardware |
| 204 | FortiClient-EMS-Cloud | Cloud Services |
| 205 | FortiSASE | Cloud Services |
| 206 | FortiEDR-MSSP | Cloud Services |

---

## FortiGate Hardware (ID: 101)

### Device Models (Parameter ID: 27)

Entry-Level Models:
- `FGT40F` - FortiGate-40F
- `FGT60F` - FortiGate-60F
- `FGT70F` - FortiGate-70F
- `FGT80F` - FortiGate-80F
- `FG100F` - FortiGate-100F

Mid-Range Models:
- `FG200F` - FortiGate-200F
- `FG201F` - FortiGate-201F
- `FG4H0F` - FortiGate-400F
- `FG6H0F` - FortiGate-600F

Previous Generation:
- `FGT60E` - FortiGate-60E
- `FGT61F` - FortiGate-61F
- `FG100E` - FortiGate-100E
- `FG101F` - FortiGate-101F
- `FG200E` - FortiGate-200E

### Service Packages (Parameter ID: 28)

- `FGHWATP` - Advanced Threat Protection (ATP)
- `FGHWUTP` - Unified Threat Protection (UTP)
- `FGHWENT` - Enterprise Bundle
- `FGHWFC247` - FortiCare 24x7

### Add-On Services (Parameter ID: 29)

Security Services:
- `FGHWSOCA` - SOCaaS (Security Operations Center as a Service)
- `FGHWFAMS` - Advanced Malware Protection
- `FGHWFAIS` - AI-Based In-line Sandbox
- `FGHWSWNM` - SD-WAN Underlay
- `FGHWDLP` - FortiGuard DLP
- `FGHWFAZC` - FortiAnalyzer Cloud
- `FGHWFCSS` - FortiConverter Service
- `FGHWFCELU` - FortiCare Elite Upgrade

Management & Cloud:
- `FGHWFMGC` - FortiGate Cloud Management
- `FGHWFAIS` - Attack Surface Security Service
- `FGHWFIPT` - Intrusion Prevention
- `FGHWFOTSS` - FortiGuard OT Security Service

SD-WAN & SASE:
- `FGHWSASE` - SD-WAN Connector for FortiSASE
- `FGHWSWAN` - SD-WAN Overlay-as-a-Service
- `FGHWMFG` - Managed FortiGate

Web & Content Filtering:
- `FGHWWEBF` - Web, DNS & Video Filtering

### Example Configuration
```python
{
    "name": "Customer-A-FGT60F-UTP",
    "product_type_id": 101,
    "parameters": [
        {"id": 27, "value": "FGT60F"},      # Device model
        {"id": 28, "value": "FGHWUTP"},     # UTP bundle
        {"id": 29, "value": "FGHWFAZC"}     # FortiAnalyzer Cloud addon
    ]
}
```

---

## FortiGate VM (ID: 1)

### CPU Cores (Parameter ID: 1)

- `2` - 2 vCPUs
- `4` - 4 vCPUs
- `8` - 8 vCPUs
- `16` - 16 vCPUs
- `32` - 32 vCPUs (High-end deployments)

### Service Bundles (Parameter ID: 2)

- `FGVMATP` - Advanced Threat Protection (ATP)
- `FGVMUTP` - Unified Threat Protection (UTP)
- `FGVMENT` - Enterprise Bundle
- `FGVMFC247` - FortiCare 24x7

### VDOMs (Parameter ID: 10)

- `0` - No additional VDOMs
- `10` - 10 VDOMs
- `25` - 25 VDOMs
- `50` - 50 VDOMs
- `100` - 100 VDOMs
- `250` - 250 VDOMs
- `500` - 500 VDOMs

### Additional Services (Parameter ID: 43)

- `FGVMFC` - FortiConverter Service
- `FGVMFCEL` - FortiCare Elite

### Cloud Services (Parameter ID: 44)

- `FGTSOCA` - SOCaaS for VM
- `FGTZTNA` - ZTNA (Zero Trust Network Access)
- `FGTFAZC` - FortiAnalyzer Cloud
- `FGTSWNM` - SD-WAN Underlay

### Support Level (Parameter ID: 45)

- `FGVMFC247` - 24x7 Support
- `FGVMPREM` - Premium Support

### Example Configuration
```python
{
    "name": "Customer-A-FGT-VM-8Core",
    "product_type_id": 1,
    "parameters": [
        {"id": 1, "value": "8"},           # 8 vCPUs
        {"id": 2, "value": "FGVMUTP"},     # UTP bundle
        {"id": 10, "value": "10"},         # 10 VDOMs
        {"id": 44, "value": "FGTSOCA"}     # SOCaaS addon
    ]
}
```

---

## FortiAP (ID: 102)

### Device Models (Parameter ID: 55)

Indoor Models:
- `FP231F` - FortiAP-231F (Indoor, Wi-Fi 6)
- `FP431F` - FortiAP-431F (Indoor, Wi-Fi 6)
- `FP441K` - FortiAP-441K (Indoor, Wi-Fi 6E)

Outdoor Models:
- `FP231G` - FortiAP-231G (Outdoor ruggedized)
- `FP431G` - FortiAP-431G (Outdoor ruggedized)

Universal Models:
- `FPU431F` - FortiAP-U431F (Universal, indoor/outdoor)
- `FPU433F` - FortiAP-U433F (Universal, indoor/outdoor)

### Service Packages (Parameter ID: 56)

- `FAPHWFC247` - FortiCare 24x7
- `FAPHWFCPREM` - FortiCare Premium

### Add-On Services (Parameter ID: 57)

- `FAPHWFAZC` - FortiAnalyzer Cloud
- `NONE` - No add-ons

### Example Configuration
```python
{
    "name": "Customer-A-FAP-231F",
    "product_type_id": 102,
    "parameters": [
        {"id": 55, "value": "FP231F"},       # Indoor Wi-Fi 6
        {"id": 56, "value": "FAPHWFC247"},   # 24x7 support
        {"id": 57, "value": "FAPHWFAZC"}     # FAZ Cloud addon
    ]
}
```

---

## FortiSwitch (ID: 103)

### Device Models (Parameter ID: 53)

Access Switches:
- `S108FP` - FortiSwitch-108F-POE
- `S124FP` - FortiSwitch-124F-POE
- `S148FP` - FortiSwitch-148F-POE

Aggregation Switches:
- `S224DF` - FortiSwitch-224D-FPOE
- `S448DP` - FortiSwitch-448D-POE
- `S524DF` - FortiSwitch-524D-FPOE
- `S548DF` - FortiSwitch-548D-FPOE

### Service Packages (Parameter ID: 54)

- `FSWHWFC247` - FortiCare 24x7
- `FSWHWFCPREM` - FortiCare Premium

### Example Configuration
```python
{
    "name": "Customer-A-FSW-124F",
    "product_type_id": 103,
    "parameters": [
        {"id": 53, "value": "S124FP"},       # 24-port POE switch
        {"id": 54, "value": "FSWHWFC247"}    # 24x7 support
    ]
}
```

---

## FortiEDR (ID: 206)

### Service Packages (Parameter ID: 46)

- `FEDRPDR` - EPP (Endpoint Protection Platform)
- `FEDRXDR` - XDR (Extended Detection and Response)

### Number of Endpoints (Parameter ID: 47)

- `25` - 25 endpoints
- `50` - 50 endpoints
- `100` - 100 endpoints
- `250` - 250 endpoints
- `500` - 500 endpoints
- `1000` - 1000 endpoints
- `2500` - 2500 endpoints
- `5000` - 5000 endpoints
- `10000` - 10000 endpoints

### Add-On Services (Parameter ID: 52)

- `FEDFOR` - FortiEDR Forensics
- `FEDGOA` - FortiGuard Outbreak Alert
- `FEDMDR` - FortiEDR MDR (Managed Detection & Response)
- `NONE` - No add-ons

### Cloud Storage (Parameter ID: 76)

- `1024` - 1 TB
- `5120` - 5 TB
- `10240` - 10 TB

### Example Configuration
```python
{
    "name": "Customer-A-EDR-250-Users",
    "product_type_id": 206,
    "parameters": [
        {"id": 46, "value": "FEDRPDR"},     # EPP service
        {"id": 47, "value": "250"},         # 250 endpoints
        {"id": 52, "value": "FEDMDR"},      # MDR addon
        {"id": 76, "value": "1024"}         # 1 TB storage
    ]
}
```

---

## FortiSASE (ID: 205)

### Number of Users (Parameter ID: 60)

- `25` - 25 users
- `50` - 50 users
- `100` - 100 users
- `250` - 250 users
- `500` - 500 users
- `1000` - 1000 users
- `2500` - 2500 users
- `5000` - 5000 users
- `10000` - 10000 users

### Service Package (Parameter ID: 61)

- `FSASEESS` - Essential
- `FSASEADV` - Advanced
- `FSASECOM` - Comprehensive

### Bandwidth (Mbps) (Parameter ID: 62)

- `25` - 25 Mbps
- `50` - 50 Mbps
- `100` - 100 Mbps
- `250` - 250 Mbps
- `500` - 500 Mbps
- `1000` - 1 Gbps
- `2500` - 2.5 Gbps
- `5000` - 5 Gbps
- `10000` - 10 Gbps

### Dedicated IPs (Parameter ID: 63)

- `0` - No dedicated IPs
- `1` - 1 dedicated IP
- `5` - 5 dedicated IPs
- `10` - 10 dedicated IPs
- `25` - 25 dedicated IPs

### Additional Compute Regions (Parameter ID: 64)

- `0` - No additional regions
- `1` - 1 additional region
- `2` - 2 additional regions
- `3` - 3 additional regions
- `5` - 5 additional regions

### SD-WAN On-Ramp Locations (Parameter ID: 65)

- `0` - No SD-WAN locations
- `1` - 1 SD-WAN location
- `2` - 2 SD-WAN locations
- `5` - 5 SD-WAN locations
- `10` - 10 SD-WAN locations

### Example Configuration
```python
{
    "name": "Customer-A-SASE-500-Users",
    "product_type_id": 205,
    "parameters": [
        {"id": 60, "value": "500"},         # 500 users
        {"id": 61, "value": "FSASEADV"},    # Advanced package
        {"id": 62, "value": "500"},         # 500 Mbps bandwidth
        {"id": 63, "value": "5"},           # 5 dedicated IPs
        {"id": 64, "value": "1"},           # 1 additional region
        {"id": 65, "value": "2"}            # 2 SD-WAN on-ramps
    ]
}
```

---

## FortiManager VM (ID: 2)

### Managed Devices (Parameter ID: 3)

- `10` - 10 managed devices
- `25` - 25 managed devices
- `50` - 50 managed devices
- `100` - 100 managed devices
- `250` - 250 managed devices
- `500` - 500 managed devices
- `1000` - 1000 managed devices
- `2500` - 2500 managed devices
- `5000` - 5000 managed devices
- `10000` - 10000 managed devices

### ADOMs (Parameter ID: 4)

- `1` - 1 ADOM
- `10` - 10 ADOMs
- `25` - 25 ADOMs
- `50` - 50 ADOMs
- `100` - 100 ADOMs
- `250` - 250 ADOMs
- `500` - 500 ADOMs
- `1000` - 1000 ADOMs

### Example Configuration
```python
{
    "name": "Customer-A-FMG-VM-100dev",
    "product_type_id": 2,
    "parameters": [
        {"id": 3, "value": "100"},          # 100 managed devices
        {"id": 4, "value": "25"}            # 25 ADOMs
    ]
}
```

---

## FortiAnalyzer VM (ID: 7)

### Daily Storage (GB) (Parameter ID: 21)

- `5` - 5 GB/day
- `25` - 25 GB/day
- `50` - 50 GB/day
- `100` - 100 GB/day
- `250` - 250 GB/day
- `500` - 500 GB/day
- `1000` - 1 TB/day
- `2000` - 2 TB/day
- `5000` - 5 TB/day

### ADOMs (Parameter ID: 22)

- `1` - 1 ADOM
- `10` - 10 ADOMs
- `25` - 25 ADOMs
- `50` - 50 ADOMs
- `100` - 100 ADOMs
- `250` - 250 ADOMs
- `500` - 500 ADOMs
- `1000` - 1000 ADOMs

### Example Configuration
```python
{
    "name": "Customer-A-FAZ-VM-100GB",
    "product_type_id": 7,
    "parameters": [
        {"id": 21, "value": "100"},         # 100 GB/day storage
        {"id": 22, "value": "10"}           # 10 ADOMs
    ]
}
```

---

## FortiClient EMS (ID: 5)

### Number of Endpoints (Parameter ID: 11)

- `25` - 25 endpoints
- `50` - 50 endpoints
- `100` - 100 endpoints
- `250` - 250 endpoints
- `500` - 500 endpoints
- `1000` - 1000 endpoints
- `2500` - 2500 endpoints
- `5000` - 5000 endpoints
- `10000` - 10000 endpoints
- `25000` - 25000 endpoints
- `50000` - 50000 endpoints

### Service Package (Parameter ID: 12)

- `FCTFC247` - FortiCare 24x7
- `FCTFCPREM` - FortiCare Premium
- `FCTZTP` - ZTNA (Zero Trust Network Access)

### ZTNA Add-On (Parameter ID: 13)

- `FCTZTNA` - ZTNA Add-on
- `NONE` - No ZTNA

### Example Configuration
```python
{
    "name": "Customer-A-EMS-500-Users",
    "product_type_id": 5,
    "parameters": [
        {"id": 11, "value": "500"},         # 500 endpoints
        {"id": 12, "value": "FCTZTP"},      # ZTNA package
        {"id": 13, "value": "NONE"}         # No additional ZTNA
    ]
}
```

---

## Quick Reference Table

### Common Product Types

| Product | Type ID | Key Parameters | Typical Use Case |
|---------|---------|----------------|------------------|
| FortiGate Hardware | 101 | Model, Bundle, Addons | Branch office, datacenter |
| FortiGate VM | 1 | CPU, Bundle, VDOMs | Cloud deployments, virtualization |
| FortiAP | 102 | Model, Support | Wireless access |
| FortiSwitch | 103 | Model, Support | Network switching |
| FortiEDR | 206 | Package, Endpoints, Addons | Endpoint security |
| FortiSASE | 205 | Users, Package, Bandwidth | SASE deployments |
| FortiManager VM | 2 | Devices, ADOMs | Centralized management |
| FortiAnalyzer VM | 7 | Storage, ADOMs | Centralized logging |
| FortiClient EMS | 5 | Endpoints, Package | Endpoint management |

### Parameter ID Quick Lookup

| Parameter ID | Used By | Purpose |
|--------------|---------|---------|
| 1 | FortiGate VM | CPU cores |
| 2 | FortiGate VM | Service bundle |
| 3 | FortiManager VM | Managed devices |
| 4 | FortiManager VM | ADOMs |
| 10 | FortiGate VM | VDOMs |
| 11 | FortiClient EMS | Endpoints |
| 21 | FortiAnalyzer VM | Daily storage |
| 22 | FortiAnalyzer VM | ADOMs |
| 27 | FortiGate Hardware | Device model |
| 28 | FortiGate Hardware | Service bundle |
| 29 | FortiGate Hardware | Add-on services |
| 43 | FortiGate VM | Additional services |
| 44 | FortiGate VM | Cloud services |
| 46 | FortiEDR | Service package |
| 47 | FortiEDR | Endpoints |
| 53 | FortiSwitch | Device model |
| 54 | FortiSwitch | Service package |
| 55 | FortiAP | Device model |
| 56 | FortiAP | Service package |
| 60 | FortiSASE | Users |
| 61 | FortiSASE | Service package |
| 62 | FortiSASE | Bandwidth |

---

## Usage Example: Creating Multiple Products

```python
from fortiflex_client import FortiFlexClient, get_oauth_token

# Authenticate
token = get_oauth_token(API_USERNAME, API_PASSWORD, client_id="flexvm")
client = FortiFlexClient(token, PROGRAM_SN)

# Create configurations for a full customer deployment
configs = []

# 1. FortiGate Hardware
fgt_config = client.create_config(
    name="Customer-A-FGT60F",
    product_type_id=101,
    account_id=12345,
    parameters=[
        {"id": 27, "value": "FGT60F"},
        {"id": 28, "value": "FGHWUTP"},
        {"id": 29, "value": "FGHWFAZC"}
    ]
)
configs.append(fgt_config)

# 2. FortiSwitch
fsw_config = client.create_config(
    name="Customer-A-FSW124F",
    product_type_id=103,
    account_id=12345,
    parameters=[
        {"id": 53, "value": "S124FP"},
        {"id": 54, "value": "FSWHWFC247"}
    ]
)
configs.append(fsw_config)

# 3. FortiAP
fap_config = client.create_config(
    name="Customer-A-FAP231F",
    product_type_id=102,
    account_id=12345,
    parameters=[
        {"id": 55, "value": "FP231F"},
        {"id": 56, "value": "FAPHWFC247"},
        {"id": 57, "value": "NONE"}
    ]
)
configs.append(fap_config)

# 4. FortiEDR
edr_config = client.create_config(
    name="Customer-A-EDR-250",
    product_type_id=206,
    account_id=12345,
    parameters=[
        {"id": 46, "value": "FEDRPDR"},
        {"id": 47, "value": "250"},
        {"id": 52, "value": "NONE"},
        {"id": 76, "value": "1024"}
    ]
)
configs.append(edr_config)

print(f"Created {len(configs)} configurations")
```

---

## Notes

- **Parameter values are case-sensitive** - Use exact values as shown
- **Not all combinations are valid** - Consult FortiFlex portal for supported combinations
- **Point costs vary** - Use the calculator API to get accurate pricing
- **This reference is for FortiFlex 25.1.0** - Check for updates in newer versions

---

**Source**: FortiFlex 25.1.0 Administration Guide
**Last Updated**: November 9, 2025
**Maintained By**: MSSP SE Team
