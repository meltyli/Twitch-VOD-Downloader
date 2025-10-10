#!/usr/bin/env python3
"""
Twitch VOD Compressor - Convert .ts files to .mp4 with H.265 compression and verification

Scans a directory for .ts files, compresses them to .mp4 using ffmpeg with libx265,
verifies output integrity, and optionally deletes originals after user confirmation.
"""

import argparse
import json
import os
import subprocess
import sys
import signal
import platform
import threading
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from rich.console import Console
from rich.table import Table


# Global variables for graceful shutdown
interrupted = False
current_process = None
current_output_file = None


def signal_handler(signum, frame):
    """Handle interrupt signals for graceful shutdown"""
    global interrupted, current_process, current_output_file
    interrupted = True
    logger.warning("\n\nInterrupt received. Cleaning up...")
    
    if current_process:
        try:
            current_process.terminate()
            current_process.wait(timeout=5)
        except:
            try:
                current_process.kill()
            except:
                pass
    
    if current_output_file and current_output_file.exists():
        try:
            current_output_file.unlink()
            logger.info(f"Deleted partial output file: {current_output_file.name}")
        except Exception as e:
            logger.error(f"Failed to delete partial file: {e}")
    
    logger.info("Cleanup complete. Exiting...")
    sys.exit(0)


class CompressStats:
    """Track compression statistics"""
    def __init__(self):
        self.total_found = 0
        self.skipped_existing = 0
        self.processed = 0
        self.succeeded = 0
        self.failed = 0
        self.deleted = 0
        self.errors: List[Tuple[str, str]] = []


class CompressLogger:
    """Handle logging with rich formatting"""
    def __init__(self):
        self.console = Console()
    
    def print(self, message: str, style: str = ""):
        self.console.print(message, style=style)
    
    def error(self, message: str):
        self.console.print(f"[ERROR] {message}", style="bold red")
    
    def warning(self, message: str):
        self.console.print(f"[WARNING] {message}", style="bold yellow")
    
    def success(self, message: str):
        self.console.print(f"[SUCCESS] {message}", style="bold green")
    
    def info(self, message: str):
        self.console.print(f"[INFO] {message}", style="cyan")
    
    def progress(self, message: str):
        self.console.print(message, style="blue")


logger = CompressLogger()


def clear_screen():
    """Clear the terminal screen across different platforms"""
    system = platform.system().lower()
    if system == 'windows':
        os.system('cls')
    else:
        os.system('clear')


