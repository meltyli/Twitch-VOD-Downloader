# Twitch VOD Downloader

A Python script that helps you record live Twitch streams for later viewing.

## Features

- Manually select and record live Twitch streams
- Add and manage a list of monitored streamers
- Records streams in high quality
- Saves recordings with timestamps
- Simple command-line interface

## Prerequisites

- Python 3.6+ 
- pip
- venv (included with Python standard library)
- Streamlink

## Setup and Installation

### 1. Clone the Repository

```bash
git clone https://github.com/meltyli/twitch-vod-downloader.git
cd twitch-vod-downloader
```

### 2. Create a Virtual Environment

#### On Windows:
```bash
# Create virtual environment
python -m venv venv

# Activate the virtual environment
.\venv\Scripts\activate
```

#### On macOS and Linux:
```bash
# Create virtual environment
python3 -m venv venv

# Activate the virtual environment
source venv/bin/activate
```

### 3. Install Dependencies

With the virtual environment activated, install the required packages:

```bash
pip install -r requirements.txt
```

### 4. Verify Streamlink Installation

```bash
streamlink --version
```

## Usage

1. Ensure your virtual environment is activated

2. Run the script:

- On macOS / Linux (recommended):
```bash
./launch.sh
```

- Or run directly with Python in a terminal / command prompt:
```bash
python -m src.twitch_recorder
```

3. Follow the prompts shown by the script. Use the menu to:
   - Add streamers to your monitoring list
   - Remove streamers
   - List monitored streamers
   - Start monitoring for live streams
   - Change settings (output directory, check interval)

4. When monitoring, the script will:
   - Check which streamers are currently live
   - Let you choose a single streamer to record
   - Allow you to stop recording by pressing Enter

### Stopping a Recording

- Press `q` and then `Enter` to stop the current recording
- Use Ctrl+C to interrupt the recording process

### Deactivating the Virtual Environment

When you're done, you can deactivate the virtual environment:

```bash
deactivate
```

## Configuration

Settings are stored in `config.json` and include:
- List of monitored streamers
- Output directory for recordings (default: `recordings/`)
- Default check interval for periodic monitoring (default: 2 minutes)

You can change these settings through the Settings menu (option 5).

## Recordings

Recorded streams are saved in the configured output directory (default: `recordings/`) with filenames in the format:
`streamer_name_YYYYMMDD_HHMMSS.ts`

## Limitations

- Only one stream can be recorded at a time
- You must manually start another instance to record multiple streams simultaneously

## Troubleshooting

- Ensure you have the latest version of Python
- Make sure Streamlink is correctly installed
- Check that you have write permissions in the project directory

## Notes

- The script requires an active internet connection
- Stream quality defaults to the best available option
- Requires Streamlink to be installed and working correctly

## License

This project is licensed under the GNU General Public License v3.0 - see the LICENSE file for details.
