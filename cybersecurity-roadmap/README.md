# 🎯 Cybersecurity Certification Roadmap

A comprehensive, interactive cybersecurity certification roadmap that maps resources (YouTube channels, labs, tools) to specific certification syllabi, with a professional PDF generator featuring QR codes.

## 📋 Overview

This project generates a professional, multi-page PDF roadmap covering **13 stages** (Stage 0 to Stage 12) of cybersecurity learning, from absolute beginner to expert-level specializations.

### Features

✅ **Comprehensive Coverage**: 12 certifications mapped across 13 learning stages  
✅ **Resource Mapping**: YouTube channels, labs, and tools mapped to specific certs  
✅ **Professional PDF**: Multi-page document with proper formatting and styling  
✅ **QR Codes**: Quick access to resources with QR codes (includes easter egg!)  
✅ **Clickable Links**: All URLs are clickable hyperlinks  
✅ **Visual Design**: Color-coded sections and professional layout  
✅ **Tool Reference**: Complete categorized tool directory  
✅ **Progress Tracking**: Structured stages for tracking your journey  

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

### Installation

1. **Navigate to the roadmap directory**:
   ```bash
   cd cybersecurity-roadmap
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Generate the PDF**:
   ```bash
   python roadmap_generator.py
   ```

4. **Find your PDF**:
   The generated PDF will be in the `output/` directory:
   ```
   output/cybersecurity_roadmap.pdf
   ```

## 📚 Roadmap Structure

### Stage Progression

| Stage | Level | Focus | Key Certifications |
|-------|-------|-------|-------------------|
| **0** | Absolute Zero | No IT background required | - |
| **1** | Beginner Hacker | Foundation skills | THM JR, eJPT, CEH |
| **2** | Junior Pentester | Practical skills | - |
| **3** | Real Pentester | Industry ready | PNPT |
| **4** | OSCP Level | Industry standard | OSCP |
| **5** | Complete Pentester | Advanced comprehensive | CPTS |
| **6** | Red Team/Evasion | Red team operations | OSEP |
| **7** | Web God Level | Web security expert | OSWE |
| **8** | Defensive Mindset | Blue team skills | OSDA |
| **9** | Wireless Specialist | Wireless security | OSWP |
| **10** | Exploit Development | Binary exploitation | OSED |
| **11** | Exploit Elite | Advanced exploitation | OSEE |
| **12** | macOS Researcher | macOS security | OSMR |

## 🎓 Certifications Covered

### Entry Level (3 certifications)
- **THM JR**: TryHackMe Junior Penetration Tester
- **eJPT**: eLearnSecurity Junior Penetration Tester
- **CEH**: Certified Ethical Hacker

### Attack-Focused (5 certifications)
- **PNPT**: Practical Network Penetration Tester
- **OSCP**: Offensive Security Certified Professional
- **CPTS**: Certified Penetration Testing Specialist
- **OSEP**: Offensive Security Experienced Penetration Tester
- **OSWE**: Offensive Security Web Expert

### Additional Specializations (5 certifications)
- **OSDA**: Offensive Security Defense Analyst
- **OSWP**: Offensive Security Wireless Professional
- **OSED**: Offensive Security Exploit Developer
- **OSEE**: Offensive Security Exploitation Expert
- **OSMR**: Offensive Security macOS Researcher

## 📺 YouTube Channels Mapped

### Foundation Channels
- NetworkChuck
- Learn Linux TV
- PowerCert Animated Videos
- David Bombal

### Pentesting & CTFs
- IppSec
- The Cyber Mentor
- John Hammond
- HackerSploit
- TryHackMe Official

### Advanced & Specialized
- Rana Khalil (OSWE)
- LiveOverflow (Binary Exploitation)
- STÖK, NahamSec, InsiderPhD (Bug Bounty)
- ZeroPoint Security, Sektor7 (Red Team)
- Patrick Wardle (macOS Security)

*See the generated PDF for complete channel directory with QR codes!*

## 🧪 Practice Labs Included

- **Beginner**: OverTheWire, PicoCTF
- **Intermediate**: TryHackMe Paths, HTB Academy
- **Advanced**: HTB Pro Labs, Proving Grounds
- **Specialized**: PortSwigger Academy, Exploit Education

## 🛠️ Tools Categorized

### By Category
- **Networking & Enumeration**: Nmap, Masscan, RustScan, Enum4linux
- **Passwords**: Hashcat, John the Ripper, Hydra
- **Web Testing**: Burp Suite, OWASP ZAP, FFUF, SQLmap
- **Exploitation**: Metasploit, Searchsploit
- **Privilege Escalation**: LinPEAS, WinPEAS, PowerUp
- **Active Directory**: BloodHound, PowerView, Mimikatz, Rubeus
- **Red Team**: Sliver, Mythic, Empire, Covenant
- **Pivoting**: Chisel, Ligolo-NG, ProxyChains
- **Wireless**: Aircrack-ng suite, Bettercap, Kismet
- **Exploit Dev**: WinDbg, Ghidra, IDA Pro, GDB
- **Defensive**: Splunk, Elastic, Security Onion, YARA
- **macOS**: Hopper, LLDB, Frida

## 📂 Project Structure

```
cybersecurity-roadmap/
├── roadmap_generator.py      # Main PDF generator script
├── requirements.txt           # Python dependencies
├── README.md                  # This file
├── data/                      # JSON data files
│   ├── certifications.json    # Certification details
│   ├── youtube_channels.json  # YouTube channel mappings
│   ├── labs.json             # Lab platform mappings
│   └── tools.json            # Tool categorizations
└── output/                   # Generated PDFs
    └── cybersecurity_roadmap.pdf
