# cronwatch

Lightweight daemon that monitors cron job execution and sends alerts on failures or missed runs.

## Installation

```bash
pip install cronwatch
```

## Usage

Add jobs to your `cronwatch.yaml` config file:

```yaml
jobs:
  backup-db:
    schedule: "0 2 * * *"
    command: "/usr/local/bin/backup.sh"
    alert_email: "ops@example.com"
    timeout: 300

  sync-files:
    schedule: "*/15 * * * *"
    command: "/usr/local/bin/sync.sh"
    alert_email: "ops@example.com"
```

Start the daemon:

```bash
cronwatch start --config cronwatch.yaml
```

Check status of monitored jobs:

```bash
cronwatch status
```

cronwatch will send an alert if a job exits with a non-zero status code or fails to run within its expected schedule window.

## Configuration

| Field | Description |
|-------|-------------|
| `schedule` | Cron expression for expected run frequency |
| `command` | Command to monitor |
| `alert_email` | Email address to notify on failure |
| `timeout` | Max allowed runtime in seconds |

## License

MIT