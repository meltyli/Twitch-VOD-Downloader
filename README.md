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

- Python 3.6+
- Streamlink (≥5.0.0)
- ffmpeg and ffprobe (for compression)

## Quick Start

```bash
# Clone and setup
git clone https://github.com/meltyli/twitch-vod-downloader.git
cd twitch-vod-downloader

# Create virtual environment and install dependencies
python3 -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate
pip install -r requirements.txt

# Install ffmpeg (macOS example)
brew install ffmpeg

# Run the application
./launch.sh  # macOS/Linux
# or: python3 -m src.twitch_recorder
```

For detailed setup instructions, usage guides, configuration options, and troubleshooting, please visit the [**Wiki**](https://github.com/meltyli/Twitch-VOD-Downloader/wiki).

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