```

## 🎨 PDF Features

The generated PDF includes:

1. **Cover Page** - Title, overview, and key statistics
2. **Table of Contents** - Easy navigation
3. **Foundation Section** - Prerequisites and foundational resources
4. **13 Stage Sections** - Each with:
   - Goals and description
   - Relevant certifications
   - YouTube channels (with links)
   - Practice labs and platforms
   - Essential tools table
5. **Complete Tool Reference** - All tools categorized
6. **YouTube Directory** - All channels with QR codes
7. **Quick Resource Links** - Important platform links
8. **Easter Egg** - Hidden rickroll QR code 😉

## 🎯 Usage Tips

### For Beginners (Stage 0-1)
1. Start with foundation YouTube channels (NetworkChuck, Learn Linux TV)
2. Complete OverTheWire Bandit for Linux basics
3. Follow TryHackMe Pre-Security and Complete Beginner paths

### For Intermediate (Stage 2-4)
1. Focus on TryHackMe Offensive Pentesting or HTB Academy
2. Practice on HTB Easy/Medium boxes
3. Prepare for OSCP with TJ Null list

### For Advanced (Stage 5+)
1. Choose your specialization (Web, Red Team, Exploit Dev, etc.)
2. Deep dive into specific certifications
3. Practice on Pro Labs and advanced platforms

## 🔧 Customization

### Modify Data Files

Edit JSON files in the `data/` directory to:
- Add new certifications
- Update YouTube channels
- Add new labs or tools
- Modify stage mappings

### Regenerate PDF

After making changes:
```bash
python roadmap_generator.py
```

## 📊 Statistics

- **Total Stages**: 13 (0-12)
- **Certifications**: 12
- **YouTube Channels**: 40+
- **Practice Labs**: 30+
- **Tools & Frameworks**: 70+

## 🐛 Troubleshooting

### PDF is blank
- Ensure all JSON files are valid
- Check that data files are in the `data/` directory
- Verify Python dependencies are installed

### QR codes not generating
- Install pillow: `pip install pillow`
- Check internet connection (not required but helpful for testing)

### Import errors
```bash
pip install --upgrade reportlab qrcode pillow
```

## 📝 License

This project is open source and available for educational purposes.

## 🤝 Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Make your changes
3. Test PDF generation
4. Submit a pull request

## 📧 Contact

For questions or suggestions, please open an issue on GitHub.

## ⚠️ Disclaimer

This roadmap is for educational purposes. Always practice ethical hacking and obtain proper authorization before testing systems you don't own.

---

**Generated with ❤️ for the cybersecurity community**

*Last Updated: 2026-02-02*
