# Ghost EDR

**Real-time container security for macOS.** Detects and responds to threats in Docker containers where traditional EDR tools are blind due to virtualization barriers.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

## Why Ghost EDR?

On macOS, Docker containers run inside a Linux VM (Docker Desktop or OrbStack). Host-based EDR tools cannot see inside this VM, creating a significant security blind spot. Ghost EDR solves this by deploying a monitoring agent *inside* the VM that watches container activity and reports threats to the host.

## Architecture

Ghost EDR uses a **Sidecar Mole** architecture:

| Component | Location | Role |
|-----------|----------|------|
| **The Mole** | Linux VM | Falco-based eBPF monitor that watches syscalls from sibling containers |
| **The Enforcer** | Host or Container | Policy engine that receives alerts and executes responses |

```
┌─────────────────────────────────────────────────────────────────────┐
│  Linux VM (Docker Desktop / OrbStack)                               │
│  ┌────────────────┐  ┌──────────────┐  ┌──────────────┐            │
│  │   The Mole     │  │ Container A  │  │ Container B  │   ...      │
│  │   (Falco)      │  │              │  │              │            │
│  │  eBPF monitor  │  │   your app   │  │   your app   │            │
│  └───────┬────────┘  └──────────────┘  └──────────────┘            │
│          │                                                          │
│          │ HTTP POST (JSON alerts)                                  │
└──────────┼──────────────────────────────────────────────────────────┘
           ▼
┌─────────────────────────────────────────────────────────────────────┐
│  The Enforcer (container or native)                                 │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │  Policy Engine                                                  │ │
│  │  • Match rules by pattern, priority, container                  │ │
│  │  • Execute actions: alert, kill, quarantine, webhook            │ │
│  │  • Rate limiting and cooldowns                                  │ │
│  └────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

## Requirements

- macOS (Apple Silicon or Intel)
- Docker Desktop or OrbStack
- Python 3.10+ (only if running Enforcer natively)

## Quick Start

### Option 1: Docker Compose (Recommended)

The simplest way to run Ghost EDR with both components containerized:

```bash
cd mole
docker compose up -d
```

This starts:
- **ghost-mole**: Falco container monitoring syscalls via eBPF
- **ghost-enforcer**: Policy engine receiving alerts on port 8766

> **Note:** On macOS, Falco's eBPF driver may not work inside Docker. See [Troubleshooting](#troubleshooting) for the OrbStack VM solution.

### Verify It's Working

```bash
# Check health
curl http://localhost:8766/health

# Expected output:
# {"status": "healthy", "runtime": "docker_desktop", "policies": 5}
```

### Test Detection

Trigger a reverse shell detection:

```bash
docker run --rm alpine sh -c 'apk add -q nmap-ncat && ncat -e /bin/sh localhost 4444'
```

Check the Enforcer logs:

```bash
docker logs ghost-enforcer --tail 20
```

You should see:
```
Alert received    rule='Ghost EDR - Netcat Reverse Shell'  priority=CRITICAL
Executing policy action    action=kill    policy=critical-threats-kill
```

## Detection Rules

Ghost EDR includes 15+ high-fidelity detection rules:

### Critical Threats (Default: Kill)

| Rule | Description | MITRE ATT&CK |
|------|-------------|--------------|
| Reverse Shell Detected | STDIN/STDOUT redirected to network socket | T1059 |
| Netcat Reverse Shell | Netcat with `-e` flag for shell execution | T1059 |
| Crypto Miner Binary | Known mining binaries (xmrig, cpuminer, etc.) | T1496 |
| Stratum Protocol | Mining protocol communication detected | T1496 |
| Container Escape (release_agent) | Cgroup escape via release_agent | T1611 |
| Nsenter Execution | Namespace manipulation tool | T1611 |
| Kernel Module Load | insmod/modprobe from container | T1611 |
| Download and Execute | curl/wget piped to shell | T1105 |
| Process Injection (ptrace) | PTRACE_ATTACH to other process | T1055 |

### High Priority Threats (Default: Quarantine)

| Rule | Description | MITRE ATT&CK |
|------|-------------|--------------|
| Mining Pool Connection | Connections to common mining ports | T1496 |
| Mount in Privileged Container | Mount command in privileged mode | T1611 |
| Docker Socket Access | Container accessing Docker socket | T1611 |
| Sensitive File Read | Access to /etc/shadow, SSH keys, credentials | T1552 |

### Suspicious Activity (Default: Alert)

| Rule | Description | MITRE ATT&CK |
|------|-------------|--------------|
| Package Manager Usage | apt/yum/npm/pip in running container | T1059 |
| Bash History Deletion | Clearing command history | T1070 |
| Hidden File Created | Dotfiles in /tmp, /dev/shm, /var/tmp | T1564 |

## Configuration

Configuration file: `config/ghost-edr.yaml`

```yaml
# Logging level
log_level: info

