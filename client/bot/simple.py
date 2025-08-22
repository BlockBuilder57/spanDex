import argparse
import asyncio
import math
import os
import random
import sys

from PIL import Image, ImageOps
from hilbertcurve.hilbertcurve import HilbertCurve
import websockets
from websockets.exceptions import ConnectionClosed, ConnectionClosedError
from websockets.connection import State

TILE_SIZE = -1

async def send(websocket, message):
	if websocket.state != State.OPEN:
		return

	try:
		await websocket.send(message)
	except ConnectionClosed:
		pass

def makePixelMessage(x, y, r, g, b, a):
	type = 0b0001001
	tileData = type.to_bytes(1)

	tileData += int(x).to_bytes(4, signed=True)
	tileData += int(y).to_bytes(4, signed=True)

	tileData += int(r).to_bytes(1)
	tileData += int(g).to_bytes(1)
	tileData += int(b).to_bytes(1)
	tileData += int(a).to_bytes(1)
	
	return tileData

# https://github.com/qqwweee/keras-yolo3/issues/330
def letterbox_image(image, size):
	iw, ih = image.size
	w, h = size
	scale = min(w/iw, h/ih)
	nw = int(iw*scale)
	nh = int(ih*scale)

	image = image.resize((nw,nh), Image.BICUBIC)
	new_image = Image.new("RGBA", size, (0,0,0,0))
	new_image.paste(image, ((w-nw)//2, (h-nh)//2))
	return new_image

async def grabPixelAndSend(websocket, img, i, j, x, y):
	# getting the RGB pixel value.
	r, g, b, a = img.getpixel((i, j))

	if a > 0:
		await send(websocket, makePixelMessage(x, y, r, g, b, a))
	await asyncio.sleep(0)

async def METHOD_linear(websocket, img):
	width, height = img.size
	
	print("sending pixels")
	for j in range(height): 
		for i in range(width):
			await grabPixelAndSend(websocket, img, i, j, i-(width/2), j-(height/2))

async def METHOD_hilbert(websocket, img):
	# log2 smallest dimension
	largestDim = max(img.size)
	log2 = int(math.log2(largestDim))
	p2 = int(math.pow(2, log2))
	# force a letterbox for this, we need a power of 2 size
	img = letterbox_image(img, (p2, p2))
	
	# make the curve
	# p=log2+1, 2 dimensions
	print("making hilbert curve")
	hilbert_curve = HilbertCurve(log2+1, 2)
	# get indicies out of this thing
	dist = list(range(p2*p2))
	points = hilbert_curve.points_from_distances(dist)

	print("sending pixels")
	for i in range(p2*p2):
		x, y = points[i]
		await grabPixelAndSend(websocket, img, x, y, x-(p2/2), y-(p2/2))


async def main():
	parser = argparse.ArgumentParser(description="Simple bot")
	parser.add_argument("file", help="Image file to print.", type=str)
	parser.add_argument("-s", "--scale", help="scale", type=float)
	parser.add_argument("-f", "--fit", help="scale", type=int, nargs=2)
	args = parser.parse_args()

	print(args)

	async with websockets.connect("ws://localhost:5702") as websocket:
		config = await websocket.recv()
		TILE_SIZE = int.from_bytes(config[1:3])
		print("got config, tile size is", TILE_SIZE)

		img = Image.open(args.file)
		img = img.convert("RGBA")
		
		width, height = img.size

		if args.scale is not None:
			width *= args.scale
			height *= args.scale
			img = img.resize((int(width), int(height)))

		if args.fit is not None:
			# does cropping, not scaling!
			#img = ImageOps.fit(img, (args.fit[0], args.fit[1]))
			img = letterbox_image(img, (args.fit[0], args.fit[1]))
			width, height = img.size
		
		#await METHOD_linear(websocket, img)
		await METHOD_hilbert(websocket, img)
		print("all done, waiting for socket close")

asyncio.run(main())