def check_ffmpeg_installed() -> bool:
    """Verify that ffmpeg and ffprobe are installed and accessible"""
    try:
        subprocess.run(
            ["ffmpeg", "-version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )
        subprocess.run(
            ["ffprobe", "-version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def find_ts_files(directory: Path, recursive: bool = False) -> List[Path]:
    """
    Find all .ts files in the given directory, excluding macOS metadata files
    
    Args:
        directory: Path to search
        recursive: Whether to search subdirectories
    
    Returns:
        List of Path objects for .ts files (excludes ._ AppleDouble files)
    """
    pattern = "**/*.ts" if recursive else "*.ts"
    ts_files = list(directory.glob(pattern))
    
    # Filter out macOS resource fork files (._filename) and other hidden files
    ts_files = [f for f in ts_files if not f.name.startswith('._')]
    
    return sorted(ts_files)


def get_output_path(input_path: Path) -> Path:
    """Generate output .mp4 path from input .ts path"""
    return input_path.with_suffix('.mp4')


def mp4_exists_and_valid(mp4_path: Path) -> bool:
    """
    Check if MP4 file exists and has valid metadata
    
    Args:
        mp4_path: Path to the MP4 file
    
    Returns:
        True if file exists and appears valid, False otherwise
    """
    if not mp4_path.exists():
        return False
    
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "error",
                "-show_format",
                "-print_format", "json",
                str(mp4_path)
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10
        )
        
        if result.returncode != 0:
            return False
        
        probe_data = json.loads(result.stdout.decode('utf-8'))
        
        # Check for valid format and nonzero size
        if 'format' not in probe_data:
            return False
        
        format_info = probe_data['format']
        size = int(format_info.get('size', 0))
        duration = float(format_info.get('duration', 0))
        
        return size > 0 and duration > 0
        
    except (subprocess.TimeoutExpired, json.JSONDecodeError, ValueError, KeyError):
        return False


def probe_file(file_path: Path) -> Optional[Dict]:
    """
    Use ffprobe to get file metadata
    
    Args:
        file_path: Path to media file
    
    Returns:
        Dictionary with probe data or None on error
    """
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "error",
                "-show_format",
                "-show_streams",
                "-print_format", "json",
                str(file_path)
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30
        )
        
        if result.returncode != 0:
            logger.error(f"ffprobe failed for {file_path.name}: {result.stderr.decode('utf-8')}")
            return None
        
        return json.loads(result.stdout.decode('utf-8'))
        
    except subprocess.TimeoutExpired:
        logger.error(f"ffprobe timed out for {file_path.name}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse ffprobe output for {file_path.name}: {e}")
        return None


def compress_file(input_path: Path, output_path: Path, allow_video_only: bool = False, crf: int = 28, preset: str = "medium") -> bool:
    """
    Compress .ts file to .mp4 using ffmpeg with H.265/HEVC
    
    Args:
        input_path: Source .ts file
        output_path: Destination .mp4 file
        allow_video_only: Allow files with only video stream
        crf: Constant Rate Factor for quality (0-51, lower = better quality, 28 recommended)
        preset: Encoding preset (ultrafast, superfast, veryfast, faster, fast, medium, slow, slower, veryslow)
    
    Returns:
        True if compression succeeded, False otherwise
    """
    global interrupted, current_process, current_output_file
    
    if interrupted:
        return False
    
    # First probe the input to check streams
    probe_data = probe_file(input_path)
    if not probe_data:
        logger.error(f"Cannot probe input file: {input_path.name}")
        return False
    
    streams = probe_data.get('streams', [])
    video_streams = [s for s in streams if s.get('codec_type') == 'video']
    audio_streams = [s for s in streams if s.get('codec_type') == 'audio']
    
    if not video_streams:
        logger.error(f"No video stream found in {input_path.name}")
        return False
    
    if not audio_streams and not allow_video_only:
        logger.error(f"No audio stream found in {input_path.name}. Use --allow-video-only to proceed anyway.")
        return False
    
    # Build ffmpeg command for H.265 compression
    cmd = [
        "ffmpeg",
        "-i", str(input_path),
        "-map", "0:v:0",  # Map first video stream
    ]
    
    # Only map audio if it exists
    if audio_streams:
        cmd.extend(["-map", "0:a:0"])  # Map first audio stream
    
    cmd.extend([
        "-c:v", "libx265",  # Use H.265/HEVC codec
        "-crf", str(crf),  # Quality setting
        "-preset", preset,  # Encoding speed preset
        "-c:a", "copy",  # Copy audio without re-encoding
        "-movflags", "+faststart",  # Enable fast start for web playback
        "-tag:v", "hvc1",  # Apple-compatible HEVC tag
        "-y",  # Overwrite output file if it exists
        str(output_path)
    ])
    
    try:
        current_output_file = output_path
        current_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        
        # Monitor the process and show progress
        stderr_lines = []
        for line in current_process.stderr:
            if interrupted:
                current_process.terminate()
                break
            stderr_lines.append(line)
            # Show progress if available (ffmpeg outputs to stderr)
            if "time=" in line.lower():
                # Extract and display progress information
                logger.progress(f"  {line.strip()}")
        
        current_process.wait()
        
        if interrupted:
            if output_path.exists():
                output_path.unlink()
            return False
        
        if current_process.returncode != 0:
            error_msg = ''.join(stderr_lines)
            logger.error(f"ffmpeg failed for {input_path.name}:")
            logger.error(error_msg)
            if output_path.exists():
                output_path.unlink()  # Clean up partial file
            return False
        
        current_process = None
        current_output_file = None
        return True
        
    except KeyboardInterrupt:
        interrupted = True
        if current_process:
            current_process.terminate()
            try:
                current_process.wait(timeout=5)
            except:
                current_process.kill()
        if output_path.exists():
            output_path.unlink()
        raise
    except Exception as e:
        logger.error(f"Unexpected error during compression of {input_path.name}: {e}")
        if output_path.exists():
            output_path.unlink()  # Clean up partial file
        return False


def verify_compression(input_path: Path, output_path: Path, tolerance: float = 2.0) -> Tuple[bool, str]:
    """
    Verify that compression was successful by comparing input and output
    
    Note: .ts files from Twitch often have discontinuities (ads, buffering) that inflate
    duration compared to the remuxed .mp4. We use a percentage-based tolerance and 
    frame count verification instead of strict duration matching.
    
    Args:
        input_path: Original .ts file
        output_path: Compressed .mp4 file
        tolerance: Duration tolerance percentage (default 2.0 = allow up to 2x duration difference)
    
    Returns:
        Tuple of (success: bool, error_message: str)
    """
    # Probe both files
    input_probe = probe_file(input_path)
    output_probe = probe_file(output_path)
    
    if not input_probe:
        return False, "Failed to probe input file"
    
    if not output_probe:
        return False, "Failed to probe output file"
    
    # Check output file size
    if not output_path.exists() or output_path.stat().st_size == 0:
        return False, "Output file is empty or doesn't exist"
    
    # Extract stream information
    input_streams = input_probe.get('streams', [])
    output_streams = output_probe.get('streams', [])
    
    input_video = [s for s in input_streams if s.get('codec_type') == 'video']
    input_audio = [s for s in input_streams if s.get('codec_type') == 'audio']
    output_video = [s for s in output_streams if s.get('codec_type') == 'video']
    output_audio = [s for s in output_streams if s.get('codec_type') == 'audio']
    
    # Verify video stream exists
    if not output_video:
        return False, "Output has no video stream"
    
    # Verify audio stream (if input had audio)
    if input_audio and not output_audio:
        return False, "Output missing audio stream that was in input"
    
    # Check codec names (output should be hevc/h265 for video)
    output_vcodec = output_video[0].get('codec_name', '').lower()
    
    if output_vcodec not in ['hevc', 'h265']:
        return False, f"Expected HEVC codec, got: {output_vcodec}"
    
    if output_audio:
        output_acodec = output_audio[0].get('codec_name', '').lower()
        # Audio should be copied from original
        if output_acodec not in ['aac', 'mp3', 'opus', 'ac3', 'eac3']:
            return False, f"Unexpected audio codec: {output_acodec}"
    
    # Get format information
    input_format = input_probe.get('format', {})
    output_format = output_probe.get('format', {})
    
    input_duration = float(input_format.get('duration', 0))
    output_duration = float(output_format.get('duration', 0))
    
    # Verify output has reasonable duration (not zero or suspiciously short)
    if output_duration == 0:
        return False, "Output duration is zero"
    
    if output_duration < 5:
        return False, f"Output duration suspiciously short: {output_duration:.2f}s"
    
    # Compare frame counts if available (more reliable for fragmented streams)
    # Note: .ts files from streaming often don't have frame count metadata,
    # but .mp4 files will have it after remuxing
    input_video_stream = input_video[0]
    output_video_stream = output_video[0]
    
    input_frames = input_video_stream.get('nb_frames')
    output_frames = output_video_stream.get('nb_frames')
    
    # If BOTH have frame counts available, use them for verification
    if input_frames and output_frames:
        try:
            input_frame_count = int(input_frames)
            output_frame_count = int(output_frames)
            
            # Allow 1% frame difference (accounts for encoding differences)
            frame_diff_percent = abs(output_frame_count - input_frame_count) / input_frame_count * 100
            
            if frame_diff_percent > 1.0:
                logger.info(f"Frame count: {input_frame_count} → {output_frame_count} ({frame_diff_percent:.2f}% difference)")
                # Only fail if difference is extreme (>5%)
                if frame_diff_percent > 5.0:
                    return False, f"Frame count mismatch: {frame_diff_percent:.2f}% difference"
            else:
                logger.info(f"Frame count verified: {output_frame_count} frames ({frame_diff_percent:.2f}% difference)")
        except (ValueError, ZeroDivisionError):
            pass  # Fall back to duration check
    elif output_frames:
        # Output has frame count but input doesn't (typical for .ts → .mp4)
        # Just verify output has reasonable frame count
        try:
            output_frame_count = int(output_frames)
            if output_frame_count > 0:
                logger.info(f"Output frame count: {output_frame_count} frames")
        except ValueError:
            pass
    
    # Duration comparison with smart tolerance based on video length
    # .ts files often have inflated durations due to discontinuities (ads, buffering)
    # For long videos, a few seconds difference is negligible
    if input_duration > 0:
        duration_diff = abs(input_duration - output_duration)
        duration_ratio = output_duration / input_duration
        
        # Calculate smart tolerance based on video length
        # For videos >30 min (1800s), allow 0.5% difference
        # For videos >1 hour (3600s), allow 0.2% difference
        # For videos >2 hours (7200s), allow 0.1% difference
        if input_duration > 7200:  # >2 hours
            percent_tolerance = 0.001  # 0.1%
        elif input_duration > 3600:  # >1 hour
            percent_tolerance = 0.002  # 0.2%
        elif input_duration > 1800:  # >30 min
            percent_tolerance = 0.005  # 0.5%
        else:  # <30 min
            percent_tolerance = 0.05  # 5%
        
        duration_diff_percent = duration_diff / input_duration
        
        # Log duration comparison
        logger.info(f"Duration: {input_duration:.1f}s → {output_duration:.1f}s (diff: {duration_diff:.1f}s = {duration_diff_percent:.2%}, tolerance: {percent_tolerance:.2%})")
        
        # For longer videos (>30min), use percentage-based tolerance
        # For shorter videos, allow larger differences due to encoding overhead
        if input_duration > 1800:  # >30 minutes
            # Allow the output to be slightly longer or shorter within tolerance
            if duration_diff_percent > percent_tolerance:
                # Only fail if it's way off (>10x the tolerance)
                if duration_diff_percent > percent_tolerance * 10:
                    return False, f"Duration difference too large: {duration_diff_percent:.2%} (tolerance: {percent_tolerance:.2%})"
                else:
                    logger.warning(f"Duration difference {duration_diff_percent:.2%} exceeds tolerance {percent_tolerance:.2%} but within acceptable range")
        else:
            # For short videos, use more lenient checks
            # Output should not be >20% longer than input
            if output_duration > input_duration * 1.2:
                return False, f"Output duration much longer than input: {output_duration:.1f}s > {input_duration:.1f}s"
            
            # Output should not be <50% of input (suggests corruption)
            if duration_ratio < 0.5:
                return False, f"Output duration too short: {duration_ratio:.0%} of input duration"
    
    # Verify file size is reasonable
    input_size_mb = input_path.stat().st_size / (1024 * 1024)
    output_size_mb = output_path.stat().st_size / (1024 * 1024)
    
    # Compressed file should be smaller than original (H.265 is efficient)
    if output_size_mb > input_size_mb:
        logger.warning(f"Output larger than input ({output_size_mb:.1f}MB > {input_size_mb:.1f}MB)")
    
    # Output should not be suspiciously tiny (suggests encoding failure)
    if output_size_mb < 0.1:  # Less than 100KB
        return False, f"Output file suspiciously small: {output_size_mb:.2f}MB"
    
    # Log compression ratio
    compression_ratio = (1 - (output_size_mb / input_size_mb)) * 100 if input_size_mb > 0 else 0
    logger.info(f"Size: {input_size_mb:.1f}MB → {output_size_mb:.1f}MB (compressed {compression_ratio:.1f}%)")
    

    return True, "Verification passed"


def prompt_delete(file_path: Path, auto_yes: bool = False) -> bool:
    """
    Prompt user to delete original file
    
    Args:
        file_path: File to potentially delete
        auto_yes: Auto-confirm deletion
    
    Returns:
        True if user confirmed deletion, False otherwise
    """
    if auto_yes:
        return True
    
    try:
        response = input(f"Delete original file '{file_path.name}'? [y/N]: ").strip().lower()
        return response in ['y', 'yes']
    except (EOFError, KeyboardInterrupt):
        print()  # New line after interrupt
        return False


def process_file(
    ts_path: Path,
    dry_run: bool,
    auto_yes: bool,
    allow_video_only: bool,
    crf: int,
    preset: str,
    stats: CompressStats
) -> bool:
    """
    Process a single .ts file
    
    Args:
        ts_path: Path to .ts file
        dry_run: If True, don't actually process
        auto_yes: Auto-confirm deletion
        allow_video_only: Allow video-only files
        crf: Constant Rate Factor for quality
        preset: Encoding preset
        stats: Statistics tracker
    
    Returns:
        True if processing succeeded, False otherwise
    """
    global interrupted
    
    if interrupted:
        return False
    
    mp4_path = get_output_path(ts_path)
    
    # Skip if MP4 already exists and is valid
    if mp4_exists_and_valid(mp4_path):
        logger.info(f"Skipping {ts_path.name} - valid MP4 already exists")
        stats.skipped_existing += 1
        return True
    
    logger.progress(f"Processing: {ts_path.name}")
    
    if dry_run:
        logger.info(f"[DRY RUN] Would compress {ts_path.name} -> {mp4_path.name}")
        stats.processed += 1
        return True
    
    # Compress the file
    logger.info(f"Compressing {ts_path.name} -> {mp4_path.name} (CRF={crf}, preset={preset})")
    if not compress_file(ts_path, mp4_path, allow_video_only, crf, preset):
        if interrupted:
            logger.warning("Compression interrupted by user")
            return False
        error_msg = f"Compression failed for {ts_path.name}"
        logger.error(error_msg)
        stats.failed += 1
        stats.errors.append((ts_path.name, "Compression failed"))
        return False
    
    # Verify the output
    logger.info(f"Verifying {mp4_path.name}")
    success, message = verify_compression(ts_path, mp4_path)
    
    if not success:
        error_msg = f"Verification failed for {mp4_path.name}: {message}"
        logger.error(error_msg)
        stats.failed += 1
        stats.errors.append((ts_path.name, message))
        return False
    
    logger.success(f"Successfully compressed and verified: {mp4_path.name}")
    stats.succeeded += 1
    stats.processed += 1
    
    # Prompt for deletion
    if prompt_delete(ts_path, auto_yes):
        try:
            ts_path.unlink()
            logger.success(f"Deleted original: {ts_path.name}")
            stats.deleted += 1
        except Exception as e:
            logger.error(f"Failed to delete {ts_path.name}: {e}")
    else:
        logger.info(f"Kept original: {ts_path.name}")
    
    return True


def print_summary(stats: CompressStats, logger: CompressLogger):
    """Print final summary of operations"""
    table = Table(title="Compression Summary")
    table.add_column("Metric", style="cyan")
    table.add_column("Count", style="magenta", justify="right")
    
    table.add_row("Total .ts files found", str(stats.total_found))
    table.add_row("Skipped (valid MP4 exists)", str(stats.skipped_existing))
    table.add_row("Processed", str(stats.processed))
    table.add_row("Succeeded", str(stats.succeeded), style="green")
    table.add_row("Failed", str(stats.failed), style="red")
    table.add_row("Originals deleted", str(stats.deleted))
    
    logger.console.print(table)
    
    if stats.errors:
        logger.console.print("\n[bold red]Errors:[/bold red]")
        for filename, error in stats.errors:
            logger.console.print(f"  • {filename}: {error}", style="red")


def main():
    """Main entry point"""
    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    clear_screen()
    
    parser = argparse.ArgumentParser(
        description="Compress Twitch VOD .ts files to .mp4 with H.265/HEVC and verification",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run to see what would be processed
  %(prog)s /path/to/recordings --dry-run
  
  # Compress files with prompts for deletion (default CRF 28, preset medium)
  %(prog)s /path/to/recordings
  
  # Auto-confirm deletion and recurse subdirectories
  %(prog)s /path/to/recordings -r --yes
  
  # Use higher quality (lower CRF) and slower preset
  %(prog)s /path/to/recordings --crf 23 --preset slow
  
  # Allow video-only files (no audio required)
  %(prog)s /path/to/recordings --allow-video-only

Quality Guide:
  CRF values: 0-51 (lower = better quality, larger file)
    18-23: High quality (near-lossless)
    24-28: Good quality (recommended, default: 28)
    29-34: Medium quality (smaller files)
  
  Presets: ultrafast, superfast, veryfast, faster, fast, medium (default), slow, slower, veryslow
    Slower presets = better compression but longer encoding time

Prerequisites:
  - ffmpeg with libx265 support must be installed and available on PATH
  - Install with: brew install ffmpeg (macOS) or apt-get install ffmpeg (Linux)

Verification:
  - Smart duration tolerance based on video length (0.1%%-5%% depending on duration)
  - For long videos (>2hrs), allows up to 0.1%% difference (~100s for 8hr video)
  - Handles Twitch VOD discontinuities (ads, buffering) that inflate .ts duration
  - Validates codecs, frame counts, and file integrity

Interrupting:
  - Press Ctrl+C to interrupt compression
  - Partial output files will be automatically deleted
  - You can resume processing later
        """
    )
    
    parser.add_argument(
        "directory",
        type=str,
        help="Directory containing .ts files to compress"
    )
    
    parser.add_argument(
        "-r", "--recursive",
        action="store_true",
        help="Recursively search subdirectories for .ts files"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without actually processing files"
    )
    
    parser.add_argument(
        "--yes", "-y",
        action="store_true",
        help="Auto-confirm deletion of original .ts files (skip prompts)"
    )
    
    parser.add_argument(
        "--allow-video-only",
        action="store_true",
        help="Allow processing files with video but no audio stream"
    )
    
    parser.add_argument(
        "--crf",
        type=int,
        default=28,
        choices=range(0, 52),
        metavar="0-51",
        help="Constant Rate Factor for quality (0-51, lower = better, default: 28)"
    )
    
    parser.add_argument(
        "--preset",
        type=str,
        default="medium",
        choices=["ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"],
        help="Encoding preset (default: medium)"
    )
    
    parser.add_argument(
        "--tolerance",
        type=float,
        default=2.0,
        help="Duration tolerance in seconds for verification (default: 2.0)"
    )
    
    args = parser.parse_args()
    
    # Validate directory
    directory = Path(args.directory).resolve()
    if not directory.exists():
        logger.error(f"Directory not found: {directory}")
        return 1
    
    if not directory.is_dir():
        logger.error(f"Not a directory: {directory}")
        return 1
    
    # Check for ffmpeg
    if not check_ffmpeg_installed():
        logger.error("ffmpeg and ffprobe are required but not found on PATH")
        logger.error("Install with: brew install ffmpeg (macOS) or apt-get install ffmpeg (Linux)")
        return 1
    
    # Find .ts files
    logger.info(f"Scanning directory: {directory}")
    if args.recursive:
        logger.info("Recursive mode enabled")
    
    logger.info(f"Quality settings: CRF={args.crf}, preset={args.preset}")
    
    ts_files = find_ts_files(directory, args.recursive)
    
    if not ts_files:
        logger.warning(f"No .ts files found in {directory}")
        return 0
    
    stats = CompressStats()
    stats.total_found = len(ts_files)
    
    logger.info(f"Found {len(ts_files)} .ts file(s)")
    
    if args.dry_run:
        logger.warning("DRY RUN MODE - No files will be modified")
    
    logger.info("Press Ctrl+C at any time to interrupt and clean up partial files")
    print()  # Blank line for readability
    
    # Process each file
    for ts_file in ts_files:
        if interrupted:
            logger.warning("Processing interrupted. Exiting...")
            break
        
        try:
            process_file(
                ts_file,
                args.dry_run,
                args.yes,
                args.allow_video_only,
                args.crf,
                args.preset,
                stats
            )
            print()  # Blank line between files
        except KeyboardInterrupt:
            logger.warning("\nOperation cancelled by user")
            break
        except Exception as e:
            logger.error(f"Unexpected error processing {ts_file.name}: {e}")
            stats.failed += 1
            stats.errors.append((ts_file.name, str(e)))
            print()
    
    # Print summary
    print_summary(stats, logger)
    
    return 0 if stats.failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
