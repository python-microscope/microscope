#!/usr/bin/python
"""Config file for deviceremotes.

Import device classes, then define entries in REMOTES as:
   remote(CLASS, HOST, PORT, ID, other_args)
"""
# Function to create record for each remote.
from deviceremotes import remote
# Import device modules/classes here.
import deviceremotes

REMOTES = [
	remote(deviceremotes.Remote, '127.0.0.1', 8000),
	remote(deviceremotes.Remote, '127.0.0.1', 8001, com=6, baud=115200),
	remote(deviceremotes.FloatingRemote, '127.0.0.1', 8002, uid=None),
]
