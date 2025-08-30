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

class MsgTypesClient:
	SYS_Ping = 0b0_000_000

	PIX_Put = 0b0_001_000
	PIX_PutRect = 0b0_001_001
	PIX_Erase = 0b0_001_010
	PIX_EraseRect = 0b0_001_011

	TIL_Get = 0b0_010_000

async def send(websocket, message):
	if websocket.state != State.OPEN:
		return

	try:
		await websocket.send(message)
	except ConnectionClosed:
		pass

async def sendTupleBatch(origin, batch, eraseTransparencies = False):
	async with websockets.connect("ws://localhost:5702") as websocket:
		print("new websocket")
		config = await websocket.recv()

		if eraseTransparencies:
			transparencies = [b for b in batch if b[5] != 0xFF and b[5] != 0x00]
			await send(websocket, makeEraseMessage(origin, transparencies))

		await send(websocket, makePixelMessage(origin, batch))
		await asyncio.sleep(1)
		print("socket done sending chunk, maybe wait")

def makePixelMessage(origin, batch):
	if len(batch) > 0x4000:
		print("oops, too many for a batch!")
		return None

	type = MsgTypesClient.PIX_Put
	tileData = type.to_bytes(1)

	tileData += origin[0].to_bytes(4, signed=True)
	tileData += origin[1].to_bytes(4, signed=True)
	tileData += len(batch).to_bytes(2)

	for bat in batch:
		x, y, r, g, b, a = bat

		tileData += int(x).to_bytes(2, signed=True)
		tileData += int(y).to_bytes(2, signed=True)

		tileData += int(r).to_bytes(1)
		tileData += int(g).to_bytes(1)
		tileData += int(b).to_bytes(1)
		tileData += int(a).to_bytes(1)
	
	return tileData

def makeEraseMessage(origin, batch):
	if len(batch) > 0x4000:
		print("oops, too many for a batch!")
		return None

	type = MsgTypesClient.PIX_Erase
	tileData = type.to_bytes(1)

	tileData += origin[0].to_bytes(4, signed=True)
	tileData += origin[1].to_bytes(4, signed=True)
	tileData += len(batch).to_bytes(2)

	for bat in batch:
		x = bat[0]
		y = bat[1]

		tileData += int(x).to_bytes(2, signed=True)
		tileData += int(y).to_bytes(2, signed=True)
	
	return tileData

def getPixelReturnSixTuple(img, x, y):
	# getting the RGB pixel value.
	r, g, b, a = img.getpixel((x, y))

	#if a > 0 and a != 0xFF: # silly
	if a > 0:
		return (x, y, r, g, b, a)

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

def METHOD_linear(img):
	width, height = img.size
	
	print("gathering pixels")
	for y in range(height): 
		for x in range(width):
			tup = getPixelReturnSixTuple(img, x, y)
			if tup is not None:
				SIX_TUPLE_BUFFER.append(tup)

def METHOD_hilbert(img):
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
		tup = getPixelReturnSixTuple(img, *points[i])
		if tup is not None:
			SIX_TUPLE_BUFFER.append(tup)

def METHOD_random(img):
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
		tup = getPixelReturnSixTuple(img, *p)
		if tup is not None:
			SIX_TUPLE_BUFFER.append(tup)

async def main():
	parser = argparse.ArgumentParser(description="Simple bot")
	parser.add_argument("file", help="Image file to print.", type=str)
	parser.add_argument("-m", "--method", help="Index method", type=str)
	parser.add_argument("-c", "--crop", help="Crop the image (l,t,r,b) (#1)", type=int, nargs=4)
	parser.add_argument("-s", "--scale", help="Overall scale (#2)", type=float)
	parser.add_argument("-f", "--fit", help="Fit to a box (2 args) (#3)", type=int, nargs=2)
	parser.add_argument("-r", "--resize", help="Resize (#4)", type=int, nargs=2)
	parser.add_argument("-b", "--batch", help="Batch size override", type=int)
	parser.add_argument("-p", "--position", help="Canvas position", type=int, nargs=2)
	args = parser.parse_args()

	print(args)

	img = Image.open(args.file)
	img = img.convert("RGBA")
	
	width, height = img.size

	if args.crop is not None:
		img = img.crop((args.crop[0], args.crop[1], args.crop[2], args.crop[3]))
		width, height = img.size

	if args.scale is not None:
		width *= args.scale
		height *= args.scale
		img = img.resize((int(width), int(height)))

	if args.fit is not None:
		img = letterbox_image(img, (args.fit[0], args.fit[1]))
		width, height = img.size
	
	if args.resize is not None:
		img = img.resize((args.resize[0], args.resize[1]))
		width, height = img.size

	global SIX_TUPLE_BUFFER
	SIX_TUPLE_BUFFER = []

	BATCH_SIZE = int(min(0x4000, width*height))
	if args.batch is not None:
		BATCH_SIZE = args.batch

	origin = (0, 0)
	if args.position is not None:
		origin = (args.position[0], args.position[1])

	match args.method:
		case "hilbert":
			METHOD_hilbert(img)
		case "random":
			METHOD_random(img)
		case _:
			METHOD_linear(img)

	print(len(SIX_TUPLE_BUFFER), "pixels to send")
	print(BATCH_SIZE, "per batch,", len(SIX_TUPLE_BUFFER) // BATCH_SIZE, "batches")

	tasks = []

	i = 0
	while len(SIX_TUPLE_BUFFER) > 0:
		# take the first BATCH_SIZE pixels
		batch = copy.deepcopy(SIX_TUPLE_BUFFER[:BATCH_SIZE])
		SIX_TUPLE_BUFFER = SIX_TUPLE_BUFFER[BATCH_SIZE:]

		tasks.append(asyncio.create_task(sendTupleBatch(origin, batch, True)))
		await asyncio.sleep(0.1)
		print(f"created task {i}...")
		i += 1

	await asyncio.wait(tasks)

	print("sent all batches")

asyncio.run(main())