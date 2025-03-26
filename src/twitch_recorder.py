import time
import subprocess
import json
from datetime import datetime
import os
import sys
import signal

class GracefulExit:
    """Manages graceful shutdown of the script"""
    def __init__(self):
        self.recording_process = None
        self.exit_now = False
        
        # Set up signal handlers
        signal.signal(signal.SIGINT, self.exit_gracefully)
        signal.signal(signal.SIGTERM, self.exit_gracefully)

    def set_recording_process(self, process):
        """Set the current recording process"""
        self.recording_process = process

    def exit_gracefully(self, signum=None, frame=None):
        """Handle interrupt signals"""
        print("\n\n--- Interrupt received ---")
        print("Shutting down gracefully...")
        
        # Terminate the recording process if it exists
        if self.recording_process:
            try:
                print("Stopping current recording...")
                self.recording_process.terminate()
                
                # Give the process a moment to terminate
                try:
                    self.recording_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    print("Force killing the recording process...")
                    self.recording_process.kill()
                
                print("Recording stopped successfully.")
            except Exception as e:
                print(f"Error stopping recording: {e}")
        
        # Set exit flag
        self.exit_now = True
        
        # Exit the script
        sys.exit(0)

def is_stream_live(channel_name):
    """Check if a Twitch channel is currently live."""
    try:
        # Use streamlink to check stream info
        result = subprocess.run(
            f"streamlink --json https://twitch.tv/{channel_name}",
            shell=True,
            capture_output=True,
            text=True
        )
        
        # Parse the JSON output
        stream_info = json.loads(result.stdout)
        
        # If the stream is available, it's live
        return stream_info.get('streams') is not None and len(stream_info.get('streams')) > 0
    except Exception as e:
        print(f"Error checking if stream is live: {e}")
        return False

def check_and_record(channel_name):
    """Check if a channel is live and record it if it is."""
    # Create graceful exit handler
    exit_handler = GracefulExit()
    
    print(f"Starting monitoring for Twitch channel: {channel_name}")
    print("Press Ctrl+C to stop the script at any time.")
    
    currently_recording = False
    recording_process = None
    
    while not exit_handler.exit_now:
        try:
            # Check if the stream is live
            if is_stream_live(channel_name):
                if not currently_recording:
                    print(f"[{datetime.now()}] {channel_name} is now live! Starting recording...")
                    
                    # Create a 'recordings' directory if it doesn't exist
                    os.makedirs('recordings', exist_ok=True)
                    
                    # Format filename with timestamp
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    output_file = os.path.join('recordings', f"{channel_name}_{timestamp}.ts")
                    
                    # Start the recording process
                    command = f"streamlink https://twitch.tv/{channel_name} best -o {output_file}"
                    recording_process = subprocess.Popen(command, shell=True)
                    
                    # Set the recording process for graceful shutdown
                    exit_handler.set_recording_process(recording_process)
                    
                    currently_recording = True
                    print(f"Recording to file: {output_file}")
            else:
                if currently_recording:
                    print(f"[{datetime.now()}] {channel_name} is no longer live. Stopping recording...")
                    
                    # Terminate the recording process
                    if recording_process:
                        recording_process.terminate()
                        recording_process = None
                    
                    currently_recording = False
                else:
                    print(f"[{datetime.now()}] {channel_name} is not live. Checking again in 5 minutes...")
            
        except Exception as e:
            print(f"Error in main loop: {e}")
            if recording_process:
                try:
                    recording_process.terminate()
                except:
                    pass
                recording_process = None
                currently_recording = False
        
        # Wait before checking again
        time.sleep(300)  # 5 minutes

def main():
    # Replace 'streamer_name' with the Twitch username of the streamer you want to record
    channel_name = input("Enter the Twitch channel name to monitor: ")
    check_and_record(channel_name)

if __name__ == "__main__":
    main()