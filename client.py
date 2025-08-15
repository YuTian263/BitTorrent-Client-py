import time 
import threading 
import hashlib
import os
from torrent import TorrentFile
from tracker import TrackerClient
from peer import PeerConnection

class BitTorrentClient: 
    def __init__(self,torrent_file): 
        self.torrent = TorrentFile(torrent_file)
        self.tracker = TrackerClient(self.torrent)

        # peer management 
        self.peers = {} 
        self.max_peer = 50 

        # download state 
        self.downloaded_pieces = set() 
        self.piece_data = {}
        self.downloading_pieces = set()
        self.completed_pieces = set()
        self.output_file = None

        #statistics 
        self.upload = 0 
        self.download = 0 

        # control 
        self.running = False 
        self.tracker_thread = None 
        self.download_thread = None 

    def start(self): 
        # start Bittorrent Client 
        print(f"start BitTorrent client for {self.torrent.name}")
        self.running = True 

        # start tracker updates 
        self.tracker_thread = threading.Thread(target= self.tracker_loop)
        self.tracker_thread.daemon = True 
        self.tracker_thread.start()

        # start download coordination 
        self.download_thread = threading.Thread(target = self.download_loop)
        self.download_thread.daemon = True 
        self.download_thread.start() 

        # Initialize output file
        self.output_file = open(self.torrent.name, 'wb')

        # Pre-allocate file space
        self.output_file.seek(self.torrent.length - 1)
        self.output_file.write(b'\0')
        self.output_file.flush()

        print("BitTorrent client started")
    
    def tracker_loop(self): 
        #periodically contact tracker for new peers
        while self.running: 
            try: 
                left = self.torrent.length - self.download
                peers, interval = self.tracker.announce(
                    uploaded= self.upload,
                    downloaded= self.download,
                    left = left
                )

                # connect to new peers 
                for ip, port in peers: 
                    peer_key = f"{ip}:{port}"
                    if peer_key not in self.peers and len(self.peers) < self.max_peer : 
                        peer = PeerConnection(ip, port, self.torrent, self.tracker.peer_id)
                        if peer.connect(): 
                            self.peers[peer_key] = peer 
                            peer.send_interested()
                #wait for the next tracker
                time.sleep(min(interval,300))
            except Exception as e: 
                print(f"Tracker loop error: {e}")
                time.sleep(60) # wait 1 min on error 

    def download_loop(self): 
        #corrdinate piece downloading 
        while self.running: 
            try: 
                #finding pieces to donwload 
                available_pieces = self.find_available_pieces()
                for piece_index in available_pieces: 
                    if piece_index not in self.downloaded_pieces and piece_index not in self.downloading_pieces: 
                        # find the peer with this piece 
                        peer = self._find_peer_with_piece(piece_index)
                        if peer: 
                            self._download_piece(peer,piece_index)
                time.sleep(1)
            except Exception as e: 
                print(f"download loop error: {e}")
                time.sleep(3)
    def find_available_pieces(self): 
        #find availble pieces from peers 
        available = set()
        for peer in self.peers.values():
            if peer.connected and peer.handshake : 
                available.update(peer.peer_pieces)
        return available
    
    def _find_peer_with_piece(self, piece_index):
        #find a peer that has the piece and isn't choking us 
        candidates = []
        for peer in self.peers.values(): 
            if (peer.has_piece(piece_index)and not peer.peer_choking and peer.connected and peer.handshake):
                candidates.append(peer)
        if candidates: 
            return min(candidates,key=lambda p: len(p.pending_request))
        return None 
    
    def _download_piece(self,peer,piece_index): 
        #download a complete piece from a peer
        self.downloading_pieces.add(piece_index)
        piece_size = self.torrent.get_pieces_size(piece_index)
        block_size = 16384 

        #request all the blocks for this piece 
        for offset in range(0, piece_size, block_size): 
            length = min (block_size, piece_size -offset)
            peer.request_piece (piece_index, offset, length)
        print(f"Started downloading piece {piece_index}")
    
    def piece_completed(self, piece_index, piece_data):
        """Handle a completed piece"""
        if piece_index not in self.completed_pieces:
            self.completed_pieces.add(piece_index)
            self.downloading_pieces.discard(piece_index)
            
            # Write piece to file
            if self.output_file:
                offset = piece_index * self.torrent.piece_length
                self.output_file.seek(offset)
                self.output_file.write(piece_data)
                self.output_file.flush()
            
            print(f"Piece {piece_index} written to file")

    def verify_piece(self, piece_index, data):
        """Verify a piece against its hash"""
        expected_hash = self.torrent.pieces_hash[piece_index]
        actual_hash = hashlib.sha1(data).digest()
        return expected_hash == actual_hash
    
    def get_progress(self):
        """Get download progress"""
        return len(self.completed_pieces) / self.torrent.num_pieces
    
    def stop(self):
        """Stop the BitTorrent client"""
        print("Stopping BitTorrent client...")
        self.running = False
        
        # Close all peer connections
        for peer in list(self.peers.values()):
            peer.close()
        
        # Send stop event to tracker
        try:
            self.tracker.announce(
                uploaded=self.upload,
                downloaded=self.download,
                left=self.torrent.length - self.download,
                event='stopped'
            )
        except:
            pass
        
        # Close output file
        if self.output_file:
            self.output_file.close()

