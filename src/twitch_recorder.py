import time
import subprocess
import json
from datetime import datetime
import os
import sys
import signal
import json
import threading

class StreamRecorder:
    def __init__(self, config_file='streamers.json'):
        self.config_file = config_file
        self.streamers = self.load_streamers()
        self.exit_flag = False
        self.recording_processes = {}

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
            self.recording_processes[channel_name] = process
            
            return process
        except Exception as e:
            print(f"Error recording {channel_name}'s stream: {e}")
            return None

    def monitor_streams(self):
        """Monitor all added streamers"""
        print("\n--- Starting Stream Monitoring ---")
        print(f"Monitoring {len(self.streamers)} streamers")
        
        while not self.exit_flag:
            # Check which streamers are live
            live_streams = []
            for streamer in self.streamers:
                if self.is_stream_live(streamer):
                    live_streams.append(streamer)
            
            # Record live streams
            for streamer in live_streams:
                if streamer not in self.recording_processes:
                    self.record_stream(streamer)
            
            # Wait before next check
            time.sleep(300)  # 5 minutes between checks

    def add_streamer(self, streamer):
        """Add a new streamer to monitor"""
        streamer = streamer.strip().lower()
        if streamer and streamer not in self.streamers:
            self.streamers.append(streamer)
            self.save_streamers()
            print(f"Added {streamer} to monitored streamers.")
        else:
            print("Streamer already exists or invalid name.")

    def remove_streamer(self, streamer):
        """Remove a streamer from monitoring"""
        streamer = streamer.strip().lower()
        if streamer in self.streamers:
            # Stop recording if currently recording
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

    def menu(self):
        """Main menu for stream recorder"""
        while True:
            print("\n--- Twitch Stream Recorder ---")
            print("1. Add Streamer")
            print("2. Remove Streamer")
            print("3. List Monitored Streamers")
            print("4. Start Monitoring")
            print("5. Exit")
            
            choice = input("Enter your choice (1-5): ")
            
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
            elif choice == '4':
                if not self.streamers:
                    print("No streamers added. Please add streamers first.")
                    continue
                
                # Start monitoring in a separate thread
                monitor_thread = threading.Thread(target=self.monitor_streams)
                monitor_thread.start()
                
                # Wait for user to stop
                input("Monitoring started. Press Enter to stop...\n")
                
                # Set exit flag and wait for thread to finish
                self.exit_flag = True
                monitor_thread.join()
                
                # Reset exit flag for potential future monitoring
                self.exit_flag = False
                
                # Terminate any ongoing recordings
                for streamer, process in list(self.recording_processes.items()):
                    try:
                        process.terminate()
                        del self.recording_processes[streamer]
                    except:
                        pass
            elif choice == '5':
                print("Exiting Twitch Stream Recorder.")
                break
            else:
                print("Invalid choice. Please try again.")

def main():
    recorder = StreamRecorder()
    recorder.menu()

if __name__ == "__main__":
    main()