# Twitch VOD Downloader

A Python script that automatically monitors when a Twitch streamer goes live and downloads their stream for later viewing.

## Features

- Automatically detects when a streamer goes live
- Records streams in high quality
- Saves recordings with timestamps for easy organization
- Handles stream interruptions gracefully
- Simple command-line interface

## Requirements

- Python 3.6+
- Streamlink

## Installation

1. Clone this repository:
```
git clone https://github.com/yourusername/twitch-vod-downloader.git
cd twitch-vod-downloader
```

2. Install the required dependencies:
```
pip install -r requirements.txt
```

3. Ensure Streamlink is properly installed:
```
streamlink --version
```

## Usage

1. Navigate to the project directory:
```
cd twitch-vod-downloader
```

2. Run the script:
```
python -m src.twitch_recorder
```

3. When prompted, enter the Twitch username of the streamer you want to monitor.

4. Recordings will be saved in the `recordings/` directory.

## Configuration

You can modify the following parameters in the script:
- Check interval (default: 5 minutes)
- Output file format
- Stream quality (default: best)

## License

This project is licensed under the GNU General Public License v3.0 - see the LICENSE file for details.

## Recordings

Recorded streams are saved in the `recordings/` directory with filenames in the format:
`streamer_name_YYYYMMDD_HHMMSS.ts`
