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
	if message is None:
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

def pixHandler(origin, batch):
	msg = messages.makeServerMessage(messages.MsgTypesServer.PIX_Send, origin, batch)
	asyncio.create_task(broadcast(msg))

def pixRectHandler(x, y, w, h, r, g, b, a):
	msg = messages.makeServerMessage(messages.MsgTypesServer.PIX_SendRect, x, y, w, h, r, g, b, a)
	asyncio.create_task(broadcast(msg))

def pixEraseHandler(origin, batch):
	msg = messages.makeServerMessage(messages.MsgTypesServer.PIX_SendErase, origin, batch)
	asyncio.create_task(broadcast(msg))

def pixEraseRectHandler(x, y, w, h):
	msg = messages.makeServerMessage(messages.MsgTypesServer.PIX_SendEraseRect, x, y, w, h)
	asyncio.create_task(broadcast(msg))

messages.PIXEL_HANDLER = pixHandler
messages.PIXEL_RECT_HANDLER = pixRectHandler
messages.PIXEL_ERASE_HANDLER = pixEraseHandler
messages.PIXEL_ERASE_RECT_HANDLER = pixEraseRectHandler

async def handle(websocket):
	CLIENTS.add(websocket)
	try:
		await websocket.send(messages.makeServerMessage(messages.MsgTypesServer.SYS_Config))

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
	tiles.LoadTilesFromFolder()

	async with serve(handle, "localhost", 5702) as server:
		await server.serve_forever()

if __name__ == "__main__":
	asyncio.run(main())