#!/usr/bin/python
"""Config file for deviceremotes.

Import device classes, then define entries in REMOTES as:
   (CLASS, ID, HOST, PORT)
"""
import deviceremotes

REMOTES = [
	(deviceremotes.Remote, None, '127.0.0.1', 8000),
]
