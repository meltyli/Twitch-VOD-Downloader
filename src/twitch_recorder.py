import time
import subprocess
import json
from datetime import datetime
import os
import sys
import signal
import threading
import queue
import concurrent.futures
import platform

class StreamRecorder:
    def __init__(self, config_file='streamers.json'):
        self.config_file = config_file
        self.streamers = self.load_streamers()
        self.exit_event = threading.Event()
        self.recording_processes = {}
        self.recording_lock = threading.Lock()
        self.monitor_threads = []

    def clear_screen(self):
        """Clear the terminal screen across different platforms"""
        system = platform.system().lower()
        if system == 'windows':
            os.system('cls')
        else:
            os.system('clear')

    def load_streamers(self):
        """Load list of streamers from JSON file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            return []
        except Exception as e:
            print(f"Error loading streamers: {e}")
            return []

    def save_streamers(self):
        """Save list of streamers to JSON file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.streamers, f, indent=4)
        except Exception as e:
            print(f"Error saving streamers: {e}")

    def is_stream_live(self, channel_name):
        """Check if a Twitch channel is currently live."""
        try:
            result = subprocess.run(
                f"streamlink --json https://twitch.tv/{channel_name}",
                shell=True,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            stream_info = json.loads(result.stdout)
            return stream_info.get('streams') is not None and len(stream_info.get('streams')) > 0
        except Exception as e:
            print(f"Error checking if {channel_name} is live: {e}")
            return False

    def record_stream(self, channel_name):
        """Record a single stream"""
        try:
            # Create recordings directory if it doesn't exist
            os.makedirs('recordings', exist_ok=True)
            
            # Format filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = os.path.join('recordings', f"{channel_name}_{timestamp}.ts")
            
            # Start recording
            print(f"[{datetime.now()}] Recording {channel_name}'s stream to {output_file}")
            
            # Use subprocess to start recording
            command = f"streamlink https://twitch.tv/{channel_name} best -o {output_file}"
            process = subprocess.Popen(command, shell=True)
            
            # Store the process
            with self.recording_lock:
                self.recording_processes[channel_name] = process
            
            return process
        except Exception as e:
            print(f"Error recording {channel_name}'s stream: {e}")
            return None

    def monitor_stream(self, streamer):
        """Monitor a single streamer"""
        while not self.exit_event.is_set():
            try:
                # Check if stream is live
                if self.is_stream_live(streamer):
                    # Check if not already recording
                    with self.recording_lock:
                        if streamer not in self.recording_processes:
                            self.record_stream(streamer)
                else:
                    # If was recording, stop recording
                    with self.recording_lock:
                        if streamer in self.recording_processes:
                            try:
                                process = self.recording_processes[streamer]
                                process.terminate()
                                del self.recording_processes[streamer]
                                print(f"{streamer}'s stream has ended.")
                            except Exception as e:
                                print(f"Error stopping {streamer}'s recording: {e}")
            except Exception as e:
                print(f"Error monitoring {streamer}: {e}")
            
            # Wait before next check
            if self.exit_event.wait(300):  # 5 minutes between checks
                break

    def start_monitoring(self):
        """Start monitoring all streamers"""
        if not self.streamers:
            print("No streamers to monitor.")
            input("Press Enter to continue...")
            return

        print("\n--- Starting Stream Monitoring ---")
        print(f"Monitoring {len(self.streamers)} streamers")

        # Reset exit event
        self.exit_event.clear()

        # Create a thread for each streamer using ThreadPoolExecutor
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(self.streamers)) as executor:
            # Submit monitoring tasks for each streamer
            futures = {executor.submit(self.monitor_stream, streamer): streamer for streamer in self.streamers}

            # Wait for user to stop or for streams to end
            try:
                print("Monitoring started. Press Ctrl+C to stop...\n")
                # Wait indefinitely 
                while not self.exit_event.is_set():
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\nStopping monitoring...")
                self.exit_event.set()

        # Stop monitoring
        self.stop_monitoring()

    def stop_monitoring(self):
        """Stop all monitoring threads and recording processes"""
        # Set exit event to stop threads
        self.exit_event.set()

        # Terminate all recording processes
        with self.recording_lock:
            for streamer, process in list(self.recording_processes.items()):
                try:
                    process.terminate()
                    process.wait(timeout=5)  # Wait for process to end
                    del self.recording_processes[streamer]
                except subprocess.TimeoutExpired:
                    print(f"Force terminating {streamer}'s recording")
                    process.kill()
                except Exception as e:
                    print(f"Error terminating {streamer}'s recording: {e}")

        print("Monitoring stopped.")
        input("Press Enter to continue...")

    def add_streamer(self, streamer):
        """Add a new streamer to monitor"""
        streamer = streamer.strip().lower()
        if streamer and streamer not in self.streamers:
            self.streamers.append(streamer)
            self.save_streamers()
            print(f"Added {streamer} to monitored streamers.")
        else:
            print("Streamer already exists or invalid name.")
        
        input("Press Enter to continue...")

    def remove_streamer(self, streamer):
        """Remove a streamer from monitoring"""
        streamer = streamer.strip().lower()
        if streamer in self.streamers:
            # Stop recording if currently recording
            with self.recording_lock:
                if streamer in self.recording_processes:
                    try:
                        self.recording_processes[streamer].terminate()
                        del self.recording_processes[streamer]
                    except:
                        pass
            
            self.streamers.remove(streamer)
            self.save_streamers()
            print(f"Removed {streamer} from monitored streamers.")
        else:
            print("Streamer not found in the list.")
        
        input("Press Enter to continue...")

    def menu(self):
        """Main menu for stream recorder"""
        while True:
            # Clear screen
            self.clear_screen()

            print("\n--- Twitch Stream Recorder ---")
            print("1. Add Streamer")
            print("2. Remove Streamer")
            print("3. List Monitored Streamers")
            print("4. Start Monitoring")
            print("5. Exit")
            
            choice = input("Enter your choice (1-5): ")
            
            # Clear screen after choice
            self.clear_screen()
            
            if choice == '1':
                streamer = input("Enter Twitch username to add: ")
                self.add_streamer(streamer)
            elif choice == '2':
                streamer = input("Enter Twitch username to remove: ")
                self.remove_streamer(streamer)
            elif choice == '3':
                print("\nCurrently Monitored Streamers:")
                for streamer in self.streamers:
                    print(streamer)
                input("Press Enter to continue...")
            elif choice == '4':
                if not self.streamers:
                    print("No streamers added. Please add streamers first.")
                    input("Press Enter to continue...")
                    continue
                
                # Start monitoring
                self.start_monitoring()
            elif choice == '5':
                print("Exiting Twitch Stream Recorder.")
                break
            else:
                print("Invalid choice. Please try again.")
                input("Press Enter to continue...")

def main():
    recorder = StreamRecorder()
    recorder.menu()

if __name__ == "__main__":
    main()