# Dry run mode - log actions but don't execute
dry_run: false

# Receiver configuration
receiver:
  type: http
  host: "0.0.0.0"
  port: 8766

# Containers to never take action on
excluded_containers:
  - "ghost-mole"
  - "ghost-mole-*"

# Policy rules (evaluated in order, first match wins)
policies:
  # Critical threats - immediate termination
  - name: critical-threats-kill
    description: Kill containers for critical security threats
    priority_min: critical
    rule_patterns:
      - "Ghost EDR - Reverse Shell*"
      - "Ghost EDR - Crypto Miner*"
      - "Ghost EDR - Container Escape*"
      - "Ghost EDR - Netcat Reverse Shell*"
    action: kill
    cooldown_seconds: 0

  # High priority - network isolation
  - name: high-threats-quarantine
    description: Quarantine containers for high priority threats
    priority_min: error
    rule_patterns:
      - "Ghost EDR - Mining Pool Connection*"
      - "Ghost EDR - Docker Socket Access*"
    action: quarantine
    cooldown_seconds: 30

  # Development containers - alert only
  - name: dev-containers-alert-only
    container_patterns:
      - "*-dev"
      - "*-test"
    action: alert

  # Default catch-all
  - name: default-alert
    priority_min: warning
    action: alert
    cooldown_seconds: 120
```

### Policy Actions

| Action | Description |
|--------|-------------|
| `alert` | Log the event (no enforcement) |
| `kill` | Terminate the container immediately (SIGKILL) |
| `quarantine` | Disconnect container from all networks |
| `webhook` | POST alert JSON to external URL |

### Enabling Kill/Quarantine

By default, the Enforcer runs with read-only Docker socket access (alert-only mode). To enable enforcement actions, modify `docker-compose.yml`:

```yaml
enforcer:
  # Change from read-only to read-write
  user: root
  volumes:
    - /var/run/docker.sock:/var/run/docker.sock  # Remove :ro
```

## CLI Reference

The `ghost-enforcer` CLI runs inside the container. Use `docker exec` to run commands:

```bash
# Check runtime detection
docker exec ghost-enforcer ghost-enforcer detect-runtime

# Validate configuration
docker exec ghost-enforcer ghost-enforcer validate-config --config /app/config.yaml
```

View logs and status:

```bash
# Follow enforcer logs
docker logs -f ghost-enforcer

