# CCNA & CCNP Study Labs

A structured collection of hands-on networking labs powered by [Containerlab](https://containerlab.dev/), Cisco IOL (IOS on Linux), and FRRouting. Designed for real-world practice, protocol analysis, and configuration automation across CCNA, CCNP Enterprise (ENCOR 350-401), and Advanced Routing (ENARSI 300-410).

---

## 📚 Lab Catalog

| Lab # | Directory | Focus / Topics | Node Count | Status |
| :--- | :--- | :--- | :---: | :---: |
| **01** | [**Arizona - Nevada - Florida Multi-Site Lab**](Arizona-Nevada-Florida-lab/README.md) | Enterprise Campus Switching (Core/Access), 802.1Q Trunks, EtherChannel, SVI routing, Metro Ethernet WAN transit, and Internet gateway | 10 | ✅ Complete |
| **02** | *Upcoming Lab* | Single & Multi-Area OSPFv2 / OSPFv3, DR/BDR Election, Route Summarization | — | ⏳ Planned |
| **03** | *Upcoming Lab* | Advanced BGP Routing (eBGP & iBGP Peering, Route Reflectors, Policy Filtering) | — | ⏳ Planned |
| **04** | *Upcoming Lab* | First-Hop Redundancy (HSRP, VRRP) and IPv4/IPv6 Dual Stack | — | ⏳ Planned |

*(New labs are added progressively as study topics advance).*

---

## 🗂️ Repository Structure

Each lab is maintained as a self-contained module containing its own Containerlab topology specification, initial/saved device startup configurations, and dedicated documentation:

```text
ccna-study-labs/
├── Arizona-Nevada-Florida-lab/         # Lab 01: Multi-Site Enterprise Lab
│   ├── ccna.clab.yml                   # Containerlab topology definition
│   ├── topology.svg                    # EVE-NG / GNS3 styled vector topology diagram
│   ├── topology.dot                    # Graphviz DOT diagram source
│   ├── README.md                       # Lab documentation, data IP table & exercise tasks
│   └── configs/                        # Cisco IOL startup configurations (NVRAM synced)
│       ├── R1-AZ.cfg
│       ├── Core1.cfg
│       └── ...
├── save_lab_configs.py                 # Automated config snapshot & NVRAM sync utility
└── README.md                           # Master repository index and catalog
```

---

## 🚀 Environment Prerequisites

1. **Linux OS** with Docker installed and running.
2. **Containerlab**:
   ```bash
   bash -c "$(curl -sL https://get.containerlab.dev)"
   ```
3. **Cisco IOL Docker Images**:
   - Cisco IOL L3: `tkdebnath/cisco_iol:17.12.01`
   - Cisco IOL L2: `tkdebnath/cisco_iol:L2-17.12.01`
4. **Python 3 & Dependencies**:
   ```bash
   pip install pexpect pyyaml
   ```

---

## 🛠️ Automated Configuration Snapshot Tool

This repository includes [`save_lab_configs.py`](save_lab_configs.py), a zero-sudo automation tool that connects to running lab nodes, runs `write memory`, extracts the clean `running-config`, and synchronizes the `.clab.yml` startup config paths.

### How to Save Lab Progress:

```bash
# Automatically saves the default or first detected lab:
python3 save_lab_configs.py

# Or target a specific lab directly:
python3 save_lab_configs.py Arizona-Nevada-Florida-lab/ccna.clab.yml
```

**Key Features:**
* **Self-Healing / Offline Startup**: If the lab is currently stopped, the script automatically boots it up, allows NVRAM state to load into running nodes, extracts the running configs, and updates the topology.
* **Non-Privileged Execution**: Runs seamlessly without requiring `sudo`.
* **Git-Ready Output**: Strips non-deterministic timestamps and volatile parameters for clean, diff-friendly Git commits.

---

## 📝 Adding a New Lab

To add a new lab to this collection:
1. Create a dedicated folder: `mkdir My-New-Lab`
2. Define the Containerlab topology: `My-New-Lab/<name>.clab.yml`
3. Generate high-resolution topology visuals and documentation:
   - Create `My-New-Lab/README.md` with an IP addressing table and exercise objectives.
   - Store device configs in `My-New-Lab/configs/`.
4. Register the new lab in the [Lab Catalog](#-lab-catalog) table above.
