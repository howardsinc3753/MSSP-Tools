# MSSP-Tools

A collection of monitoring, troubleshooting, and automation tools for Managed Security Service Provider (MSSP) environments. Built by a Fortinet MSSP Solutions Engineer to help the community manage and troubleshoot security infrastructure at scale.

## 🎯 Purpose

These tools are designed to help MSSPs, partners, and network engineers:
- Monitor security infrastructure proactively
- Troubleshoot issues before they impact customers
- Automate repetitive diagnostic tasks
- Share best practices across the community

## 🛠️ Available Tools

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

## 🚀 Coming Soon

More MSSP tools are in development:
- FortiAnalyzer log analysis utilities
- FortiManager automation scripts
- Multi-vendor health check tools
- SIEM integration helpers

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

## 📞 Support

These are community-maintained tools. For issues or questions:

- **Tool-specific bugs:** Open an issue in this repository
- **Feature requests:** Submit via GitHub Issues
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
