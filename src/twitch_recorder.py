from datetime import datetime
import time
import subprocess
import json
import os
import sys
import signal
import platform
import threading
import logging
from logging.handlers import RotatingFileHandler
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, DownloadColumn, TimeRemainingColumn
from rich.live import Live
from rich.table import Table

class StreamRecorder:
    def __init__(self, config_file='config.json'):
        self.config_file = config_file

        # Configure logging early so errors during startup are captured.
        logs_dir = os.environ.get('LOGS_DIR', '/logs')
        try:
            os.makedirs(logs_dir, exist_ok=True)
        except Exception:
            # If we can't create the dir (permissions), fall back to cwd 'logs'
            logs_dir = os.path.join(os.getcwd(), 'logs')
            os.makedirs(logs_dir, exist_ok=True)

        log_file = os.path.join(logs_dir, 'log')
        logger = logging.getLogger('twitch_recorder')
        logger.setLevel(logging.INFO)

        # Stream handler (stdout)
        sh = logging.StreamHandler(sys.stdout)
        sh.setLevel(logging.INFO)

        # Rotating file handler
        fh = RotatingFileHandler(log_file, maxBytes=10 * 1024 * 1024, backupCount=5)
        fh.setLevel(logging.INFO)

        formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
        sh.setFormatter(formatter)
        fh.setFormatter(formatter)

        # Avoid adding duplicate handlers if re-instantiated
        if not logger.handlers:
            logger.addHandler(sh)
            logger.addHandler(fh)

        self.logger = logger

        # Load config after logging is configured
        self.config = self.load_config()
        self.streamers = self.config.get('streamers', [])
        self.output_directory = self.config.get('output_directory', 'recordings')
        self.compressed_directory = self.config.get('compressed_directory', os.path.join(self.output_directory, 'compressed'))
        self.default_check_interval = self.config.get('default_check_interval', 2)
        self.default_crf = self.config.get('default_crf', 24)
        self.default_preset = self.config.get('default_preset', 'faster')

        # New configurable network settings for stream checks
        self.stream_check_timeout = float(self.config.get('stream_check_timeout', 10))
        self.stream_check_retries = int(self.config.get('stream_check_retries', 2))
        self.stream_check_backoff = float(self.config.get('stream_check_backoff', 5))
        # Headless mode flag (may be set during first-run prompt)
        self.run_headless = bool(self.config.get('run_headless', False))
        self.current_process = None  # Keep for backward compatibility with old methods
        self.active_recordings = {}  # Dictionary of {streamer_name: process}
        self.recording_threads = {}  # Dictionary of {streamer_name: thread}
        self.monitoring_thread = None
        self.stop_monitoring_event = threading.Event()
        self.stop_all_recordings = threading.Event()
        self.recordings_path = 'recordings'  # Default recordings directory
        self.console = Console()
        self.monitoring_interrupted = False  # Flag for Ctrl+C during monitoring

    def monitoring_signal_handler(self, signum, frame):
        """Handle Ctrl+C during monitoring to gracefully stop and return to menu"""
        if not self.monitoring_interrupted:
            self.monitoring_interrupted = True
            self.console.print("\n[bold yellow]Interrupt received. Stopping all monitoring and recordings...[/bold yellow]")
            self.stop_all_recordings.set()

    def clear_screen(self):
        """Clear the terminal screen across different platforms"""
        system = platform.system().lower()
        if system == 'windows':
            os.system('cls')
        else:
            os.system('clear')

    def load_config(self):
        """Load configuration from JSON file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    # Add network/check defaults if not present
                    if 'stream_check_timeout' not in config:
                        config['stream_check_timeout'] = 10
                    if 'stream_check_retries' not in config:
                        config['stream_check_retries'] = 2
                    if 'stream_check_backoff' not in config:
                        config['stream_check_backoff'] = 5
                    # Add compressed_directory if not present
                    if 'compressed_directory' not in config:
                        config['compressed_directory'] = os.path.join(config.get('output_directory', 'recordings'), 'compressed')
                    # Add compression defaults if not present
                    if 'default_crf' not in config:
                        config['default_crf'] = 24
                    if 'default_preset' not in config:
                        config['default_preset'] = 'faster'
                    return config

            # Return default configuration
            return {
                'streamers': [],
                'output_directory': 'recordings',
                'stream_check_timeout': 10,
                'stream_check_retries': 2,
                'stream_check_backoff': 5,
                'compressed_directory': 'recordings/compressed',
                'default_check_interval': 2,
                'default_crf': 24,
                'default_preset': 'faster'
            }
        except Exception as e:
            # Logging may not be available in some very early failure modes; fall back to print
            try:
                self.logger.exception(f"Error loading config: {e}")
            except Exception:
                print(f"Error loading config: {e}")
            return {
                'streamers': [],
                'output_directory': 'recordings',
                'compressed_directory': 'recordings/compressed',
                'default_check_interval': 2,
                'default_crf': 24,
                'default_preset': 'faster'
            }

    def save_config(self):
        """Save configuration to JSON file"""
        try:
            self.config = {
                'streamers': self.streamers,
                'output_directory': self.output_directory,
                'compressed_directory': self.compressed_directory,
                'default_check_interval': self.default_check_interval,
                'default_crf': self.default_crf,
                'default_preset': self.default_preset,
                'stream_check_timeout': self.stream_check_timeout,
                'stream_check_retries': self.stream_check_retries,
                'stream_check_backoff': self.stream_check_backoff
                ,
                'run_headless': self.run_headless
            }
            # If the config file or directory is not writable (e.g., mounted read-only in Docker), skip saving.
            config_path = os.path.abspath(self.config_file)
            config_dir = os.path.dirname(config_path) or os.getcwd()
            if os.path.exists(config_path):
                if not os.access(config_path, os.W_OK):
                    try:
                        self.logger.warning("Config file %s is not writable; skipping save", self.config_file)
                    except Exception:
                        print(f"Config file {self.config_file} is not writable; skipping save")
                    return
            else:
                if not os.access(config_dir, os.W_OK):
                    try:
                        self.logger.warning("Config directory %s is not writable; skipping save", config_dir)
                    except Exception:
                        print(f"Config directory {config_dir} is not writable; skipping save")
                    return

            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            try:
                self.logger.exception(f"Error saving config: {e}")
            except Exception:
                print(f"Error saving config: {e}")

    def is_stream_live(self, channel_name):
        """Check if a Twitch channel is currently live."""
        timeout = float(getattr(self, 'stream_check_timeout', 10))
        retries = int(getattr(self, 'stream_check_retries', 2))
        backoff = float(getattr(self, 'stream_check_backoff', 5))

        cmd = f"streamlink --json https://twitch.tv/{channel_name}"

        for attempt in range(1, retries + 2):
            try:
                result = subprocess.run(
                    cmd,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=timeout
                )

                if result.returncode != 0:
                    # Non-zero exit code - log and possibly retry
                    self.logger.warning("streamlink returned non-zero for %s (attempt %d): %s", channel_name, attempt, result.stderr.strip())
                else:
                    try:
                        stream_info = json.loads(result.stdout)
                        return stream_info.get('streams') is not None and len(stream_info.get('streams')) > 0
                    except json.JSONDecodeError:
                        self.logger.warning("Failed to parse streamlink JSON for %s (attempt %d)", channel_name, attempt)

            except subprocess.TimeoutExpired as e:
                self.logger.warning("streamlink timeout checking %s (attempt %d): %s", channel_name, attempt, str(e))
            except Exception as e:
                self.logger.exception("Unexpected error when checking %s (attempt %d): %s", channel_name, attempt, str(e))

            # If here, attempt failed. If more attempts remain, sleep exponential backoff
            if attempt <= retries:
                sleep_time = backoff * (2 ** (attempt - 1))
                self.logger.info("Retrying %s in %.1f seconds (attempt %d of %d)", channel_name, sleep_time, attempt + 1, retries + 1)
                time.sleep(sleep_time)

        # All attempts exhausted
        self.logger.error("All attempts exhausted checking if %s is live; marking as offline", channel_name)
        return False

    def find_live_streamers(self):
        """Find which streamers in the list are currently live"""
        live_streamers = []
        print("Checking live status of streamers...")
        for streamer in self.streamers:
            if self.is_stream_live(streamer):
                live_streamers.append(streamer)
        return live_streamers

    def record_stream(self, channel_name):
        """Record a single stream"""
        try:
            # Create output directory if it doesn't exist
            os.makedirs(self.output_directory, exist_ok=True)

            # Format filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = os.path.join(self.output_directory, f"{channel_name}_{timestamp}.ts")
            
            # Start recording
            try:
                self.logger.info(f"Recording {channel_name}'s stream to {output_file}")
            except Exception:
                print(f"[{datetime.now()}] Recording {channel_name}'s stream to {output_file}")
            
            # Use subprocess to start recording
            command = f"streamlink https://twitch.tv/{channel_name} best -o {output_file}"
            self.current_process = subprocess.Popen(command, shell=True)
            
            # Create a thread to monitor the subprocess
            def monitor_process():
                self.current_process.wait()
                try:
                    self.logger.info("Stream ended naturally.")
                except Exception:
                    print("Stream ended naturally.")
                self.stop_recording()
                
            monitor_thread = threading.Thread(target=monitor_process)
            monitor_thread.daemon = True
            monitor_thread.start()
            
            # Wait for user input to manually stop recording
            print("Press Enter to stop recording manually...")
            input()  # This still allows manual stopping
            if self.current_process and self.current_process.poll() is None:
                # Only stop if process is still running
                self.stop_recording()
        except Exception as e:
            try:
                self.logger.exception(f"Error recording {channel_name}'s stream: {e}")
            except Exception:
                print(f"Error recording {channel_name}'s stream: {e}")

    def record_stream_concurrent(self, channel_name, progress, task_id):
        """Record a single stream with progress tracking"""
        try:
            # Create output directory if it doesn't exist
            os.makedirs(self.output_directory, exist_ok=True)

            # Format filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = os.path.join(self.output_directory, f"{channel_name}_{timestamp}.ts")

            # Start recording
            progress.update(task_id, description=f"[green]{channel_name}: Recording...")

            # Use subprocess to start recording
            command = f"streamlink https://twitch.tv/{channel_name} best -o {output_file}"
            process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            self.active_recordings[channel_name] = process

            # Monitor the process
            while process.poll() is None and not self.stop_all_recordings.is_set():
                # Check file size for progress indication
                if os.path.exists(output_file):
                    file_size = os.path.getsize(output_file)
                    progress.update(task_id, completed=file_size / (1024 * 1024))  # Convert to MB
                time.sleep(1)

            # Process ended or stop requested
            if self.stop_all_recordings.is_set() and process.poll() is None:
                progress.update(task_id, description=f"[yellow]{channel_name}: Stopping gracefully...")
                process.terminate()
                try:
                    process.wait(timeout=5)
                    progress.update(task_id, description=f"[blue]{channel_name}: Stopped and saved")
                except subprocess.TimeoutExpired:
                    process.kill()
                    progress.update(task_id, description=f"[red]{channel_name}: Force stopped")
            else:
                progress.update(task_id, description=f"[blue]{channel_name}: Stream ended, saved to {os.path.basename(output_file)}")

        except Exception as e:
            progress.update(task_id, description=f"[red]{channel_name}: Error - {str(e)}")
        finally:
            if channel_name in self.active_recordings:
                del self.active_recordings[channel_name]

    def monitor_and_record_streamer(self, channel_name, check_interval, progress, task_id):
        """Continuously monitor and record a streamer when they go live"""
        progress.update(task_id, description=f"[cyan]{channel_name}: Checking if live...")

        while not self.stop_all_recordings.is_set():
            try:
                # Check if stream is live
                if self.is_stream_live(channel_name):
                    progress.update(task_id, description=f"[yellow]{channel_name}: Stream detected! Starting recording...")

                    # Start recording
                    self.record_stream_concurrent(channel_name, progress, task_id)

                    # After recording ends, wait a bit before checking again
                    if not self.stop_all_recordings.is_set():
                        progress.update(task_id, description=f"[cyan]{channel_name}: Waiting 30s before next check...")
                        for _ in range(30):
                            if self.stop_all_recordings.is_set():
                                break
                            time.sleep(1)
                else:
                    # Not live, show monitoring status
                    progress.update(task_id, description=f"[dim]{channel_name}: Offline - checking in {check_interval}m...")

                # Wait for check interval
                if not self.stop_all_recordings.is_set():
                    wait_time = check_interval * 60
                    for _ in range(wait_time):
                        if self.stop_all_recordings.is_set():
                            break
                        time.sleep(1)

            except Exception as e:
                progress.update(task_id, description=f"[red]{channel_name}: Error - {str(e)}")
                time.sleep(60)  # Wait a minute before retrying on error

        progress.update(task_id, description=f"[blue]{channel_name}: Monitoring stopped")

    def monitor_multiple_streamers(self, selected_streamers, check_interval):
        """Monitor and record multiple streamers concurrently with progress bars"""
        self.stop_all_recordings.clear()
        self.monitoring_interrupted = False

        # Set up signal handler for Ctrl+C
        original_sigint_handler = signal.signal(signal.SIGINT, self.monitoring_signal_handler)

        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.completed:.1f}MB"),
                console=self.console
            ) as progress:

                # Create progress tasks for each streamer
                tasks = {}
                for streamer in selected_streamers:
                    task_id = progress.add_task(f"[cyan]{streamer}: Initializing...", total=None)
                    tasks[streamer] = task_id

                # Start monitoring threads for each streamer
                threads = []
                for streamer in selected_streamers:
                    thread = threading.Thread(
                        target=self.monitor_and_record_streamer,
                        args=(streamer, check_interval, progress, tasks[streamer])
                    )
                    thread.daemon = True
                    thread.start()
                    threads.append(thread)
                    self.recording_threads[streamer] = thread

                # Show instructions
                self.console.print("\n[bold yellow]Press Ctrl+C to stop all monitoring and save any active recordings[/bold yellow]")

                # Wait for all threads to complete or stop signal
                for thread in threads:
                    thread.join()

                if self.monitoring_interrupted:
                    self.console.print("\n[bold green]All monitoring stopped. Returning to menu...[/bold green]")
                else:
                    self.console.print("\n[bold green]All monitoring completed[/bold green]")
                
                self.recording_threads.clear()

        finally:
            # Restore original signal handler
            signal.signal(signal.SIGINT, original_sigint_handler)

    def stop_recording(self):
        """Stop the current recording"""
        if self.current_process:
            try:
                self.current_process.terminate()
                self.current_process.wait(timeout=5)
                print("Recording stopped.")

                # Add delay before checking again
                if hasattr(self, 'monitor_after_stream') and self.monitor_after_stream:
                    print(f"Waiting 30 seconds before checking if {self.current_streamer} is live again...")
                    time.sleep(30)

                    # Resume monitoring with the same settings
                    if hasattr(self, 'current_streamer') and hasattr(self, 'current_interval'):
                        print(f"Checking if {self.current_streamer} is live again...")
                        self.start_monitoring(self.current_streamer, self.current_interval)

            except subprocess.TimeoutExpired:
                print("Force terminating recording...")
                self.current_process.kill()
            finally:
                self.current_process = None

    def add_streamer(self):
        """Add a new streamer to monitor"""
        # Display current streamers
        print("\nCurrent Monitored Streamers:")
        for streamer in self.streamers:
            print(streamer)
        
        # Prompt for new streamer
        streamer = input("\nEnter Twitch username to add (or 'q' to cancel): ").strip().lower()
        
        if streamer == 'q':
            return

        if streamer and streamer not in self.streamers:
            self.streamers.append(streamer)
            self.save_config()
            print(f"Added {streamer} to monitored streamers.")
        else:
            print("Streamer already exists or invalid name.")
        
        input("Press Enter to continue...")

    def remove_streamer(self):
        """Remove a streamer from monitoring"""
        if not self.streamers:
            print("No streamers to remove.")
            input("Press Enter to continue...")
            return

        # Display streamers with numbers
        print("\nCurrently Monitored Streamers:")
        for i, streamer in enumerate(self.streamers, 1):
            print(f"{i}. {streamer}")

        # Prompt user to choose a streamer to remove
        try:
            choice = input("\nEnter the number of the streamer to remove (or 'q' to quit): ")
            
            if choice.lower() == 'q':
                return

            # Validate choice
            index = int(choice) - 1
            if 0 <= index < len(self.streamers):
                removed_streamer = self.streamers.pop(index)
                self.save_config()
                print(f"Removed {removed_streamer} from monitored streamers.")
            else:
                print("Invalid selection.")
        except ValueError:
            print("Invalid input. Please enter a number or 'q'.")
        
        input("Press Enter to continue...")

    def periodic_live_check(self, check_interval):
        """Periodically check for live streamers"""
        while not self.stop_monitoring_event.is_set():
            print(f"\nChecking for live streamers (interval: {check_interval} minutes)...")
            live_streamers = self.find_live_streamers()

            if live_streamers:
                print("\nLive Streamers Found:")
                for i, streamer in enumerate(live_streamers, 1):
                    print(f"{i}. {streamer}")
                
                try:
                    choice = input("Enter the number of the streamer to record (or 'q' to stop checking): ")
                    
                    if choice.lower() == 'q':
                        break

                    # Validate choice
                    index = int(choice) - 1
                    if 0 <= index < len(live_streamers):
                        selected_streamer = live_streamers[index]
                        # Stop periodic checking before recording
                        self.stop_monitoring_event.set()
                        self.record_stream(selected_streamer)
                        break
                except ValueError:
                    print("Invalid input. Please enter a number or 'q'.")
            
            # Wait for the specified interval
            wait_time = check_interval * 60  # convert minutes to seconds
            self.stop_monitoring_event.wait(wait_time)

    def start_monitoring(self, selected_streamer=None, check_interval=None):
        """Start monitoring streamers with continuous automatic recording"""
        if not self.streamers:
            print("No streamers added. Please add streamers first.")
            input("Press Enter to continue...")
            return

        # Display all monitored streamers
        print("\nMonitored Streamers:")
        for i, streamer in enumerate(self.streamers, 1):
            print(f"{i}. {streamer}")

        print("\n[Multi-Selection Mode]")
        print("Enter streamer numbers separated by commas (e.g., 1,2,3) to monitor multiple streamers (max 5)")
        print("Streams will automatically start recording when they go live")

        # Get streamer selection
        selected_streamers = []
        while True:
            try:
                choice = input("\nEnter your selection (or 'q' to quit): ")

                if choice.lower() == 'q':
                    return

                # Parse selection (handles both single and multi-selection)
                if ',' in choice:
                    indices = [int(x.strip()) - 1 for x in choice.split(',')]
                else:
                    indices = [int(choice.strip()) - 1]

                # Validate all selections
                if all(0 <= idx < len(self.streamers) for idx in indices):
                    if len(indices) > 5:
                        print("You can only select up to 5 streamers at once. Please try again.")
                        continue

                    selected_streamers = [self.streamers[idx] for idx in indices]
                    print(f"\nSelected streamers: {', '.join(selected_streamers)}")
                    break
                else:
                    print("Invalid selection. Please try again.")
            except ValueError:
                print("Invalid input. Please enter valid numbers.")

        # Use default check interval from config
        check_interval = self.default_check_interval

        print(f"\nStarting continuous monitoring for {len(selected_streamers)} streamer(s)")
        print(f"Check interval: {check_interval} minutes (change in Settings menu if needed)")
        print("Streams will automatically record when live and resume monitoring after they end")
        print()

        # Start monitoring
        self.monitor_multiple_streamers(selected_streamers, check_interval)

    def change_settings(self):
        """Change application settings"""
        while True:
            self.clear_screen()
            print("\n--- Settings ---")
            print(f"1. Change Output Directory (Current: {self.output_directory})")
            print(f"2. Change Compressed Output Directory (Current: {self.compressed_directory})")
            print(f"3. Change Default Check Interval (Current: {self.default_check_interval} minutes)")
            print(f"4. Change Default Compression CRF (Current: {self.default_crf})")
            print(f"5. Change Default Compression Preset (Current: {self.default_preset})")
            print("q. Back to Main Menu")

            choice = input("Enter your choice (1-5, q): ").strip().lower()

            if choice == '1':
                new_dir = input(f"\nEnter new output directory (current: {self.output_directory}): ").strip()
                if new_dir:
                    self.output_directory = new_dir
                    self.save_config()
                    print(f"Output directory changed to: {self.output_directory}")
                    input("Press Enter to continue...")
            elif choice == '2':
                new_dir = input(f"\nEnter new compressed output directory (current: {self.compressed_directory}): ").strip()
                if new_dir:
                    self.compressed_directory = new_dir
                    self.save_config()
                    print(f"Compressed output directory changed to: {self.compressed_directory}")
                    input("Press Enter to continue...")
            elif choice == '3':
                try:
                    new_interval = input(f"\nEnter new default check interval in minutes (current: {self.default_check_interval}): ").strip()
                    if new_interval:
                        interval = float(new_interval)
                        if interval > 0:
                            self.default_check_interval = interval
                            self.save_config()
                            print(f"Default check interval changed to: {self.default_check_interval} minutes")
                        else:
                            print("Interval must be greater than 0.")
                    input("Press Enter to continue...")
                except ValueError:
                    print("Invalid input. Please enter a valid number.")
                    input("Press Enter to continue...")
            elif choice == '4':
                try:
                    print("\nCRF (Constant Rate Factor): 0-51 (lower = better quality, larger file)")
                    print("Recommended: 20-28 (default: 24, optimized for streaming content)")
                    new_crf = input(f"Enter new default CRF (current: {self.default_crf}): ").strip()
                    if new_crf:
                        crf = int(new_crf)
                        if 0 <= crf <= 51:
                            self.default_crf = crf
                            self.save_config()
                            print(f"Default CRF changed to: {self.default_crf}")
                        else:
                            print("CRF must be between 0 and 51.")
                    input("Press Enter to continue...")
                except ValueError:
                    print("Invalid input. Please enter a valid number.")
                    input("Press Enter to continue...")
            elif choice == '5':
                print("\nAvailable presets: ultrafast, superfast, veryfast, faster, fast, medium, slow, slower, veryslow")
                print("Faster presets = quicker encoding (recommended: 'faster' for good balance)")
                print("Slower presets = better compression but longer encoding time")
                new_preset = input(f"Enter new default preset (current: {self.default_preset}): ").strip().lower()
                valid_presets = ["ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"]
                if new_preset in valid_presets:
                    self.default_preset = new_preset
                    self.save_config()
                    print(f"Default preset changed to: {self.default_preset}")
                elif new_preset:
                    print("Invalid preset. No changes made.")
                input("Press Enter to continue...")
            elif choice == 'q':
                break
            else:
                print("Invalid choice. Please try again.")
                input("Press Enter to continue...")

    def compress_recordings(self, dry_run=False):
        """Compress .ts recordings to .mp4 format with H.265"""
        from pathlib import Path
        import src.compression as compress_module
        
        # Reset the interrupted flag before starting
        compress_module.interrupted = False
        
        # Find .ts files in the output directory
        output_path = Path(self.output_directory)
        if not output_path.exists():
            print(f"Output directory does not exist: {self.output_directory}")
            input("Press Enter to continue...")
            return
        
        # Get all .ts files and filter out macOS resource fork files (._filename)
        ts_files = sorted([f for f in output_path.glob("*.ts") if not f.name.startswith('._')])
        
        if not ts_files:
            print(f"No .ts files found in {self.output_directory}")
            input("Press Enter to continue...")
            return
        
        print(f"\nFound {len(ts_files)} .ts file(s) to compress:\n")
        for i, ts_file in enumerate(ts_files, 1):
            file_size = ts_file.stat().st_size / (1024 * 1024 * 1024)  # GB
            print(f"{i}. {ts_file.name} ({file_size:.2f} GB)")
        
        print("\nCompress Options:")
        print("1. Compress all files")
        print("2. Select specific files")
        print("3. Cancel")
        
        choice = input("\nEnter your choice (1-3): ").strip()
        
        selected_files = []
        
        if choice == '1':
            selected_files = ts_files
        elif choice == '2':
            file_nums = input("\nEnter file numbers separated by commas (e.g., 1,2,3): ").strip()
            try:
                indices = [int(x.strip()) - 1 for x in file_nums.split(',')]
                selected_files = [ts_files[i] for i in indices if 0 <= i < len(ts_files)]
                if not selected_files:
                    print("No valid files selected.")
                    input("Press Enter to continue...")
                    return
            except (ValueError, IndexError):
                print("Invalid input.")
                input("Press Enter to continue...")
                return
        elif choice == '3':
            return
        else:
            print("Invalid choice.")
            input("Press Enter to continue...")
            return
        
        # Use default compression settings from config
        crf = self.default_crf
        preset = self.default_preset
        
        # Create compressed directory if it doesn't exist
        compressed_path = Path(self.compressed_directory)
        try:
            compressed_path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            print(f"Error creating compressed directory: {e}")
            input("Press Enter to continue...")
            return
        
        print(f"\nWill compress {len(selected_files)} file(s) to: {self.compressed_directory}")
        print(f"Quality settings: CRF={crf}, preset={preset} (change in Settings menu if needed)")
        
        auto_delete = False
        auto_yes = False
        if not dry_run:
            auto_delete = input("\nAutomatically delete original .ts files after successful compression? [y/N]: ").strip().lower()
            auto_yes = auto_delete in ['y', 'yes']
        
        # Check for ffmpeg
        if not compress_module.check_ffmpeg_installed():
            print("\n[ERROR] ffmpeg and ffprobe are required but not found on PATH")
            print("Install with: brew install ffmpeg (macOS) or apt-get install ffmpeg (Linux)")
            input("\nPress Enter to continue...")
            return
        
        if dry_run:
            print("\n[DRY RUN MODE] - No files will be compressed or modified")
            print("="*60)
        else:
            print("\nStarting compression process...")
            self.console.print("[bold yellow]Press Ctrl+C at any time to interrupt (partial files will be cleaned up)[/bold yellow]")
            self.console.print("[bold yellow]Keyboard input is disabled during compression - only Ctrl+C will stop the process[/bold yellow]\n")
        
        stats = compress_module.CompressStats()
        stats.total_found = len(selected_files)
        
        try:
            for ts_file in selected_files:
                if compress_module.interrupted:
                    print("\n[WARNING] Processing interrupted by user")
                    break
                
                output_file = compressed_path / ts_file.with_suffix('.mp4').name
                
                # Check if already exists and valid
                if compress_module.mp4_exists_and_valid(output_file):
                    print(f"[INFO] Skipping {ts_file.name} - valid MP4 already exists")
                    stats.skipped_existing += 1
                    
                    # If user wants auto-delete, delete the original .ts file
                    # since compression was already done previously
                    if auto_yes:
                        try:
                            ts_file.unlink()
                            print(f"[INFO] Deleted original: {ts_file.name}")
                            stats.deleted += 1
                        except Exception as e:
                            print(f"[WARNING] Failed to delete {ts_file.name}: {e}")
                    else:
                        print(f"[INFO] Kept original: {ts_file.name}")
                    
                    continue
                
                if dry_run:
                    # Dry run mode - just show what would be done
                    print(f"[DRY RUN] Would compress: {ts_file.name}")
                    print(f"[DRY RUN]   Input:  {ts_file}")
                    print(f"[DRY RUN]   Output: {output_file}")
                    print(f"[DRY RUN]   Settings: CRF={crf}, preset={preset}")
                    input_size = ts_file.stat().st_size / (1024 * 1024 * 1024)
                    print(f"[DRY RUN]   Input size: {input_size:.2f} GB")
                    if auto_yes:
                        print(f"[DRY RUN]   Would delete original after compression")
                    print()
                    stats.processed += 1
                    stats.succeeded += 1
                    continue
                
                print(f"[PROGRESS] Processing: {ts_file.name}")
                print(f"[INFO] Compressing {ts_file.name} -> {output_file.name}")
                print(f"[INFO] Using CRF={crf}, preset={preset}")
                
                if not compress_module.compress_file(ts_file, output_file, allow_video_only=False, crf=crf, preset=preset):
                    if compress_module.interrupted:
                        print("\n[WARNING] Compression interrupted")
                        break
                    print(f"[ERROR] Compression failed for {ts_file.name}")
                    stats.failed += 1
                    stats.errors.append((ts_file.name, "Compression failed"))
                    continue
                
                print(f"[INFO] Verifying {output_file.name}")
                success, message = compress_module.verify_compression(ts_file, output_file)
                
                if not success:
                    print(f"[ERROR] Verification failed for {output_file.name}: {message}")
                    stats.failed += 1
                    stats.errors.append((ts_file.name, message))
                    continue
                
                print(f"[SUCCESS] Successfully compressed and verified: {output_file.name}")
                stats.succeeded += 1
                stats.processed += 1
                
                # Handle deletion
                if auto_yes:
                    try:
                        ts_file.unlink()
                        print(f"[INFO] Deleted original: {ts_file.name}")
                        stats.deleted += 1
                    except Exception as e:
                        print(f"[WARNING] Failed to delete {ts_file.name}: {e}")
                else:
                    print(f"[INFO] Kept original: {ts_file.name}")
                
                print()  # Blank line between files
        
        except KeyboardInterrupt:
            print("\n[WARNING] Operation cancelled by user")
        
        # Print summary
        print("\n" + "="*60)
        if dry_run:
            print("Dry Run Summary (No files were modified)")
        else:
            print("Compression Summary")
        print("="*60)
        print(f"Total .ts files found: {stats.total_found}")
        print(f"Skipped (valid MP4 exists): {stats.skipped_existing}")
        if dry_run:
            print(f"Would process: {stats.processed}")
        else:
            print(f"Processed: {stats.processed}")
            print(f"Succeeded: {stats.succeeded}")
            print(f"Failed: {stats.failed}")
            print(f"Originals deleted: {stats.deleted}")
        
        if stats.errors:
            print("\nErrors:")
            for filename, error in stats.errors:
                print(f"  - {filename}: {error}")
        
        print("="*60)
        input("\nPress Enter to continue...")

    def manage_streamers_menu(self):
        """Submenu for managing streamers"""
        while True:
            self.clear_screen()
            print("\n--- Manage Streamers ---")
            print("1. Add Streamer")
            print("2. Remove Streamer")
            print("3. List Monitored Streamers")
            print("q. Back to Main Menu")

            choice = input("Enter your choice (1-3, q): ").strip().lower()

            self.clear_screen()

            if choice == '1':
                self.add_streamer()
            elif choice == '2':
                self.remove_streamer()
            elif choice == '3':
                print("\nCurrently Monitored Streamers:")
                for streamer in self.streamers:
                    print(streamer)
                input("Press Enter to continue...")
            elif choice == 'q':
                break
            else:
                print("Invalid choice. Please try again.")
                input("Press Enter to continue...")

    def menu(self):
        """Main menu for stream recorder"""
        while True:
            # Clear screen
            self.clear_screen()

            print("\n--- Twitch Stream Recorder ---")
            print("1. Manage Streamers")
            print("2. Start Monitoring")
            print("3. Compress Recordings to MP4 (H.265)")
            print("4. Dry Run Compression (Preview)")
            print("5. Settings")
            print("q. Exit")

            choice = input("Enter your choice (1-5, q): ").strip().lower()

            # Clear screen after choice
            self.clear_screen()

            if choice == '1':
                self.manage_streamers_menu()
            elif choice == '2':
                self.start_monitoring()
            elif choice == '3':
                self.compress_recordings()
            elif choice == '4':
                self.compress_recordings(dry_run=True)
            elif choice == '5':
                self.change_settings()
            elif choice == 'q':
                print("Exiting Twitch Stream Recorder.")
                break
            else:
                print("Invalid choice. Please try again.")
                input("Press Enter to continue...")

def main():
    recorder = StreamRecorder()

    # First-time headless setup: prompt user if running interactively; otherwise default to headless.
    try:
        if 'run_headless' not in recorder.config:
            if sys.stdin.isatty():
                ans = input("First-time setup: run in headless mode (no interactive menu)? [y/N]: ").strip().lower()
                recorder.run_headless = ans in ('y', 'yes')
            else:
                recorder.run_headless = True
                recorder.logger.info("No TTY detected; defaulting to headless mode.")

            recorder.config['run_headless'] = recorder.run_headless
            recorder.save_config()
    except Exception as e:
        try:
            recorder.logger.exception(f"Error during first-time headless setup: {e}")
        except Exception:
            print(f"Error during first-time headless setup: {e}")
        # Fail safe to headless
        recorder.run_headless = True

    if recorder.run_headless:
        if not recorder.streamers:
            recorder.logger.info("Headless mode requested but no streamers configured. Exiting.")
            print("No streamers configured for headless mode. Please add streamers or run interactively.")
            return

        # Start monitoring all configured streamers (cap at 5)
        selected = recorder.streamers[:5]
        recorder.logger.info("Starting headless monitoring for %d streamer(s): %s", len(selected), ",".join(selected))
        recorder.monitor_multiple_streamers(selected, recorder.default_check_interval)
    else:
        recorder.menu()

if __name__ == "__main__":
    main()