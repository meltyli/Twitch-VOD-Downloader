# Twitch VOD Downloader

A Python script that automatically monitors when a Twitch streamer goes live and downloads their stream for later viewing.

## Features

- Automatically detects when a streamer goes live
- Records streams in high quality
- Saves recordings with timestamps for easy organization
- Handles stream interruptions gracefully
- Simple command-line interface

## Prerequisites

- Python 3.6+ 
- pip
- venv (included with Python standard library)

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
```bash
python -m src.twitch_recorder
```

3. When prompted, enter the Twitch username of the streamer you want to monitor.

### Deactivating the Virtual Environment

When you're done, you can deactivate the virtual environment:

```bash
deactivate
```

## Configuration

You can modify the following parameters in the script:
- Check interval (default: 5 minutes)
- Output file format
- Stream quality (default: best)

## Recordings

Recorded streams are saved in the `recordings/` directory with filenames in the format:
`streamer_name_YYYYMMDD_HHMMSS.ts`

## Troubleshooting

- Ensure you have the latest version of Python
- Make sure Streamlink is correctly installed
- Check that you have write permissions in the project directory

## License

This project is licensed under the GNU General Public License v3.0 - see the LICENSE file for details.
