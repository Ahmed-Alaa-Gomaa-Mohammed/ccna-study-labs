#!/usr/bin/env python3
"""
save_lab_configs.py - Automated Containerlab Configuration Persistence

Features:
1. Locates the Containerlab topology file (.clab.yml).
2. Checks if the lab containers are currently running:
   - If running: extracts configs directly from live devices.
   - If NOT running: automatically deploys the lab (loading the existing NVRAM state
     into the devices), waits for nodes to boot and initialize SSH, and extracts configs.
3. Issues 'write memory' on each device.
4. Extracts clean 'show running-config' via SSH.
5. Saves configurations to '<lab_folder>/configs/<node_name>.cfg'.
6. Updates the topology YAML file (using ruamel.yaml to preserve comments/formatting)
   to set 'startup-config: configs/<node_name>.cfg' for all saved nodes.
7. Optional flag '--destroy-after': shuts down the lab after extraction if it was started by the script.
"""

import os
import sys
import time
import re
import socket
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


def print_help():
    print("""Usage: python3 save_lab_configs.py [path/to/topology.clab.yml] [options]

Options:
  -h, --help           Show this help message and exit.
  --destroy-after      If the lab was not running and had to be started automatically,
                       destroy it after saving the configurations.

Description:
  Automates extracting live running-configs from Containerlab nodes, saving them into
  a 'configs/' folder, and updating the topology YAML file to use them as startup-configs.
  If the lab is stopped, the script starts it to let nodes load their NVRAM state,
  captures the configs, and updates your topology.
""")
    sys.exit(0)


def find_topology_file(explicit_path=None):
    """Locate the target Containerlab topology YAML file."""
    if explicit_path:
        p = Path(explicit_path)
        if not p.exists():
            print(f"[-] Error: Specified topology file does not exist: {explicit_path}")
            sys.exit(1)
        return p.resolve()

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
            prefix = f"clab-{lab_name}-"
            if c_name.startswith(prefix):
                node_name = c_name[len(prefix):]
                ip_cmd = ["docker", "inspect", c_id, "--format", "{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}"]
                try:
                    ip = subprocess.check_output(ip_cmd, text=True).strip()
                    if ip:
                        containers[node_name] = {"ip": ip, "container": c_name}
                except Exception:
                    pass
    return containers


def ensure_lab_running(topo_file, lab_name):
    """Check if lab is active; if not, deploy it so NVRAM is loaded into devices."""
    running = get_running_containers(lab_name)
    if running:
        print(f"[+] Lab '{lab_name}' is already running ({len(running)} active containers).")
        return running, False

    print(f"[*] Lab '{lab_name}' is not running.")
    print(f"[*] Starting lab to load existing NVRAM / saved state into devices...")
    print(f"    Running: containerlab deploy -t {topo_file.name}")

    deploy_cmd = ["containerlab", "deploy", "-t", str(topo_file)]
    res = subprocess.run(deploy_cmd, cwd=topo_file.parent)
    if res.returncode != 0:
        print(f"[-] Error: Failed to start Containerlab (exit code {res.returncode}).")
        sys.exit(res.returncode)

    running = get_running_containers(lab_name)
    if not running:
        print("[-] Error: No containers detected even after deployment.")
        sys.exit(1)

    print(f"[+] Lab deployed successfully ({len(running)} containers up).")
    return running, True


