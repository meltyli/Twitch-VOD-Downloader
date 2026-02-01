# Twitch VOD Downloader

A Python CLI tool that monitors Twitch streamers and automatically records their live streams with integrated H.265 compression.

## 📚 [**View Full Documentation & User Guide on the Wiki**](https://github.com/meltyli/Twitch-VOD-Downloader/wiki)

## Features

- Monitor and record up to 5 concurrent Twitch streams
- Add and manage a list of monitored streamers
- Integrated H.265/HEVC compression with quality control
- Rich progress UI with file size tracking
- Automatic stream detection and recording
- Configurable output directories and compression settings
- Interactive menu-driven interface

## Prerequisites

- **Docker** and **Docker Compose** installed ([Get Docker](https://docs.docker.com/get-docker/))
- For complete installation guide, see the [**Quick Start Guide**](https://github.com/meltyli/Twitch-VOD-Downloader/wiki/Quick-Start-Guide)

## Running (Docker)

This application is designed to run in Docker and supports **full interactive menus** in containers.

### Initial Setup

1. **Build and start the container**:

```bash
docker compose up --build
```

The container starts with `stdin_open: true` and `tty: true` enabled, allowing full interactive menu navigation.

2. **First-run setup prompt**:

You'll see: `First-time setup: run in headless mode (no interactive menu)? [y/N]:`

- Press **Enter** or type `n` for **interactive menu mode** (recommended) — navigate menus to add streamers, start monitoring, compress recordings
- Type `y` for **headless mode** — automatically monitors all configured streamers on startup (no menus)

Your choice is saved to `config.json`.

### Interactive Menu Usage

If you chose interactive mode, you'll see the main menu:

```
╔════════════════════════════════════╗
║      Twitch Stream Recorder        ║
╚════════════════════════════════════╝

1. Manage Streamers
2. Start Monitoring
3. Compress Recordings to MP4 (H.265)
4. Settings
q. Exit
```

Navigate by typing option numbers. The menu runs inside the Docker container with full TTY support.

**Detaching without stopping**: Press `Ctrl-P` then `Ctrl-Q` to detach and leave the container running.

### Running in Background (Detached)

For production/unattended use:

```bash
# Start detached
docker compose up -d

# Attach to interact with menus
docker compose attach server

# View logs
docker compose logs -f server

# Stop
docker compose down
```

### Managing the Container

```bash
# Restart container
docker compose restart server

# Execute commands inside running container
docker compose exec server python3 -m src.compression recordings

# Open shell inside container
docker compose exec server /bin/bash
```

## Alternative: Local Development (Without Docker)

For development without Docker:

```bash
python3 -m venv pyenv
source pyenv/bin/activate
pip install -r requirements.txt
python3 -m src.twitch_recorder
```

## Logs

The application logs to:
- **Container stdout**: View with `docker compose logs -f server`
- **Rotating log file**: `/logs/log` inside container, mounted to `./logs/log` on host

```bash
# View log file from host
tail -f ./logs/log
```

## Configuration
- Edit `config.json` to set defaults. New network settings available:
	- `stream_check_timeout`: seconds to wait for `streamlink` (default 10)
	- `stream_check_retries`: number of retries on failure (default 2)
	- `stream_check_backoff`: base seconds for exponential backoff between retries (default 5)

## Roadmap

### Feature Roadmap

- Low disk space monitoring and warnings
- Retry logic for failed stream checks
- Enhanced notification system for stream status changes
- Configuration profiles for different quality presets

## Contributing & Feedback

Found a bug or have a feature request? Please help improve this project!

**Create an Issue on GitHub:**
- **Bug Reports**: Provide detailed information including steps to reproduce, error messages, and your environment (OS, Python version, Streamlink version)
- **Feature Requests**: Describe the feature you'd like to see and how it would improve the tool
- **Suggestions**: Share your ideas for improvements or enhancements

[**→ Create an Issue**](https://github.com/meltyli/twitch-vod-downloader/issues)

Detailed issue reports help identify and fix problems quickly, and well-described feature requests help prioritize development efforts.
