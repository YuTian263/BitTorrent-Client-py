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

        params = {
            'info_hash': self.torrent.info_hash,
            'peer_id': self.peer_id,
            'port': str(self.port),
            'uploaded': str(uploaded), 
            'downloaded': str(downloaded), 
            'left': str(left),
            'event': event,
            'compact': '1' 
        }

        # Build query string with proper URL encoding
        query_parts = []
        for key, value in params.items():
            if isinstance(value, bytes):
                encoded_value = urllib.parse.quote(value, safe='')
            else:
                encoded_value = urllib.parse.quote(str(value), safe='')
            query_parts.append(f"{key}={encoded_value}")
        
        query = "&".join(query_parts)
        url = f"{announce_url}?{query}"
        
        print(f"Tracker URL: {url}")
        
        try: 
            request = urllib.request.Request(url)
            request.add_header('User-Agent', 'BitTorrent/1.0')
            response = urllib.request.urlopen(request, timeout=30)
            response_data = Bencode.decode(response.read())
            
            print(f"Tracker response keys: {list(response_data.keys())}")
            print(f"Tracker response: {response_data}")

            # Handle response keys as bytes or strings
            failure_key = b'failure reason' if b'failure reason' in response_data else 'failure reason'
            peers_key = b'peers' if b'peers' in response_data else 'peers'
            interval_key = b'interval' if b'interval' in response_data else 'interval'

            # Check for failure reason first
            if failure_key in response_data:
                failure_reason = response_data[failure_key]
                if isinstance(failure_reason, bytes):
                    failure_reason = failure_reason.decode('utf-8')
                raise Exception(f"Tracker error: {failure_reason}")
            
            # Check for peers
            if peers_key not in response_data:
                print(f"Available keys: {list(response_data.keys())}")
                raise Exception("Tracker response missing 'peers' field")
            
            peers = self._parse_peers(response_data[peers_key])
            interval = response_data.get(interval_key, 1800)

            print(f"Found {len(peers)} peers from tracker ")
            return peers, interval
        except Exception as e: 
            print(f"Tracker request failed: {e}")
            return [], 1800
    
    def _parse_peers(self, peers_data): 
        peers = [] 
        if isinstance(peers_data, list):
            # Dictionary format (non-compact)
            for peer_dict in peers_data:
                ip_key = b'ip' if b'ip' in peer_dict else 'ip'
                port_key = b'port' if b'port' in peer_dict else 'port'
                ip = peer_dict.get(ip_key, b'').decode() if isinstance(peer_dict.get(ip_key, ''), bytes) else peer_dict.get(ip_key, '')
                port = peer_dict.get(port_key, 0)
                peers.append((ip, port))
        else:
            # Compact format (binary)
            for i in range(0, len(peers_data), 6): 
                ip_bytes = peers_data[i:i+4]
                port_bytes = peers_data[i+4:i+6]
                ip = '.'.join(str(b) for b in ip_bytes)
                port = struct.unpack('>H', port_bytes)[0]
                peers.append((ip, port))
        return peers