# Check container status
docker compose ps
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/falco` | POST | Receive Falco alerts (JSON) |
| `/health` | GET | Health check with runtime info |
| `/metrics` | GET | Prometheus-format metrics |

## Performance

Ghost EDR uses eBPF for syscall monitoring with minimal overhead.

### Benchmark Results

Tested on macOS with OrbStack, Falco 0.39.2 (modern_ebpf):

| Workload | With Falco | Without | Overhead |
|----------|------------|---------|----------|
| **CPU-bound** ||||
| Compression (100MB) | 1,887ms | 1,864ms | +1.2% |
| SHA256 hash (10x100MB) | 2,948ms | 2,915ms | +1.1% |
| **I/O-bound** ||||
| Create 5,000 files | 63ms | 53ms | +19.6% |
| Read 5,000 files | 698ms | 612ms | +14.1% |
| Sequential write 200MB | 194ms | 206ms | -6.0% |
| **Mixed** ||||
| Python compile (500 files) | 144ms | 139ms | +3.6% |
| Tar extract (5k files) | 79ms | 67ms | +17.3% |
| **Overall** | **6,073ms** | **5,915ms** | **+2.7%** |

**Summary:**
- CPU-bound tasks: ~1% overhead
- Large sequential I/O: negligible
- Many small files: 15-20% overhead (syscall-heavy)
- Typical development workloads: 3-5% overhead

## Project Structure

```
ghost-edr/
├── mole/                          # The Mole (Falco + Enforcer containers)
│   ├── docker-compose.yml         # Container orchestration
│   ├── config/
│   │   ├── falco.yaml             # Falco configuration
│   │   └── rules/
│   │       └── ghost_rules.yaml   # Detection rules
│   └── benchmark.sh               # Performance benchmark
├── enforcer/                      # The Enforcer (Python)
│   ├── Dockerfile                 # Hardened container image
│   ├── pyproject.toml
│   └── src/ghost_enforcer/
│       ├── cli.py                 # CLI commands
│       ├── daemon.py              # HTTP server
│       ├── config.py              # Configuration models
│       ├── policy_engine.py       # Alert processing
│       ├── actions/               # Response actions
│       │   ├── alert.py
│       │   ├── kill.py
│       │   ├── quarantine.py
│       │   └── webhook.py
│       └── runtime/               # Container runtime detection
│           ├── docker_desktop.py
│           └── orbstack.py
├── config/
│   └── ghost-edr.yaml             # Main configuration
└── README.md
```

## Troubleshooting

### Falco fails to start on macOS

Falco's eBPF driver requires direct kernel access. Inside Docker on macOS, this may fail with:

```
An error occurred in an event source, forcing termination
```

**Solution: Run Falco in an OrbStack Linux VM**

```bash
# Create a Linux VM
orb create ubuntu ghost-edr-vm

# Install Falco
orb -m ghost-edr-vm bash -c '
  curl -fsSL https://falco.org/repo/falcosecurity-packages.asc | \
    sudo gpg --dearmor -o /usr/share/keyrings/falco-archive-keyring.gpg
  echo "deb [signed-by=/usr/share/keyrings/falco-archive-keyring.gpg] \
    https://download.falco.org/packages/deb stable main" | \
    sudo tee /etc/apt/sources.list.d/falcosecurity.list
  sudo apt-get update && sudo apt-get install -y falco
'

# Copy Ghost EDR rules
cat mole/config/rules/ghost_rules.yaml | \
  orb -m ghost-edr-vm sudo tee /etc/falco/rules.d/ghost_rules.yaml

# Configure HTTP output
orb -m ghost-edr-vm bash -c 'cat << EOF | sudo tee /etc/falco/config.d/ghost-http.yaml
http_output:
  enabled: true
  url: "http://host.internal:8766/falco"
json_output: true
json_include_output_property: true
EOF'

# Start Falco
orb -m ghost-edr-vm sudo systemctl start falco-modern-bpf.service
```

### Enforcer can't connect to Docker

```bash
# Check Docker socket permissions
ls -la /var/run/docker.sock

# Verify Enforcer can reach Docker
docker exec ghost-enforcer wget -qO- --spider http://localhost:8766/health
```

### No alerts received

1. Verify Falco is running:
   ```bash
   docker compose ps
   docker logs ghost-mole
   ```

2. Check Falco HTTP output is configured:
   ```bash
   docker exec ghost-mole cat /etc/falco/falco.yaml | grep http_output
   ```

3. Test the Enforcer endpoint directly:
   ```bash
   curl -X POST http://localhost:8766/falco \
     -H "Content-Type: application/json" \
     -d '{"rule": "Test", "priority": "Warning", "output_fields": {}}'
   ```

### Kill action fails with "Permission denied"

The Enforcer needs write access to the Docker socket. Modify `docker-compose.yml` to grant write access (see [Enabling Kill/Quarantine](#enablingkillquarantine)).

## Security Considerations

The Enforcer container is hardened with:

- **Non-root user** (`ghost:1000`)
- **Read-only filesystem**
- **No new privileges** (`no-new-privileges:true`)
- **All capabilities dropped** (`cap_drop: ALL`)
- **Resource limits** (256MB memory, 0.5 CPU)
- **Minimal base image** (Alpine)

The Mole (Falco) requires privileged access to monitor syscalls, which is an inherent requirement for eBPF-based monitoring.

## License

MIT
