import argparse
import asyncio
import os
from PIL import Image
from websockets.sync.client import connect

TILE_SIZE = 20

def makePixelMessage(x, y, r, g, b):
	type = 0b0000001
	tileData = type.to_bytes(1)

	tileData += int(x).to_bytes(4, signed=True)
	tileData += int(y).to_bytes(4, signed=True)

	tileData += int(r).to_bytes(1)
	tileData += int(g).to_bytes(1)
	tileData += int(b).to_bytes(1)

	#print("made a pixel message")
	
	return tileData

def hello():
	with connect("ws://localhost:5702") as websocket:
		config = websocket.recv()
		TILE_SIZE = int.from_bytes(config[1:3])

		img = Image.open("images/container2.png")
		img.resize((TILE_SIZE // 2, TILE_SIZE // 2))

		width, height = img.size

		# taking half of the width:
		for i in range(width):
			for j in range(height):
			
				# getting the RGB pixel value.
				r, g, b, p = img.getpixel((i, j))

				websocket.send(makePixelMessage(i, j, r, g, b))

hello()