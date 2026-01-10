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
# Trigger a reverse shell detection
docker run --rm alpine sh -c 'nc -e /bin/sh localhost 4444'

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

## Project Structure

```
ghost-edr/
├── mole/                   # The Mole (Falco container)
│   ├── docker-compose.yml
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
