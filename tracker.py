import random 
import struct 
import urllib.parse 
import urllib.request
from bencode import Bencode

class TrackerClient: 
    def __init__(self, torrent): 
        self.torrent = torrent 
        self.peer_id = self._generate_peer_id() 
        self.port = 6681 
    
    def _generate_peer_id(self): 
        return b'-PC0001-' + bytes([random.randint(0, 255) for _ in range(12)])
    
    def announce(self, uploaded = 0, downloaded = 0, left = None, event= 'started'): 
        if left is None: 
            left = self.torrent.length 

        # Ensure announce URL is a string
        announce_url = self.torrent.announce
        if isinstance(announce_url, bytes):
            announce_url = announce_url.decode('utf-8')

        param = {
            'peer_id' : self.peer_id,
            'port': self.port,
            'uploaded': uploaded, 
            'downloaded' : downloaded, 
            'left': left,
            'event' : event,
            'compact' : 1 
        }

        # Build query string manually to handle info_hash properly
        query_parts = []
        for key, value in param.items():
            if isinstance(value, bytes):
                query_parts.append(f"{key}={value}")
            else:
                query_parts.append(f"{key}={value}")
        
        # Add info_hash separately (it's raw bytes)
        query_parts.append(f"info_hash={self.torrent.info_hash}")
        
        query = "&".join(query_parts)
        url = f"{announce_url}?{query}"
        
        print(f"Tracker URL: {url}")
        
        try: 
            response = urllib.request.urlopen(url, timeout=10)
            response_data = Bencode.decode(response.read())
            
            print(f"Tracker response keys: {list(response_data.keys())}")
            print(f"Tracker response: {response_data}")

            # Check for failure reason first
            if b'failure reason' in response_data:
                failure_reason = response_data[b'failure reason']
                if isinstance(failure_reason, bytes):
                    failure_reason = failure_reason.decode('utf-8')
                print(f"Tracker error: {failure_reason}")
                return [], 1800  # Return empty peer list instead of throwing error
            
            # Only check for missing peers if there's no failure reason
            if b'peers' not in response_data:
                print(f"Available keys: {list(response_data.keys())}")
                # Check if it's a warning message
                if b'warning message' in response_data:
                    warning = response_data[b'warning message']
                    if isinstance(warning, bytes):
                        warning = warning.decode('utf-8')
                    print(f"Tracker warning: {warning}")
                print("Tracker response missing 'peers' field")
                return [], 1800  # Return empty peer list instead of throwing error
            
            peers = self._parse_peers(response_data[b'peers'])
            interval = response_data.get(b'interval',1800)

            print(f"Found {len(peers)} peers from tracker ")
            return peers, interval
        except Exception as e: 
            print(f"Tracker request failed: {e}")
            return [], 1800
    
    def _parse_peers(self, peers_data): 
        peers = [] 
        for i in range(0,len(peers_data), 6): 
            ip_bytes = peers_data[i:i+4]
            port_bytes = peers_data[i+4:i+6]
            ip = '.'.join(str(b)for b in ip_bytes)
            port = struct.unpack('>H',port_bytes)[0]
            peers.append((ip,port))
        return peers