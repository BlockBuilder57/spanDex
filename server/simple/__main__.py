import argparse
import asyncio
from websockets.asyncio.server import serve
from websockets.exceptions import ConnectionClosed, ConnectionClosedError
from websockets.connection import State

import messages
import tiles

global CLIENTS
CLIENTS = set()

async def send(websocket, message):
	if websocket.state != State.OPEN:
		return

	try:
		await websocket.send(message)
	except ConnectionClosed:
		pass

async def broadcast(message):
	#print("broadcasting to", len(CLIENTS))
	for websocket in CLIENTS:
		#print("broadcasting to socket")
		asyncio.create_task(send(websocket, message))

def pixHandler(x, y, r, g, b, a):
	msg = messages.makeServerMessage(0b1001001, x, y, r, g, b, a)
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
				await asyncio.sleep(0)
	except ConnectionClosedError as e:
		print("forcibly closed websocket due to", type(e), e)
		pass
	finally:
		CLIENTS.remove(websocket)

async def main():
	async with serve(handle, "localhost", 5702) as server:
		await server.serve_forever()

if __name__ == "__main__":
	asyncio.run(main())