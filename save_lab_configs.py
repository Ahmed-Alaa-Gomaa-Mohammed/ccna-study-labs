#!/usr/bin/env python3
"""
save_lab_configs.py - Automated Containerlab Configuration Persistence

This script:
1. Locates the Containerlab topology file (.clab.yml).
2. Identifies running network devices (Cisco IOL, IOS, etc.) and their management IPs.
3. Connects via SSH to issue 'write memory' and extract 'show running-config'.
4. Saves configurations to '<lab_folder>/configs/<node_name>.cfg'.
5. Updates the topology YAML file to point each node's 'startup-config' to its saved config.
"""

import os
import sys
import time
import re
import json
import pty
import select
import subprocess
from pathlib import Path

try:
    from ruamel.yaml import YAML
    HAS_RUAMEL = True
except ImportError:
    HAS_RUAMEL = False
    import yaml


def find_topology_file(explicit_path=None):
    """Locate the target Containerlab topology YAML file."""
    if explicit_path:
        p = Path(explicit_path)
        if not p.exists():
            print(f"[-] Error: Specified topology file does not exist: {explicit_path}")
            sys.exit(1)
        return p.resolve()

    # Search in current directory and 1 level deep
    cwd = Path.cwd()
    topos = list(cwd.glob("*.clab.yml")) + list(cwd.glob("*.clab.yaml"))
    if not topos:
        topos = list(cwd.glob("*/*.clab.yml")) + list(cwd.glob("*/*.clab.yaml"))

    if not topos:
        print("[-] Error: No Containerlab topology file (*.clab.yml) found.")
        print("    Usage: python3 save_lab_configs.py [path/to/topology.clab.yml]")
        sys.exit(1)

    if len(topos) == 1:
        return topos[0].resolve()

    print("[*] Multiple topology files found:")
    for idx, t in enumerate(topos, 1):
        print(f"  [{idx}] {t.relative_to(cwd)}")
    choice = input("Select topology number [1]: ").strip() or "1"
    try:
        return topos[int(choice) - 1].resolve()
    except (ValueError, IndexError):
        print("[-] Invalid choice. Exiting.")
        sys.exit(1)


def parse_topology(topo_path):
    """Load topology YAML preserving formatting if possible."""
    if HAS_RUAMEL:
        yaml_parser = YAML()
        yaml_parser.preserve_quotes = True
        yaml_parser.indent(mapping=2, sequence=4, offset=2)
        with open(topo_path, "r", encoding="utf-8") as f:
            data = yaml_parser.load(f)
        return data, yaml_parser
    else:
        with open(topo_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data, None


def get_running_containers(lab_name):
    """Find running Docker containers matching the lab name."""
    cmd = [
        "docker", "ps", "--filter", f"name=clab-{lab_name}-",
        "--format", "{{.Names}}\t{{.ID}}"
    ]
    try:
        out = subprocess.check_output(cmd, text=True).strip()
    except Exception as e:
        print(f"[-] Error querying Docker: {e}")
        return {}

    if not out:
        return {}

    containers = {}
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) >= 2:
            c_name, c_id = parts[0], parts[1]
            # Extract node short name: clab-<lab_name>-<node_name>
            prefix = f"clab-{lab_name}-"
            if c_name.startswith(prefix):
                node_name = c_name[len(prefix):]
                # Get IP
                ip_cmd = ["docker", "inspect", c_id, "--format", "{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}"]
                try:
                    ip = subprocess.check_output(ip_cmd, text=True).strip()
                    if ip:
                        containers[node_name] = {"ip": ip, "container": c_name}
                except Exception:
                    pass
    return containers


