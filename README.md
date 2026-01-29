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

## Setup

For complete installation and setup instructions, see the [**Quick Start Guide**](https://github.com/meltyli/Twitch-VOD-Downloader/wiki/Quick-Start-Guide) on the Wiki.

## Running

Docker (recommended):

1. Build and start in the background:

```bash
docker compose up --build -d
```

2. **First-run setup**: Attach to the container to answer the interactive prompt:

```bash
docker compose attach server
```

You'll be prompted: `First-time setup: run in headless mode (no interactive menu)? [y/N]:`
- Type `y` for headless mode (auto-monitors all configured streamers on startup)
- Type `n` or press Enter for interactive menu mode

After answering, your choice is saved to `config.json`. 

To detach without stopping the container: press `Ctrl-P` then `Ctrl-Q`

3. Follow container stdout (also shows logs written to the host-mounted log file):

```bash
docker compose logs -f server
```

4. View the application log file written by the container (host path):

```bash
tail -f ./logs/log
```

Stop and remove containers:

```bash
docker compose down
```

Local development (without Docker):

```bash
# create and activate venv (macOS/Linux)
python3 -m venv pyenv
source pyenv/bin/activate
pip install -r requirements.txt
python3 -m src.twitch_recorder
```

Logs
- The app logs to both stdout and a rotating file at `/logs/log` inside the container. The compose setup mounts `./logs` on the host to `/logs` in the container so you can inspect logs with `tail -f ./logs/log`.

Configuration
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
