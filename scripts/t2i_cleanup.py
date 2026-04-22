import time
import os
import sys

def cleanup(file_path, delay=150):
    """
    Wait for the specified delay and then remove the file.
    This ensures the Gateway has enough time to upload the file to Telegram.
    """
    try:
        print(f"[Disk Hygiene] Cleanup process started. Waiting {delay}s before removing: {file_path}")
        time.sleep(delay)
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"[Disk Hygiene] Successfully removed: {file_path}")
        else:
            print(f"[Disk Hygiene] File already gone: {file_path}")
    except Exception as e:
        print(f"[Disk Hygiene] Error during cleanup: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Error: No file path provided for cleanup.")
        sys.exit(1)
    
    path = sys.argv[1]
    # Default delay is 150s, can be overridden by 2nd argument
    delay_val = int(sys.argv[2]) if len(sys.argv) > 2 else 150
    cleanup(path, delay_val)
