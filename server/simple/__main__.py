import argparse
import asyncio
import PIL
import os
from websockets.asyncio.server import serve
from websockets.exceptions import ConnectionClosed
import messages

global CLIENTS
CLIENTS = set()

async def send(websocket, message):
    try:
        await websocket.send(message)
    except ConnectionClosed:
        pass

async def broadcast(message):
	print("broadcasting to", len(CLIENTS))
	for websocket in CLIENTS:
		print("broadcasting to socket")
		await send(websocket, message)

def pixHandler(x, y, r, g, b):
	msg = messages.makeServerMessage(0b1000011, x, y, r, g, b)
	asyncio.create_task(broadcast(msg))

messages.PIXEL_HANDLER = pixHandler

async def handle(websocket):
	CLIENTS.add(websocket)
	try:
		await websocket.send(messages.makeServerMessage(0b1000001))

		async for message in websocket:
			resp = messages.handleClientMessage(message)
			if resp is not None:
				#print(resp)
				await websocket.send(resp)
	finally:
		CLIENTS.remove(websocket)

async def main():
	for i in range(messages.TILE_SIZE * messages.TILE_SIZE):
		messages.pixels.append(255)
		messages.pixels.append(255)
		messages.pixels.append(255)

	async with serve(handle, "localhost", 5702) as server:
		await server.serve_forever()

if __name__ == "__main__":
	asyncio.run(main())