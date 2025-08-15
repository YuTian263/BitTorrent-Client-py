import sys
import time
from client import BitTorrentClient

def main(): 
    if len(sys.argv) != 2: 
        print("Usage: python main.py <torrent_file>")
        sys.exit(1)
    torrent_file = sys.argv[1]
    try:
        # Create and start client
        client = BitTorrentClient(torrent_file)
        client.start()
        
        # Monitor progress
        print("Starting download... Press Ctrl+C to stop")
        try:
            while client.running:
                progress = client.get_progress()
                print(f"Progress: {progress:.1%} - Peers: {len(client.peers)}")
                time.sleep(10)
        except KeyboardInterrupt:
            print("\nShutting down...")
        
        # Clean shutdown
        client.stop()
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()