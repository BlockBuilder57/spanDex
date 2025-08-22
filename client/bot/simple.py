import argparse
import asyncio
import copy
import math
import os
import random
import sys

from PIL import Image, ImageOps
from hilbertcurve.hilbertcurve import HilbertCurve
import websockets
from websockets.exceptions import ConnectionClosed, ConnectionClosedError
from websockets.connection import State

async def send(websocket, message):
	if websocket.state != State.OPEN:
		return

	try:
		await websocket.send(message)
	except ConnectionClosed:
		pass

async def sendTupleBatch(batch):
	async with websockets.connect("ws://localhost:5702") as websocket:
		print("new websocket")
		config = await websocket.recv()

		await send(websocket, makePixelBatchMessage(batch))
		#await asyncio.sleep(1)
		print("socket done sending chunk, maybe wait")

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

def makePixelBatchMessage(batch):
	type = 0b0001010
	tileData = type.to_bytes(1)

	if len(batch) > 0x4000:
		print("oops, too many for a batch!")
		return None

	tileData += len(batch).to_bytes(2)

	for b in batch:
		x, y, r, g, b, a = b

		tileData += int(x).to_bytes(4, signed=True)
		tileData += int(y).to_bytes(4, signed=True)

		tileData += int(r).to_bytes(1)
		tileData += int(g).to_bytes(1)
		tileData += int(b).to_bytes(1)
		tileData += int(a).to_bytes(1)
	
	return tileData

def getPixelReturnSixTuple(img, x, y, px, py):
	# getting the RGB pixel value.
	r, g, b, a = img.getpixel((x, y))

	return (x + px, y + py, r, g, b, a)

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

def METHOD_linear(img, posX, posY):
	width, height = img.size
	
	print("gathering pixels")
	for y in range(height): 
		for x in range(width):
			tup = getPixelReturnSixTuple(img, x, y, posX, posY)
			if tup[5] > 0: # alpha
				SIX_TUPLE_BUFFER.append(tup)

def METHOD_hilbert(img, posX, posY):
	# log2 largest dimension
	imgDim = max(img.size)
	log2 = int(math.log2(imgDim))
	p2 = math.ceil(math.pow(2, log2))
	# force a letterbox for this, we need a power of 2 size
	img = letterbox_image(img, (p2, p2))
	
	# make the curve
	# p=log2+1, 2 dimensions
	print("making hilbert curve")
	hilbert_curve = HilbertCurve(log2+1, 2)
	# get indicies out of this thing
	dist = list(range(p2*p2))
	points = hilbert_curve.points_from_distances(dist)

	print("gathering pixels")
	for i in range(p2*p2):
		x, y = points[i]
		tup = getPixelReturnSixTuple(img, x, y, posX, posY)
		if tup[5] > 0: # alpha
			SIX_TUPLE_BUFFER.append(tup)

def METHOD_random(img, posX, posY):
	width, height = img.size

	points = []
	
	print("gathering points")
	for y in range(height): 
		for x in range(width):
			points.append((x, y))
	
	print("shuffling")
	random.shuffle(points)

	print("gathering pixels")
	for p in points:
		tup = getPixelReturnSixTuple(img, *p, posX, posY)
		if tup[5] > 0: # alpha
			SIX_TUPLE_BUFFER.append(tup)

async def main():
	parser = argparse.ArgumentParser(description="Simple bot")
	parser.add_argument("file", help="Image file to print.", type=str)
	parser.add_argument("-m", "--method", help="Index method", type=str)
	parser.add_argument("-s", "--scale", help="Overall scale (applied first)", type=float)
	parser.add_argument("-f", "--fit", help="Fit to a box (2 args)", type=int, nargs=2)
	parser.add_argument("-r", "--resize", help="Resize", type=int, nargs=2)
	parser.add_argument("-b", "--batch", help="Batch size override", type=int)
	parser.add_argument("-p", "--position", help="Canvas position", type=int, nargs=2)
	args = parser.parse_args()

	print(args)

	img = Image.open(args.file)
	img = img.convert("RGBA")
	
	width, height = img.size

	if args.scale is not None:
		img = img.resize((int(width), int(height)))

	if args.fit is not None:
		# does cropping, not scaling!
		#img = ImageOps.fit(img, (args.fit[0], args.fit[1]))
		img = letterbox_image(img, (args.fit[0], args.fit[1]))
		width, height = img.size
	
	if args.resize is not None:
		img = img.resize((args.resize[0], args.resize[1]))
		width, height = img.size

	global SIX_TUPLE_BUFFER
	SIX_TUPLE_BUFFER = []

	BATCH_SIZE = min(0x4000, width*height)
	if args.batch is not None:
		BATCH_SIZE = args.batch

	x = y = 0
	if args.position is not None:
		x, y = (args.position[0], args.position[1])

	match args.method:
		case "hilbert":
			METHOD_hilbert(img, x, y)
		case "random":
			METHOD_random(img, x, y)
		case _:
			METHOD_linear(img, x, y)

	print(len(SIX_TUPLE_BUFFER), "pixels to send")
	print(BATCH_SIZE, "per batch,", len(SIX_TUPLE_BUFFER) // BATCH_SIZE, "batches")

	tasks = []

	i = 0
	while len(SIX_TUPLE_BUFFER) > 0:
		# take the first BATCH_SIZE pixels
		batch = copy.deepcopy(SIX_TUPLE_BUFFER[:BATCH_SIZE])
		SIX_TUPLE_BUFFER = SIX_TUPLE_BUFFER[BATCH_SIZE:]

		tasks.append(asyncio.create_task(sendTupleBatch(batch)))
		await asyncio.sleep(0.001)
		print(f"created task {i}...")
		i += 1

	await asyncio.wait(tasks)

	print("sent all batches")

asyncio.run(main())