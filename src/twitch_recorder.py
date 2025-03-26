iimport time
import subprocess
import json
from datetime import datetime
import os
import sys
import signal
import platform
import threading

class StreamRecorder:
    def __init__(self, config_file='streamers.json'):
        self.config_file = config_file
        self.streamers = self.load_streamers()
        self.current_process = None
        self.monitoring_thread = None
        self.stop_monitoring_event = threading.Event()

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
            # Create recordings directory if it doesn't exist
            os.makedirs('recordings', exist_ok=True)
            
            # Format filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = os.path.join('recordings', f"{channel_name}_{timestamp}.ts")
            
            # Start recording
            print(f"[{datetime.now()}] Recording {channel_name}'s stream to {output_file}")
            
            # Use subprocess to start recording
            command = f"streamlink https://twitch.tv/{channel_name} best -o {output_file}"
            self.current_process = subprocess.Popen(command, shell=True)
            
            # Wait for the process to complete or be interrupted
            try:
                print("Press Enter to stop recording...")
                input()  # This will block until Enter is pressed
                self.stop_recording()
            except KeyboardInterrupt:
                self.stop_recording()
        except Exception as e:
            print(f"Error recording {channel_name}'s stream: {e}")

    def stop_recording(self):
        """Stop the current recording"""
        if self.current_process:
            try:
                self.current_process.terminate()
                self.current_process.wait(timeout=5)
                print("Recording stopped.")
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
            self.save_streamers()
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
                self.save_streamers()
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

    def start_monitoring(self):
        """Start monitoring and allow user to choose a live streamer to record"""
        if not self.streamers:
            print("No streamers added. Please add streamers first.")
            input("Press Enter to continue...")
            return

        # Find live streamers
        live_streamers = self.find_live_streamers()

        if not live_streamers:
            print("\nThere aren't any live channels in your list.")
            periodic_check = input("Do you want to periodically check for streamers to go live? (y/n): ").lower()
            
            if periodic_check != 'y':
                return

            # Prompt for check interval
            while True:
                try:
                    check_interval = float(input("How frequently do you want to check for live streams (in minutes)? "))
                    if check_interval <= 0:
                        print("Please enter a positive number.")
                        continue
                    break
                except ValueError:
                    print("Please enter a valid number.")

            # Reset the stop event
            self.stop_monitoring_event.clear()

            # Start periodic checking in a separate thread
            self.monitoring_thread = threading.Thread(
                target=self.periodic_live_check, 
                args=(check_interval,)
            )
            self.monitoring_thread.start()

            print(f"\nPeriodically checking for live streamers every {check_interval} minutes.")
            print("Press Enter to stop checking...")
            input()

            # Stop the monitoring
            self.stop_monitoring_event.set()
            if self.monitoring_thread:
                self.monitoring_thread.join()

            return

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
                self.add_streamer()
            elif choice == '2':
                self.remove_streamer()
            elif choice == '3':
                print("\nCurrently Monitored Streamers:")
                for streamer in self.streamers:
                    print(streamer)
                input("Press Enter to continue...")
            elif choice == '4':
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