def wait_for_node_ssh(ip, timeout=50):
    """Wait until SSH port 22 on the device is open and responsive."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            with socket.create_connection((ip, 22), timeout=1.0):
                return True
        except (socket.timeout, ConnectionRefusedError, OSError):
            time.sleep(1.5)
    return False


def ssh_extract_config(ip, username="admin", password="admin", timeout=15, max_retries=3):
    """Connect via SSH using PTY to issue write memory and extract show running-config."""
    for attempt in range(1, max_retries + 1):
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
            while time.time() - start < timeout:
                r, _, _ = select.select([master], [], [], 0.3)
                if r:
                    try:
                        chunk = os.read(master, 1024)
                    except OSError:
                        break
                    if not chunk:
                        break
                    buf += chunk
                    if b"Password:" in buf or b"password:" in buf:
                        os.write(master, f"{password}\n".encode())
                        logged_in = True
                        break

            if not logged_in:
                os.close(master)
                os.waitpid(pid, 0)
                if attempt < max_retries:
                    time.sleep(2)
                    continue
                return None, "Failed to reach password prompt"

            time.sleep(1)

            # Step 1: Write memory to ensure NVRAM matches current running-config
            os.write(master, b"terminal length 0\n")
            time.sleep(0.3)
            os.write(master, b"write memory\n")
            time.sleep(1.5)

            # Step 2: Fetch running configuration
            os.write(master, b"show running-config\n")
            time.sleep(0.8)

            full_output = b""
            wait_start = time.time()
            while time.time() - wait_start < timeout:
                r, _, _ = select.select([master], [], [], 1.5)
                if not r:
                    break
                try:
                    chunk = os.read(master, 4096)
                except OSError:
                    break
                if not chunk:
                    break
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
        m = re.search(r"((?:version \d+\.\d+|hostname\s+\S+).*?\nend)", text, re.DOTALL)
        if m:
            clean_cfg = m.group(1).strip() + "\n"
            return clean_cfg, None

        if attempt < max_retries:
            time.sleep(2)

    return None, "Could not locate clean config delimiters in output"


def main():
    args = sys.argv[1:]
    if "-h" in args or "--help" in args:
        print_help()

    destroy_after = "--destroy-after" in args
    explicit_topo = next((a for a in args if not a.startswith("-")), None)

    topo_file = find_topology_file(explicit_topo)
    topo_dir = topo_file.parent

    print(f"[*] Target topology: {topo_file}")

    # Parse topology
    data, yaml_parser = parse_topology(topo_file)
    lab_name = data.get("name", "ccna")
    nodes_spec = data.get("topology", {}).get("nodes", {})

    print(f"[*] Lab name: {lab_name}")
    print(f"[*] Total nodes defined in topology: {len(nodes_spec)}")

    # Ensure lab is active (deploys it if stopped to load NVRAM into devices)
    running_containers, started_by_script = ensure_lab_running(topo_file, lab_name)

    # Filter for network devices (Cisco IOL, IOS-XE, cEOS, etc.)
    target_nodes = {}
    for node_name, spec in nodes_spec.items():
        kind = spec.get("kind", "")
        if any(brand in kind for brand in ("cisco", "ceos", "juniper")):
            if node_name in running_containers:
                target_nodes[node_name] = (spec, running_containers[node_name]["ip"])

    if not target_nodes:
        print("[-] No network operating system nodes found to extract configs from.")
        sys.exit(1)

    # If the lab was just deployed, wait for nodes to finish booting and open SSH
    if started_by_script:
        print("[*] Waiting for Cisco nodes to finish booting and open SSH...")
        for node_name, (_, ip) in target_nodes.items():
            print(f"    Checking {node_name} ({ip})...", end="", flush=True)
            if wait_for_node_ssh(ip, timeout=50):
                print(" [READY]")
            else:
                print(" [TIMEOUT]")
        # Give IOL a moment to finish internal CLI initialization
        time.sleep(3)

    # Prepare configs directory
    configs_dir = topo_dir / "configs"
    configs_dir.mkdir(parents=True, exist_ok=True)

    saved_nodes = []

    # Extract configs
    for node_name, (spec, ip) in target_nodes.items():
        print(f"[*] Extracting config from '{node_name}' ({ip})...", end="", flush=True)

        cfg_text, err = ssh_extract_config(ip, username="admin", password="admin")
        if cfg_text:
            cfg_path = configs_dir / f"{node_name}.cfg"
            with open(cfg_path, "w", encoding="utf-8") as f:
                f.write(cfg_text)
            print(f" [OK] -> saved to configs/{node_name}.cfg ({len(cfg_text.splitlines())} lines)")

            spec["startup-config"] = f"configs/{node_name}.cfg"
            saved_nodes.append(node_name)
        else:
            print(f" [FAIL] ({err})")

    if not saved_nodes:
        print("[-] No configurations were successfully extracted.")
        sys.exit(1)

    # Update topology YAML file
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

    # Destroy lab if requested
    if started_by_script and destroy_after:
        print(f"[*] Destroying lab as requested (--destroy-after)...")
        subprocess.run(["containerlab", "destroy", "-t", str(topo_file), "--cleanup"], cwd=topo_dir)
    elif started_by_script:
        print(f"[i] Lab remains running. To stop it later, run:")
        print(f"    containerlab destroy -t {topo_file.name} --cleanup")

    print("\n[+] Done! You can now commit your persistent changes to Git:")
    print("    git add .")
    print('    git commit -m "feat(configs): save dynamic CLI configurations"')


if __name__ == "__main__":
    main()
