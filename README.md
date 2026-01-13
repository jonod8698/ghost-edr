# Ghost EDR

Real-time container runtime security for macOS. Detects and responds to threats in Docker containers where host-based EDR tools are blind due to virtualization barriers.

## Architecture

Ghost EDR uses a "Sidecar Mole" architecture with two components:

- **The Mole** (Guest Side): A privileged Falco container running inside the Linux VM that monitors syscalls from sibling containers using eBPF.
- **The Enforcer** (Host Side): A Python daemon running natively on macOS that receives alerts and executes policy responses (kill, quarantine, alert).

```
┌──────────────────────────────────────────────────────────────────┐
│  Linux VM (Docker Desktop / OrbStack)                            │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │  The Mole (Falco)  │  Container A  │  Container B  │  ...   │ │
│  │  - eBPF monitoring │               │               │        │ │
│  └────────┬────────────────────────────────────────────────────┘ │
│           │ HTTP (JSON alerts)                                   │
└───────────┼──────────────────────────────────────────────────────┘
            ▼
┌──────────────────────────────────────────────────────────────────┐
│  macOS Host                                                       │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │  The Enforcer                                                │ │
│  │  - Policy engine → kill / quarantine / alert                 │ │
│  └─────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

## Requirements

- macOS (Apple Silicon or Intel)
- Docker Desktop or OrbStack
- Python 3.10+

## Quick Start

### 1. Install

```bash
./scripts/install.sh
```

### 2. Start Ghost EDR

```bash
./scripts/start.sh
```

Or manually:

```bash
# Start The Mole (Falco container)
cd mole && docker compose up -d

# Start The Enforcer (in another terminal)
ghost-enforcer run --config ~/.config/ghost-edr/config.yaml
```

### 3. Test Detection

```bash
# Trigger a reverse shell detection (uses ncat which supports -e flag)
docker run --rm alpine sh -c 'apk add -q nmap-ncat && ncat -e /bin/sh localhost 4444'

# Trigger a crypto miner detection
docker run --rm alpine sh -c 'echo xmrig'
```

## Detection Rules

Ghost EDR includes detection rules for:

| Threat | Priority | Response |
|--------|----------|----------|
| Reverse shells | CRITICAL | Kill |
| Crypto miners | CRITICAL | Kill |
| Container escape attempts | CRITICAL | Kill |
| Mining pool connections | HIGH | Quarantine |
| Shell from web process | HIGH | Quarantine |
| Docker socket access | HIGH | Quarantine |
| Package manager usage | WARNING | Alert |
| Sensitive file access | HIGH | Alert |

## Configuration

Edit `~/.config/ghost-edr/config.yaml`:

```yaml
# Dry run mode (log only, no actions)
dry_run: false

# Policies define what action to take for matching alerts
policies:
  - name: critical-threats-kill
    priority_min: critical
    rule_patterns:
      - "Ghost EDR - Reverse Shell*"
      - "Ghost EDR - Crypto Miner*"
    action: kill
    cooldown_seconds: 0

  - name: suspicious-activity-alert
    priority_min: warning
    action: alert
    cooldown_seconds: 60
```

### Policy Actions

- `alert` - Log the alert (no enforcement)
- `kill` - Terminate the container immediately
- `quarantine` - Disconnect container from all networks
- `webhook` - POST alert to external URL

## CLI Usage

```bash
# Start with default config
ghost-enforcer run

# Start with custom config
ghost-enforcer run --config /path/to/config.yaml

# Dry run mode (no actions)
ghost-enforcer run --dry-run

# Detect runtime
ghost-enforcer detect-runtime

