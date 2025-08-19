import argparse
import asyncio
import os
import random
import sys
from PIL import Image, ImageOps
import websockets

TILE_SIZE = -1

def makePixelMessage(x, y, r, g, b):
	type = 0b0001001
	tileData = type.to_bytes(1)

	tileData += int(x).to_bytes(4, signed=True)
	tileData += int(y).to_bytes(4, signed=True)

	tileData += int(r).to_bytes(1)
	tileData += int(g).to_bytes(1)
	tileData += int(b).to_bytes(1)
	
	return tileData

async def main():
	async with websockets.connect("ws://localhost:5702") as websocket:
		config = await websocket.recv()
		TILE_SIZE = int.from_bytes(config[1:3])

		img = Image.open(sys.argv[1])
		img = img.convert("RGBA")
		#img = img.resize((TILE_SIZE, TILE_SIZE))
		#img = ImageOps.fit(img, (TILE_SIZE, TILE_SIZE))

		width, height = img.size

		# taking half of the width:
		for j in range(height):
			for i in range(width):
			
				# getting the RGB pixel value.
				r, g, b, a = img.getpixel((i, j))

				if a >= 200:
					await websocket.send(makePixelMessage(i-(width/2), j-(height/2), r, g, b))

asyncio.run(main())