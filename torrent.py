import hashlib 
from bencode import Bencode

class TorrentFile: 
    def __init__(self, file): 
        with open(file,'rb')as f: 
            self.data = Bencode.decode(f.read())
        self.announce = self.data['announce']
        self.info = self.data['info']
        self.name = self.info['name']
        self.piece_length = self.info['piece length']
        self.pieces = self.info['pieces']
        
        # Handle single-file vs multi-file torrents
        if 'length' in self.info:
            self.length = self.info['length']
        elif 'files' in self.info:
            self.length = sum(f['length'] for f in self.info['files'])
        else:
            raise ValueError("Invalid torrent: no length or files field")

        self.info_hash = hashlib.sha1(Bencode.encode(self.info)).digest() 

        self.pieces_hash = []
        for i in range(0,len(self.pieces), 20): 
            self.pieces_hash.append(self.pieces[i:i+20])

        self.num_pieces = len(self.pieces_hash)
        print(f"load torrent file{self.name}")
        print(f'Pieces: {self.num_pieces}, Piece Length: {self.piece_length}')
    
    def get_pieces_size(self, piece_index): 
        if piece_index == len(self.pieces_hash) -1: 
            return self.length % self.piece_length or self.piece_length
        return self.piece_length
    