# Validate config
ghost-enforcer validate-config --config /path/to/config.yaml
```

## Endpoints

The Enforcer exposes:

- `POST /falco` - Receives Falco alerts
- `GET /health` - Health check
- `GET /metrics` - Prometheus-style metrics

## Performance Impact

Ghost EDR uses eBPF for syscall monitoring, which has minimal overhead on container workloads.

### Benchmark Results

Tested on macOS with OrbStack 2.0.5, Falco 0.42.1 (modern_ebpf driver):

| Workload Type | With Falco | Without | Overhead |
|---------------|------------|---------|----------|
| **CPU-Heavy** | | | |
| Compression (100MB gzip) | 1,887ms | 1,864ms | +1.2% |
| SHA256 hashing (10×100MB) | 2,948ms | 2,915ms | +1.1% |
| **I/O-Heavy** | | | |
| Create 5,000 files | 63ms | 53ms | +19.6% |
| Read 5,000 files | 698ms | 612ms | +14.1% |
| Write 200MB sequential | 194ms | 206ms | -6.0% |
| Read 200MB sequential | 13ms | 14ms | -9.3% |
| **Mixed** | | | |
| Python compile (500 files) | 144ms | 139ms | +3.6% |
| Tar extract (5k files) | 79ms | 67ms | +17.3% |
| **Overall** | **6,073ms** | **5,915ms** | **+2.7%** |

### Key Findings

- **CPU-bound tasks**: Minimal impact (+1.2%)
- **Large sequential I/O**: No measurable impact
- **Many small files**: Highest overhead (+15-20%) due to per-syscall monitoring
- **Typical npm/pip installs**: ~3-5% overhead

### Running Benchmarks

Run the included benchmark script to measure performance on your system:

```bash
# Start Falco monitoring
orb -m ghost-edr-vm sudo systemctl start falco-modern-bpf.service

# Run benchmark WITH Falco
docker run --rm -v $(pwd)/mole/benchmark.sh:/benchmark.sh:ro \
  python:3.11-alpine sh /benchmark.sh

# Stop Falco and run again to compare
orb -m ghost-edr-vm sudo systemctl stop falco-modern-bpf.service
docker run --rm -v $(pwd)/mole/benchmark.sh:/benchmark.sh:ro \
  python:3.11-alpine sh /benchmark.sh
```

### Reducing Overhead

For build-heavy workloads, you can exclude trusted containers:

```yaml
# In ~/.config/ghost-edr/config.yaml
excluded_containers:
  - "build-*"
  - "*-ci"
  - "npm-*"
```

Or reduce the monitored syscall scope in Falco:

```yaml
# In mole/config/falco.yaml
base_syscalls:
  custom_set: [execve, execveat, connect, ptrace]  # Critical only
```

## Project Structure

```
ghost-edr/
├── mole/                   # The Mole (Falco container)
│   ├── docker-compose.yml
│   ├── benchmark.sh        # Performance benchmark script
│   └── config/
│       ├── falco.yaml
│       └── rules/
│           └── ghost_rules.yaml
├── enforcer/               # The Enforcer (Python daemon)
│   └── src/ghost_enforcer/
├── config/                 # Configuration templates
├── scripts/                # Helper scripts
└── README.md
```

## Troubleshooting

### The Mole won't start

Check Docker/OrbStack is running:
```bash
docker ps
```

Check Falco logs:
```bash
cd mole && docker compose logs -f
```

### OrbStack: Falco fails with "scap_init" error

Falco's modern_ebpf driver doesn't work inside Docker containers on OrbStack. Instead, run Falco in an OrbStack Linux VM:

```bash
# Create an OrbStack Linux VM
orb create ubuntu ghost-edr-vm

# Install Falco in the VM
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

# Configure HTTP output to Enforcer (use port 8766 to avoid OrbStack conflict)
orb -m ghost-edr-vm bash -c 'cat << EOF | sudo tee /etc/falco/config.d/ghost-http.yaml
http_output:
  enabled: true
  url: "http://host.internal:8766/falco"
json_output: true
json_include_output_property: true
EOF'

# Start Falco
orb -m ghost-edr-vm sudo systemctl restart falco-modern-bpf.service
```

Note: OrbStack uses port 8765 internally, so run the Enforcer on port 8766:
```bash
ghost-enforcer run --port 8766
```

### The Enforcer can't connect

Verify the receiver is listening:
```bash
curl http://localhost:8765/health
```

### No alerts received

1. Verify Falco is running: `docker compose ps`
2. Check Falco can reach the Enforcer: The Mole uses `host.docker.internal:8765`
3. Generate a test event and check Falco logs

## License

MIT
