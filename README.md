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
- ffmpeg (required for the remux tool)

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

### 5. Install ffmpeg (Required for Remux Tool)

#### On macOS:
```bash
brew install ffmpeg
```

#### On Linux (Ubuntu/Debian):
```bash
sudo apt-get update
sudo apt-get install ffmpeg
```

#### On Windows:
Download from [ffmpeg.org](https://ffmpeg.org/download.html) and add to PATH

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

## Remux Tool

Convert recorded `.ts` files to `.mp4` format with verification.

### Usage

```bash
# Dry run to preview
python tools/remux_ts_to_mp4.py recordings/ --dry-run

# Remux with prompts for each deletion
python tools/remux_ts_to_mp4.py recordings/

# Auto-confirm deletion
python tools/remux_ts_to_mp4.py recordings/ --yes

# Recursive processing
python tools/remux_ts_to_mp4.py recordings/ -r --yes
```

### Features

- Fast remuxing with ffmpeg stream copy (no re-encoding)
- Comprehensive verification of output integrity
- Handles data streams (timed_id3) automatically
- Skips existing valid MP4s
- Optional deletion with prompts or auto-confirm
- Dry-run mode

### Prerequisites

Requires ffmpeg and ffprobe:
```bash
# macOS
brew install ffmpeg

# Linux
sudo apt-get install ffmpeg
```

Allow files with video but no audio:
```bash
python tools/remux_ts_to_mp4.py recordings/ --allow-video-only
```

#### Command-Line Options

- `directory` - Path to directory containing .ts files (required)
- `-r, --recursive` - Recursively search subdirectories for .ts files
- `--dry-run` - Show what would be done without modifying files
- `-y, --yes` - Auto-confirm deletion of original .ts files
- `--allow-video-only` - Allow processing files without audio streams
- `--tolerance` - Duration tolerance in seconds for verification (default: 0.5)

#### How It Works

1. **Discovery**: Scans the specified directory for .ts files
2. **Skip Check**: Skips files that already have valid .mp4 versions
3. **Remux**: Converts .ts to .mp4 using `ffmpeg -c copy` (stream copy, no re-encoding)
   - Explicitly maps first video stream and first audio stream
   - Excludes data streams (e.g., timed_id3) that can cause issues in MP4 containers
   - Adds `+faststart` flag for better web/streaming playback
4. **Verification**: Uses ffprobe to verify:
   - Output file has nonzero size
   - Duration matches input within tolerance (±0.5s by default)
   - Video and audio streams present (matching input)
   - Codecs are valid (h264/hevc for video, aac/mp3/opus for audio)
   - Container metadata is readable
5. **Cleanup**: Optionally deletes original .ts file after user confirmation

#### Verification Details

The tool performs comprehensive verification to ensure remuxed files are valid:

- **Stream Comparison**: Ensures output has the same number and types of streams as input
- **Duration Check**: Compares input and output durations within a small tolerance
- **Codec Validation**: Verifies expected codecs (h264/hevc for video, aac/mp3/opus for audio)
- **Size Check**: Ensures output file is non-zero size
- **Metadata Validation**: Confirms output container has valid, readable metadata

If verification fails, the original .ts file is kept and an error is logged.

#### Example Output

```
[INFO] Scanning directory: /path/to/recordings
[INFO] Found 3 .ts file(s)

Processing: streamer_20251008_024102.ts
[INFO] Remuxing streamer_20251008_024102.ts -> streamer_20251008_024102.mp4
[INFO] Verifying streamer_20251008_024102.mp4
[SUCCESS] Successfully remuxed and verified: streamer_20251008_024102.mp4
Delete original file 'streamer_20251008_024102.ts'? [y/N]: y
[SUCCESS] Deleted original: streamer_20251008_024102.ts

                  Remux Summary                  
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━┓
┃ Metric                     ┃ Count ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━┩
│ Total .ts files found      │     3 │
│ Skipped (valid MP4 exists) │     0 │
│ Processed                  │     3 │
│ Succeeded                  │     3 │
│ Failed                     │     0 │
│ Originals deleted          │     3 │
└────────────────────────────┴───────┘
```

#### Troubleshooting

**ffmpeg not found**:
- Make sure ffmpeg is installed: `brew install ffmpeg` (macOS) or `apt-get install ffmpeg` (Linux)
- Verify installation: `ffmpeg -version`

**No audio stream error**:
- Use `--allow-video-only` flag if the file intentionally has no audio
- Check the input file with: `ffprobe input.ts`

**Verification failed**:
- The tool will keep the original .ts file and log the specific error
- Common causes: corrupted input file, interrupted ffmpeg process, or disk space issues

**Duration mismatch**:
- Adjust tolerance with `--tolerance 1.0` for files with timing irregularities

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
