# MSSP-Tools

A collection of monitoring, troubleshooting, and automation tools for Managed Security Service Provider (MSSP) environments. Built by a Fortinet MSSP Solutions Engineer to help the community manage and troubleshoot security infrastructure at scale.

## 🎯 Purpose

These tools are designed to help MSSPs, partners, and network engineers:
- Monitor security infrastructure proactively
- Troubleshoot issues before they impact customers
- Automate repetitive diagnostic tasks
- Share best practices across the community

## 🛠️ Available Tools

### [FortiFlex MSSP Automation Toolkit](FortiFlex-Dev-Package/fortiflex-mssp-toolkit/)
**Status:** ✅ Production Ready - November 2025

Complete Python automation toolkit for Fortinet FortiFlex MSSP operations. Manage customer lifecycle from onboarding to offboarding with production-ready scripts covering all 7 critical use cases.

**Key Features:**
- Customer onboarding with cost estimation
- Service expansion and modification
- Daily consumption reporting for billing
- Entitlement suspension/reactivation
- Multi-tenant operations dashboard
- MSSP commitment tracking (50K points/year)
- Complete FortiFlex 25.1.0 product catalog

**What's Included:**
- 7 production-ready use case scripts
- Complete API integration guide (Parts 1 & 2)
- Full product type reference
- Automated testing utilities
- November 2025 compatibility patches

**Use Cases:**
- Automated customer onboarding workflows
- Monthly billing and invoicing
- Service lifecycle management
- MSSP program balance monitoring
- Multi-customer operations at scale

[📖 View Documentation →](FortiFlex-Dev-Package/fortiflex-mssp-toolkit/)

---

### [FortiGate Conserve Mode Monitor](FortiGate-Monitor-Tool/)
**Status:** ✅ Production Ready v2.2

Monitor FortiGate memory usage in real-time to prevent conserve mode before it impacts traffic flow. Tracks top 30 processes by memory consumption via FortiOS REST API.

**Key Features:**
- Real-time CPU and memory monitoring
- Conserve mode threshold detection (79% warning, 88% critical)
- Multi-device support for A/A clusters
- JSON + human-readable logging
- Process-level memory analysis

**Use Cases:**
- 24/7 monitoring of production FortiGate clusters
- Proactive alerting before conserve mode activation
- Memory leak detection and troubleshooting
- Capacity planning and trend analysis

[📖 View Documentation →](FortiGate-Monitor-Tool/)

---

### [SOCaaS Python SDK](SOCaaS-SDK/)
**Status:** ✅ Production Ready - February 2026

Python SDK for Fortinet SOCaaS (Security Operations Center as a Service) API. Enables MSSP partners to automate alert triage, add investigation notes, monitor for new alerts, and integrate with third-party platforms.

**Key Features:**
- Alert management: list, get details (IOCs/events/endpoints), update status
- Investigation comments: add analyst notes to alerts
- Service requests: list, create, track support tickets
- Alert polling: background monitoring with webhook delivery
- MSSP client management: multi-tenant operations
- Webhook integrations: ServiceNow, Slack, Teams, PagerDuty

**What's Included:**
- 6 partner-facing example scripts
- Webhook integration guide with setup for 5 platforms
- Credential file template and 3 auth methods
- Full API reference documentation

**Use Cases:**
- Automated alert triage and enrichment workflows
- SOAR/SIEM integration via webhooks
- Investigation note automation during incident response
- Multi-tenant alert monitoring across MSSP clients
- ServiceNow incident creation from SOCaaS alerts

[📖 View Documentation →](SOCaaS-SDK/)

---

### [FortiZTP Python SDK](FortiZTP/)
**Status:** ✅ Production Ready - January 2026

Python SDK for Fortinet FortiZTP (Zero Touch Provisioning) API. Automate device provisioning, script management, and firmware deployment for MSSP environments.

[📖 View Documentation →](FortiZTP/)

---

## 🚀 Coming Soon

More MSSP tools are in development:
- FortiManager automation scripts
- FortiAnalyzer log analysis utilities
- Multi-vendor health check tools

## 💡 Contributing

Have a tool that would help the MSSP community? Contributions are welcome!

1. Fork this repository
2. Create a new directory for your tool
3. Include README, LICENSE, and proper documentation
4. Submit a pull request

Please ensure all tools include:
- Clear documentation
- Proper error handling
- Security best practices
- Disclaimer about non-official status

## ⚠️ Disclaimer

**These tools are provided for educational and diagnostic purposes only.**

- **NOT official Fortinet products** - These tools are not endorsed, tested, or maintained by Fortinet, Inc.
- **Use at your own risk** - Always test in lab environments before production deployment
- **No warranties** - Provided "AS IS" without warranties of any kind
- **No liability** - Neither the author nor Fortinet, Inc. shall be held liable for any damages, outages, or issues resulting from use of these tools

By using any tool in this repository, you agree to:
1. Test and validate in non-production environments first
2. Assume full responsibility for deployment and outcomes
3. Validate all outputs independently before taking action

## 📞 Support & Bug Reports

These are community-maintained tools. For issues or questions:

### Reporting Bugs
Found a bug? Help us improve! Please open a GitHub Issue with:

1. **Go to:** https://github.com/howardsinc3753/MSSP-Tools/issues
2. **Click:** "New Issue"
3. **Include:**
   - Tool name (e.g., "SOCaaS SDK", "FortiFlex MSSP Toolkit", "FortiGate Monitor", "FortiZTP SDK")
   - Description of the issue
   - Steps to reproduce
   - Expected vs actual behavior
   - Your environment (OS, Python version, etc.)
   - Error messages or logs (remove any credentials!)

### Other Support
- **Feature requests:** Submit via [GitHub Issues](https://github.com/howardsinc3753/MSSP-Tools/issues)
- **Fortinet product support:** Contact [Fortinet TAC](https://support.fortinet.com) (not responsible for these tools)
- **General MSSP questions:** Engage with the Fortinet community forums

## 👤 About

**Author:** Daniel Howard  
**Role:** MSSP Solutions Engineer, Fortinet  
**Note:** These tools are personal projects developed to support the MSSP community and are not official Fortinet products.

## 📄 License

All tools in this repository are licensed under the MIT License unless otherwise specified. See individual tool directories for specific license files.

---

**⭐ Found these tools helpful?** Give this repo a star and share it with your network engineering community!
