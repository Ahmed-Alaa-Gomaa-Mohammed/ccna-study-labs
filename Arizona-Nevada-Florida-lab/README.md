# Lab 01: Arizona - Nevada - Florida Multi-Site Enterprise Lab

An enterprise multi-site network topology based on CBT Nuggets CCNA/CCNP scenarios, simulating an Arizona Corporate HQ, Nevada and Florida branch offices, carrier Metro Ethernet WAN transit, and an Internet gateway.

---

## Topology Diagram

![Arizona-Nevada-Florida Topology Diagram](topology.svg)

<details>
<summary><b>Click to view Mermaid Diagram code</b></summary>

```mermaid
flowchart TD
    classDef router fill:#DBEAFE,stroke:#2563EB,stroke-width:2px,color:#1E3A8A;
    classDef switch fill:#D1FAE5,stroke:#059669,stroke-width:2px,color:#064E3B;
    classDef access fill:#CCFBF1,stroke:#0D9488,stroke-width:2px,color:#134E4A;
    classDef cloud fill:#FEF3C7,stroke:#D97706,stroke-width:2px,color:#78350F;
    classDef host fill:#F3F4F6,stroke:#4B5563,stroke-width:2px,color:#1F2937;

    subgraph Service_Provider ["SERVICE PROVIDER (WAN & INTERNET)"]
        Internet(["Internet Gateway (Cloud)<br><b>eth1 (Public IP Transit)</b>"]):::cloud
        MetroE(["MetroE Carrier Bridge (Cloud)<br><b>br0 [eth1, eth2, eth3]</b>"]):::cloud
    end

    subgraph Arizona_HQ ["ARIZONA HQ CAMPUS (Subnets: 10.16.0.0/24 & 10.1.1.0/24)"]
        R1["R1-AZ (Router)<br><b>Eth1/0: 10.16.0.2/24</b>"]:::router
        Core1["Core1 (Switch)<br><b>SVI Vlan1: 10.16.0.1/24</b>"]:::switch
        Core2["Core2 (Switch)<br>Distribution / Core"]:::switch
        Access1["Access1 (Switch)<br>Access Layer"]:::access
        PC10["PC-10 (Host PC)<br><b>eth1: 10.1.1.10/24</b>"]:::host
        PC20["PC-20 (Host PC)<br><b>eth1: 10.1.1.11/24</b>"]:::host

        R1 ---|"Eth1/0 (10.16.0.2) &nbsp;&bull;&nbsp; Eth2/1 (10.16.0.1)"| Core1
        Core1 ===|"Eth2/3, Eth2/2 &nbsp;&bull;&nbsp; 802.1Q Trunk &nbsp;&bull;&nbsp; Eth3/0, Eth3/1"| Core2
        Core1 ---|"Eth2/0 &nbsp;&bull;&nbsp; Eth1/1"| Access1
        Core2 ---|"Eth3/2 &nbsp;&bull;&nbsp; Eth1/2"| Access1
        Access1 ---|"Eth1/0 &nbsp;&bull;&nbsp; eth1"| PC10
        Access1 ---|"Eth2/0 &nbsp;&bull;&nbsp; eth1"| PC20
    end

    subgraph Nevada_Branch ["NEVADA BRANCH OFFICE"]
        R2["R2-NV (Router)<br>Branch Gateway"]:::router
        NVSwitch["NV-Switch (Switch)<br>Branch Access"]:::switch
        NVPC["NV-PC (Host PC)<br>LAN Client"]:::host

        R2 ---|"Eth2/0 &nbsp;&bull;&nbsp; Eth4/3"| NVSwitch
        NVSwitch ---|"Eth0/1 &nbsp;&bull;&nbsp; eth1"| NVPC
    end

    subgraph Florida_Branch ["FLORIDA BRANCH OFFICE"]
        R3["R3-FL (Router)<br>Branch Gateway"]:::router
        FLSwitch["FL-Switch (Switch)<br>Branch Access"]:::switch
        FLPC["FL-PC (Host PC)<br>LAN Client"]:::host

        R3 ---|"Eth2/0 &nbsp;&bull;&nbsp; Eth4/3"| FLSwitch
        FLSwitch ---|"Eth0/1 &nbsp;&bull;&nbsp; eth1"| FLPC
    end

    Internet ---|"eth1 &nbsp;&bull;&nbsp; Public Transit &nbsp;&bull;&nbsp; Eth2/0"| R1
    MetroE ---|"eth1 &nbsp;&bull;&nbsp; MetroE Trunk &nbsp;&bull;&nbsp; Eth3/0"| R1
    MetroE ---|"eth2 &nbsp;&bull;&nbsp; MetroE L2 Link &nbsp;&bull;&nbsp; Eth1/0"| R2
    MetroE ---|"eth3 &nbsp;&bull;&nbsp; MetroE L2 Link &nbsp;&bull;&nbsp; Eth1/0"| R3
```
</details>

---

## IP Addressing Table

| Device Name | Layer 3 Interface | IP Address |
| :--- | :--- | :--- |
| **Core1** | `Vlan1` | `10.16.0.1/24` |
| **R1-AZ** | `Ethernet1/0` | `10.16.0.2/24` |
| **PC-10** | `eth1` | `10.1.1.10/24` |
| **PC-20** | `eth1` | `10.1.1.11/24` |

---

## Lab Scenario & Exercise Overview

<!-- Exercise explanation placeholder: Add your brief explanation of the exercise below -->
> [!NOTE]
> **Exercise Summary:**
> *(Placeholder for exercise overview and scenario background. You can insert your lab description, topology requirements, and problem statements here).*

### Key Learning Tasks
* **Task 1: Base Configurations & Hostnames**
  * Set hostnames, disable domain lookup, configure synchronous console logging, and verify MOTD banners.
* **Task 2: Layer 2 Switching & Trunks**
  * Configure 802.1Q trunks between Core1, Core2, and Access1; set up EtherChannel and verify Spanning Tree Protocol (Rapid-PVST).
* **Task 3: IP Routing & Core Gateway**
  * Establish IP connectivity between Arizona Core SVI `10.16.0.1/24` and Router `10.16.0.2/24`.
* **Task 4: WAN & Branch Connectivity**
  * Configure routing across the Metro Ethernet WAN transit between Arizona, Nevada, and Florida.

---

## Quickstart Commands

```bash
# Navigate to this lab directory
cd Arizona-Nevada-Florida-lab

# Deploy the topology
containerlab deploy --topo ccna.clab.yml

# Check running status
containerlab inspect --topo ccna.clab.yml

# SSH into AZ Router (Credentials: admin / admin)
ssh admin@clab-ccna-R1-AZ

# Save CLI changes to configs/ and update ccna.clab.yml
python3 ../save_lab_configs.py ccna.clab.yml

# Destroy the lab
containerlab destroy --topo ccna.clab.yml --cleanup
```
