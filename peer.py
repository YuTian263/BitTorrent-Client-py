import socket 
import struct 
import threading 
import time 
from torrent import * 

class PeerConnection:
    CHOKE = 0
    UNCHOKE = 1
    INTERESTED = 2
    NOT_INTERESTED = 3
    HAVE = 4
    BITFIELD = 5
    REQUEST = 6
    PIECE = 7
    CANCEL = 8

    def __init__(self, ip, port, torrent, peer_id): 
        self.ip = ip 
        self.port = port 
        self.torrent = torrent 
        self.peer_id = peer_id 
        self.socket = None 
        self.connected = False 
        self.handshake = False 

        #peer state 
        self.peer_choking = True 
        self.peer_interested = False
        self.am_chocking = True 
        self.am_interested = False 

        #pieces available 
        self.peer_pieces = set() 
        self.pending_request = {} 
        self.piece_blocks = {}  
         
         #threading 
        self.running = False 
        self.message_thread = None 

    def connect(self): 
        # connect to peer and perform handshake 
        try: 
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(10)
            self.socket.connect((self.ip, self.port))
            self.connected = True 

            #send handshake 
            handshake = self._build_handshake()
            self.socket.send(handshake)

            #receive handshake response 
            response = self.socket.recv(68)
            if len(response)== 68 and response[28:48]== self.torrent.info_hash: 
                self.handshake = True
                print(f"Handshake successful with {self.ip} : {self.port}")

                #message handling thread 
                self.running = True 
                self.message_thread = threading.Thread(target=self._handle_message )
                self.message_thread.daemon = True 
                self.message_thread.start()

                return True 
            else: 
                print(f'Handshake failed with {self.ip}: {self.port}')
                return False 
        except Exception as e: 
            print(f"Connection failed with {self.ip}: {self.port}: {e}")
            return False 
        
    def _build_handshake(self): 
        protocol = b"BitTorrent Protocol"
        pstrlen = len(protocol)
        reserved = b'\x00' *8 

        return struct.pack(f'B{pstrlen}s8s20s20s',pstrlen,protocol,reserved,self.torrent.info_hash, self.peer_id)
    
    def _handle_message(self): 
        #handle income message from peer 
        try: 
            while self.running and self.connected:
                #read message length
                length_data = self._recv_exact(4)
                if not length_data:
                    break 
                length = struct.unpack('!I', length_data)[0] 
                if length ==0: #keep message alive 
                    continue
                #read message 
                message_data = self._recv_exact(length)
                if not message_data:
                    break
                self._process_message(message_data)
        except Exception as e: 
            print(f"Message handling error for {self.ip}:{self.port}: {e}")
        finally:
            self.close()
    
    def _recv_exact(self,length):
        # receive exact length bytes 
        data = b''
        while len(data)< length: 
            chunk = self.socket.recv(length -len(data))
            if not chunk: 
                return None
            data += chunk
        return data 
    
    def _process_message(self,data): 
        #process a received message 
        message_id = data[0]
        payload = data[1:]
        if message_id == self.CHOKE: 
            self.peer_choking = True 
            print(f"Peer {self.ip}: {self.port} chocked us ")
        elif message_id == self.UNCHOKE: 
            self.peer_choking = False 
            print(f"Peer {self.ip}: {self.port} unchocked us")
        elif message_id == self.INTERESTED: 
            self.peer_interested = True 
        elif message_id == self.NOT_INTERESTED: 
            self.peer_interested = False 
        elif message_id == self.HAVE: 
            pieces_index = struct.unpack("!I", payload )[0]
            self.peer_pieces.add(pieces_index)
        elif message_id == self.BITFIELD:
            self._parse_bitfield(payload)
        elif message_id == self.PIECE:
            self._handle_piece_message(payload)
    
    def _parse_bitfield(self, bitfield): 
        # parse bitfield message to determine the peer's piece 
        for bytes_index , byte in enumerate(bitfield):
            for bit_index in range(8): 
                piece_index = bytes_index * 8 + bit_index
                if piece_index >= self.torrent.num_pieces: 
                    break 
                if byte & (0x80 >> bit_index): 
                    self.peer_pieces.add(piece_index)
            print(f"Peer {self.ip}:{self.port} has {len(self.peer_pieces)} pieces")
    
    def _handle_piece_message(self, payload): 
        # handle received piece data 
        piece_index, begin = struct.unpack('!II', payload[:8])
        block_data = payload[8:]
        request_key = (piece_index, begin)
        
        if request_key in self.pending_request: 
            print(f"Received block {piece_index}:{begin} from {self.ip}:{self.port}")
            del self.pending_request[request_key]
            
            # Store the block data
            if piece_index not in self.piece_blocks:
                self.piece_blocks[piece_index] = {}
            self.piece_blocks[piece_index][begin] = block_data
            
            # Check if piece is complete
            piece_size = self.torrent.get_pieces_size(piece_index)
            received_size = sum(len(data) for data in self.piece_blocks[piece_index].values())
            
            if received_size >= piece_size:
                self._complete_piece(piece_index)

    def send_message(self,message_id, payload = b''):
        #send message to peer 
        if not self.connected: 
            return False 
        try: 
            length = len(payload) + 1 
            message = struct.pack('!IB', length, message_id) + payload 
            self.socket.send(message)
            return True 
        except Exception as e: 
            print(f"Failed to send message {self.ip}: {self.port}:{e}")
            return False 
    
    def _complete_piece(self, piece_index):
        """Assemble and verify a complete piece"""
        # Sort blocks by offset and concatenate
        sorted_blocks = sorted(self.piece_blocks[piece_index].items())
        piece_data = b''.join(data for offset, data in sorted_blocks)
        
        # Verify hash
        import hashlib
        expected_hash = self.torrent.pieces_hash[piece_index]
        actual_hash = hashlib.sha1(piece_data).digest()
        
        if expected_hash == actual_hash:
            print(f"Piece {piece_index} completed and verified")
            # TODO: Signal to client that piece is complete
            # You'll need to add a callback mechanism here
        else:
            print(f"Piece {piece_index} hash verification failed")
        
        # Clean up
        del self.piece_blocks[piece_index]
        
    def send_interested(self): 
        # send interested message 
        if self.send_message(self.INTERESTED) : 
            self.am_interested = True 
            print(f"send interest to {self.ip}: {self.port}")
    
    def send_not_interested(self): 
        #send non interested message 
        if self.send_message(self.NOT_INTERESTED): 
            self.am_interested = False
         
    def request_piece(self,piece_index, begin, length): 
        # request a piece block from peer 
        if self.peer_choking or not self.handshake: 
            return False 
        payload = struct.pack('!III', piece_index, begin,length)
        if self.send_message(self.REQUEST, payload): 
            self.pending_request[(piece_index,begin)] = time.time()
            print(f"Requested piece {piece_index}:{begin} from {self.ip}:{self.port}")
            return True
        return False 
    
    def has_piece(self,piece_index): 
        #check if peer has specific piece 
        return piece_index in self.peer_pieces
    
    def close(self): 
        #close connections 
        self.running = False 
        if self.socket: 
            try: 
                self.socket.close() 
            except: 
                pass
        self.connected = False 
        print(f"Closed connection to {self.ip}: {self.port}")

