import argparse
import asyncio
import PIL
import os
from websockets.asyncio.server import serve

TILE_SIZE = 512
pixels = []

def makeMessageConfig():
	type = 0b000001
	tile_size = TILE_SIZE
	
	return type.to_bytes(1) + tile_size.to_bytes(2)

def makeMessageTile(x, y):
	# todo: an image format, maybe? :P

	type = 0b000010
	tileData = type.to_bytes(1)

	# tile position
	tileData += int(x).to_bytes(4, signed=True)
	tileData += int(y).to_bytes(4, signed=True)

	#print("okay sending this tile:", tileData)

	tileData += bytes(pixels)

	#print("made the data yay")
	
	return tileData

def makeMessage(type):
	match type:
		case 0b000001: # send config
			return makeMessageConfig()
		case 0b000010: # send tile
			return makeMessageTile(0, 0)
		#default:
		#    print("dunno what kind of message that is")

def handleMessagePutPixel(data):
	posX = int.from_bytes(data[1:5], signed=True)
	posY = int.from_bytes(data[5:9], signed=True)

	colR = int.from_bytes(data[9:10])
	colG = int.from_bytes(data[10:11])
	colB = int.from_bytes(data[11:12])

	# todo: actually do different tiles
	posX = posX % TILE_SIZE
	posY = posY % TILE_SIZE

	print(posX, posY, colR, colG, colB)

	idx = (posX + (posY * TILE_SIZE)) * 3

	pixels[idx+0] = colR
	pixels[idx+1] = colG
	pixels[idx+2] = colB

def handleMessageGetTile(data):
	posX = int.from_bytes(data[1:5], signed=True)
	posY = int.from_bytes(data[5:9], signed=True)

	print("client asked for", posX, posY)
	return makeMessageTile(posX, posY)

def handleMessage(data):
	print(data)
	match data[0]:
		case 0b000001: # put pixel
			return handleMessagePutPixel(data)
		case 0b000010: # get tile
			return handleMessageGetTile(data)

	return None

async def handle(websocket):
	await websocket.send(makeMessage(0b000001))
	async for message in websocket:
		resp = handleMessage(message)
		if resp is not None:
			#print(resp)
			await websocket.send(resp)

async def echo(websocket):
	async for message in websocket:
		print("got a message")
		print(message)
		await websocket.send(message)

async def main():
	for i in range(TILE_SIZE * TILE_SIZE):
		pixels.append(255)
		pixels.append(255)
		pixels.append(255)

	async with serve(handle, "localhost", 5702) as server:
		await server.serve_forever()

asyncio.run(main())