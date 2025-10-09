# Twitch VOD Downloader

A Python CLI tool that monitors Twitch streamers and automatically records their live streams with integrated H.265 compression.

## Features

- Monitor and record up to 5 concurrent Twitch streams
- Add and manage a list of monitored streamers
- Integrated H.265/HEVC compression with quality control
- Rich progress UI with file size tracking
- Automatic stream detection and recording
- Configurable output directories and compression settings
- Interactive menu-driven interface

## Prerequisites

- Python 3.6+
- Streamlink (≥5.0.0)
- ffmpeg and ffprobe (for compression)

## Quick Start

### 1. Clone and Setup

```bash
git clone https://github.com/meltyli/twitch-vod-downloader.git
cd twitch-vod-downloader

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Verify installation
streamlink --version
```

### 2. Install ffmpeg

```bash
# macOS
brew install ffmpeg

# Linux (Ubuntu/Debian)
sudo apt-get update && sudo apt-get install ffmpeg

# Windows
# Download from ffmpeg.org and add to PATH
```

### 3. Run the Application

```bash
./launch.sh  # macOS/Linux (recommended)
# or
python3 -m src.twitch_recorder
```

## Usage

### Main Menu Options

1. **Manage Streamers** - Add/remove streamers from your monitoring list
2. **Start Monitoring** - Monitor up to 5 streamers concurrently
3. **Compress Recordings to MP4 (H.265)** - Convert .ts files with quality control
4. **Settings** - Configure directories, check intervals, and compression defaults
q. **Exit**

### Monitoring Workflow

The application offers two monitoring modes:

1. **Immediate Check**: Detects currently live streamers and lets you select which to record
2. **Continuous Monitoring**: Select up to 5 streamers to monitor - automatically records when they go live and resumes monitoring after streams end

### Stopping Recordings

- Press `q` then `Enter` to stop individual recordings
- Use `Ctrl+C` to interrupt the application

### Compression

Two ways to compress recordings:

**Option 1: In-App Compression (Recommended)**
- Main menu → Option 3
- Select specific files or all .ts files
- Configure CRF (quality: 0-51, lower = better, default: 28) and preset (speed)
- Optional: Save settings as new defaults
- Optional: Auto-delete originals after compression

**Option 2: Standalone Script**
```bash
python3 -m src.remux_ts_to_mp4
```

## Configuration

Settings are stored in `config.json`:

```json
{
  "streamers": ["username1", "username2"],
  "output_directory": "recordings",
  "compressed_directory": "recordings/compressed",
  "default_check_interval": 2,
  "default_crf": 28,
  "default_preset": "medium"
}
```

All settings can be modified through the Settings menu (Option 4).

### File Naming

- **Recordings**: `{output_directory}/{streamer}_{YYYYMMDD_HHMMSS}.ts`
- **Compressed**: `{compressed_directory}/{streamer}_{YYYYMMDD_HHMMSS}.mp4`

## Compression Details

### H.265/HEVC Encoding

The compression tool uses H.265 encoding for efficient file sizes while maintaining quality:

- **CRF (Constant Rate Factor)**: 0-51 scale (lower = better quality, default: 28)
- **Presets**: ultrafast, superfast, veryfast, faster, fast, medium (default), slow, slower, veryslow
- **Verification**: Automatically verifies output integrity using ffprobe
- **Interrupt Handling**: Gracefully handles Ctrl+C with automatic cleanup

### Compression Process

1. Scans for .ts files in recordings directory
2. Checks if valid .mp4 already exists (skips if found)
3. Compresses with configured CRF and preset
4. Verifies output integrity (size, duration, codecs)
5. Optionally deletes originals after user confirmation

## Troubleshooting

**Streamlink not found**: Ensure virtual environment is activated and dependencies are installed
```bash
source venv/bin/activate  # or myenv/bin/activate
pip install -r requirements.txt
```

**ffmpeg not found**: Verify installation with `ffmpeg -version`

**Compression fails**: Check that ffmpeg and ffprobe are properly installed and in PATH

**Permission errors**: Ensure write permissions in the project directory

## Limitations

- Maximum of 5 concurrent stream recordings
- Manual selection required - fully automatic recording not supported
- No retry logic for failed stream checks

## Roadmap

### Feature Roadmap

- Low disk space monitoring and warnings
- Retry logic for failed stream checks
- Enhanced notification system for stream status changes
- Configuration profiles for different quality presets

## Contributing & Feedback

Found a bug or have a feature request? Please help improve this project!

**Create an Issue on GitHub:**
- 🐛 **Bug Reports**: Provide detailed information including steps to reproduce, error messages, and your environment (OS, Python version, Streamlink version)
- ✨ **Feature Requests**: Describe the feature you'd like to see and how it would improve the tool
- 💡 **Suggestions**: Share your ideas for improvements or enhancements

[**→ Create an Issue**](https://github.com/meltyli/twitch-vod-downloader/issues)

Detailed issue reports help identify and fix problems quickly, and well-described feature requests help prioritize development efforts.

## License

This project is licensed under the GNU General Public License v3.0 - see the LICENSE file for details.