def ssh_extract_config(ip, username="admin", password="admin", timeout=12):
    """Connect via SSH using a PTY to write memory and extract running-config."""
    master, slave = pty.openpty()
    pid = os.fork()

    if pid == 0:
        os.close(master)
        os.setsid()
        import fcntl, termios
        fcntl.ioctl(slave, termios.TIOCSCTTY, 0)
        for fd in (0, 1, 2):
            os.dup2(slave, fd)
        os.close(slave)
        ssh_cmd = [
            "ssh",
            "-o", "UserKnownHostsFile=/dev/null",
            "-o", "StrictHostKeyChecking=no",
            "-o", "ConnectTimeout=5",
            f"{username}@{ip}"
        ]
        os.execvp("ssh", ssh_cmd)

    os.close(slave)
    buf = b""
    start = time.time()
    logged_in = False

    try:
        # Step 1: Handle password prompt
        while time.time() - start < timeout:
            r, _, _ = select.select([master], [], [], 0.3)
            if r:
                chunk = os.read(master, 1024)
                buf += chunk
                if b"Password:" in buf or b"password:" in buf:
                    os.write(master, f"{password}\n".encode())
                    logged_in = True
                    break

        if not logged_in:
            os.close(master)
            os.waitpid(pid, 0)
            return None, "Failed to reach password prompt"

        time.sleep(1)

        # Step 2: Save to startup-config on the box (write memory)
        os.write(master, b"terminal length 0\n")
        time.sleep(0.3)
        os.write(master, b"write memory\n")
        time.sleep(1.2)

        # Step 3: Fetch running config
        os.write(master, b"show running-config\n")
        time.sleep(0.8)

        full_output = b""
        wait_start = time.time()
        while time.time() - wait_start < timeout:
            r, _, _ = select.select([master], [], [], 1.5)
            if not r:
                break
            chunk = os.read(master, 4096)
            full_output += chunk
            if b"#" in chunk and b"\nend" in full_output:
                break

        os.write(master, b"exit\n")
        time.sleep(0.2)
    finally:
        try:
            os.close(master)
            os.waitpid(pid, 0)
        except Exception:
            pass

    text = full_output.decode("utf-8", errors="ignore")

    # Match configuration between 'version ...' or 'hostname ...' and 'end'
    m = re.search(r"((?:version \d+\.\d+|hostname\s+\S+).*?\nend)", text, re.DOTALL)
    if m:
        clean_cfg = m.group(1).strip() + "\n"
        return clean_cfg, None

    return None, "Could not locate clean config delimiters in output"


def main():
    if len(sys.argv) > 1 and sys.argv[1] in ("-h", "--help"):
        print("Usage: python3 save_lab_configs.py [path/to/topology.clab.yml]")
        print("\nAutomates saving live running-configs from Containerlab nodes,")
        print("writing configs to a 'configs/' folder, and updating the topology file.")
        sys.exit(0)

    topo_arg = sys.argv[1] if len(sys.argv) > 1 else None
    topo_file = find_topology_file(topo_arg)
    topo_dir = topo_file.parent

    print(f"[*] Target topology: {topo_file}")

    # Parse topology
    data, yaml_parser = parse_topology(topo_file)
    lab_name = data.get("name", "ccna")
    nodes_spec = data.get("topology", {}).get("nodes", {})

    print(f"[*] Lab name: {lab_name}")
    print(f"[*] Total nodes defined in topology: {len(nodes_spec)}")

    # Check running containers
    running_containers = get_running_containers(lab_name)
    if not running_containers:
        print(f"[-] Error: No active containers found for lab '{lab_name}'.")
        print(f"    Make sure the lab is deployed using: sudo containerlab deploy -t {topo_file.name}")
        sys.exit(1)

    print(f"[+] Detected {len(running_containers)} active containers.")

    # Prepare configs directory
    configs_dir = topo_dir / "configs"
    configs_dir.mkdir(parents=True, exist_ok=True)

    saved_nodes = []

    # Process nodes
    for node_name, spec in nodes_spec.items():
        kind = spec.get("kind", "")
        # Only process network OS nodes (cisco_iol, cisco_ios, etc.)
        if "cisco" not in kind and "ceos" not in kind and "juniper" not in kind:
            continue

        if node_name not in running_containers:
            print(f"[!] Warning: Node '{node_name}' is not currently running. Skipping.")
            continue

        ip = running_containers[node_name]["ip"]
        print(f"[*] Extracting config from '{node_name}' ({ip})...", end="", flush=True)

        cfg_text, err = ssh_extract_config(ip, username="admin", password="admin")
        if cfg_text:
            cfg_path = configs_dir / f"{node_name}.cfg"
            with open(cfg_path, "w", encoding="utf-8") as f:
                f.write(cfg_text)
            print(f" [OK] -> saved to configs/{node_name}.cfg ({len(cfg_text.splitlines())} lines)")

            # Update spec in topology data
            rel_cfg_path = f"configs/{node_name}.cfg"
            spec["startup-config"] = rel_cfg_path
            saved_nodes.append(node_name)
        else:
            print(f" [FAIL] ({err})")

    if not saved_nodes:
        print("[-] No configurations were saved.")
        sys.exit(1)

    # Save updated topology file
    print(f"[*] Updating topology file '{topo_file.name}' with startup-config references...")
    if HAS_RUAMEL and yaml_parser:
        with open(topo_file, "w", encoding="utf-8") as f:
            yaml_parser.dump(data, f)
    else:
        with open(topo_file, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)

    print(f"[+] Successfully saved configurations for {len(saved_nodes)} nodes:")
    for n in saved_nodes:
        print(f"    - {n} -> configs/{n}.cfg")

    print("\n[+] Done! You can now commit your persistent changes to Git:")
    print("    git add .")
    print('    git commit -m "feat(configs): save dynamic CLI configurations"')


if __name__ == "__main__":
    main()
