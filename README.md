# BitTorrent-Client-py

A simple BitTorrent Client implemenation using python 

## File Structure: 
- bencode.py : Handles the bencode encoding and decoding for the torrent file 
- torrent.py : Parses torrent file and handles the metadata 
- tracker.py : Manage indivisual peer connections and BitTorrent protocol 
- peer.py : Handles peer-to-peer connections, BitTorrent protocol message, and piece downloading 
- client.py : Main BitTorrent client that corrdinates tracker communication, peer management and downloading progess 
- main.py: Entry point script that starts the BitTorrent client and handles command-line arguments

## Usage 

to run the client: 

```bash
python main.py filename.torrent 

```
can stop the client by using `Ctrl + C` 

## Features implemented 
-Torrent file parsing
-Tracker communication
-Peer discovery and connection
-Basic piece downloading 
-Progress monitoring 

