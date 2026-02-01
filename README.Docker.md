## Docker Usage Guide

This application is **Docker-first** and supports full **interactive menus** inside containers via TTY.

### Interactive Mode (Default)

The compose file includes `stdin_open: true` and `tty: true`, enabling full menu navigation.

#### First Run

```bash
docker compose up --build
```

You'll see a first-time setup prompt:
```
First-time setup: run in headless mode (no interactive menu)? [y/N]:
```

- Press **Enter** (or type `n`) for interactive menus
- Type `y` for headless auto-monitoring

Your choice saves to `config.json`.

#### Using the Interactive Menu

After setup, navigate the main menu:
```
1. Manage Streamers
2. Start Monitoring
3. Compress Recordings to MP4 (H.265)
4. Settings
q. Exit
```

Type option numbers to navigate. All prompts work normally inside the Docker container.

**To detach without stopping**: Press `Ctrl-P` then `Ctrl-Q`

#### Background Mode

Start detached, then attach when needed:

```bash
# Start in background
docker compose up -d

# Attach to interact
docker compose attach server

# View logs
docker compose logs -f server

# Stop
docker compose down
```

### Running One-Off Commands

Execute commands inside the running container:

```bash
# Run compression utility
docker compose exec server python3 -m src.compression recordings

# Open shell
docker compose exec server /bin/bash

# Run recorder directly (bypasses launch.sh)
docker compose exec server python3 -m src.twitch_recorder
```

### Multiple Instances (Advanced)

To run multiple independent instances on one host:

```bash
# Start second instance with different project name
docker compose -p recorder2 up -d

# Important: Edit compose.yaml first to change:
# - Port mapping (8001 → 8002)
# - Volume paths (./recordings → ./recordings2, etc.)
```

**Avoid running the same project twice** — port and volume conflicts will occur.

### Deploying to Production

Build for specific platforms:

```bash
# For amd64 cloud servers (from Mac M1/M2)
docker build --platform=linux/amd64 -t twitch-vod-downloader .

# Push to registry
docker tag twitch-vod-downloader myregistry.com/twitch-vod-downloader
docker push myregistry.com/twitch-vod-downloader
```

For headless deployment, ensure `config.json` has `"headless": true` or answer `y` during first-run setup.

### Architecture Details

- **Base image**: `python:3.13.3-slim`
- **Entrypoint**: `./launch.sh` → `python3 -m src.twitch_recorder`
- **Exposed port**: 8001 (configurable in compose.yaml)
- **User**: Non-root `appuser` (UID 10001)
- **Volumes**: 
  - `./recordings` → `/app/recordings`
  - `./logs` → `/logs`
  - `./config.json` → `/app/config.json`

### References
* [Docker Compose Specification](https://docs.docker.com/compose/compose-file/)
* [Docker's Python Guide](https://docs.docker.com/language/python/)
* [Interactive Containers with TTY](https://docs.docker.com/engine/reference/run/#foreground)