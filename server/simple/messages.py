from enum import Enum
import tiles

class MsgTypesClient:
	SYS_Ping = 0b0_000_000

	PIX_Put = 0b0_001_000
	PIX_PutRect = 0b0_001_001
	PIX_Erase = 0b0_001_010
	PIX_EraseRect = 0b0_001_011

	TIL_Get = 0b0_010_000

class MsgTypesServer:
	SYS_Pong = 0b1_000_000
	SYS_Config = 0b1_000_001

	PIX_Send = 0b1_001_000
	PIX_SendRect = 0b1_001_001
	PIX_SendErase = 0b1_001_010
	PIX_SendEraseRect = 0b1_001_011

	TIL_Send = 0b1_010_000

#
# Network Handlers
#

PIXEL_HANDLER = None
PIXEL_RECT_HANDLER = None
PIXEL_ERASE_HANDLER = None
PIXEL_ERASE_RECT_HANDLER = None

#
# Server
#

def makeServerMessageConfig():
	type = MsgTypesServer.SYS_Config
	tile_size = tiles.TILE_SIZE
	
	return type.to_bytes(1) + tile_size.to_bytes(2)

def makeServerMessageSend(origin, batch):
	if len(batch) > 0x4000:
		print("oops, too many for a batch!")
		return None

	type = MsgTypesServer.PIX_Send
	tileData = type.to_bytes(1)

	tileData += origin[0].to_bytes(4, signed=True)
	tileData += origin[1].to_bytes(4, signed=True)
	tileData += len(batch).to_bytes(2)

	for bat in batch:
		x, y, r, g, b, a = bat

		if abs(x) > 32768 or abs(y) > 32768:
			print(bat)
			print("can't move more than 32768 pixels from origin!")
			return None

		tileData += int(x).to_bytes(2, signed=True)
		tileData += int(y).to_bytes(2, signed=True)

		tileData += int(r).to_bytes(1)
		tileData += int(g).to_bytes(1)
		tileData += int(b).to_bytes(1)
		tileData += int(a).to_bytes(1)

	#print("made a pixel batch message")
	
	return tileData

def makeServerMessageSendRect(x, y, w, h, r, g, b, a):
	type = MsgTypesServer.PIX_SendRect
	tileData = type.to_bytes(1)

	tileData += int(x).to_bytes(4, signed=True)
	tileData += int(y).to_bytes(4, signed=True)
	tileData += int(w).to_bytes(2)
	tileData += int(h).to_bytes(2)

	tileData += int(r).to_bytes(1)
	tileData += int(g).to_bytes(1)
	tileData += int(b).to_bytes(1)
	tileData += int(a).to_bytes(1)
	
	return tileData

def makeServerMessageErase(origin, batch):
	if len(batch) > 0x4000:
		print("oops, too many for a batch!")
		return None

	type = MsgTypesServer.PIX_SendErase
	tileData = type.to_bytes(1)

	tileData += origin[0].to_bytes(4, signed=True)
	tileData += origin[1].to_bytes(4, signed=True)
	tileData += len(batch).to_bytes(2)

	for bat in batch:
		x, y = bat

		if abs(x) > 32768 or abs(y) > 32768:
			print(bat)
			print("can't move more than 32768 pixels from origin!")
			return None

		tileData += int(x).to_bytes(2, signed=True)
		tileData += int(y).to_bytes(2, signed=True)

	#print("made an erase batch message")

	return tileData
	
def makeServerMessageEraseRect(todo):
	pass

def makeServerMessageTile(x, y):
	type = MsgTypesServer.TIL_Send
	tileData = type.to_bytes(1)

	# tile position
	tileData += int(x).to_bytes(4, signed=True)
	tileData += int(y).to_bytes(4, signed=True)

	#print("okay sending this tile:", tileData)

	#tileData += bytes(pixels)

	tile = tiles.GetOrCreateTile((x, y))
	tileData += tile.convert("RGBA").tobytes()

	#print("made the data yay")
	
	return tileData

def makeServerMessage(type, *data):
	match type:
		case MsgTypesServer.SYS_Config: # send config
			return makeServerMessageConfig()
		case MsgTypesServer.PIX_Send: # send pixels
			return makeServerMessageSend(*data)
		case MsgTypesServer.PIX_SendRect: # send pixel rect
			return makeServerMessageSendRect(*data)
		case MsgTypesServer.PIX_SendErase: # send erases
			return makeServerMessageErase(*data)
		case MsgTypesServer.PIX_SendEraseRect: # send erase rect
			return makeServerMessageEraseRect(*data)
		case MsgTypesServer.TIL_Send: # send tile
			return makeServerMessageTile(*data)
		case _:
			print("cannot make a message of type", type)
	
	return None

#
# Client
#

def handleClientMessagePut(data):
	origin = (int.from_bytes(data[1:5], signed=True), int.from_bytes(data[5:9], signed=True))
	length = int.from_bytes(data[9:11])

	batch = []
	clean_batch = []

	idx = 11
	for i in range(length):
		posX = int.from_bytes(data[idx+0:idx+2], signed=True)
		posY = int.from_bytes(data[idx+2:idx+4], signed=True)

		colR = int.from_bytes(data[idx+4:idx+5])
		colG = int.from_bytes(data[idx+5:idx+6])
		colB = int.from_bytes(data[idx+6:idx+7])
		colA = int.from_bytes(data[idx+7:idx+8])

		idx += 8 # posX + posY + colRGBA

		#print(posX, posY, colR, colG, colB, colA)

		if colA == 0:
			continue

		batch.append((posX, posY, colR, colG, colB, colA))

	# check for duplicate pixels

	#subtract = 0

	for c in batch:
		posX, posY, colR, colG, colB, colA = c
		newPix = tiles.SetPixel(posX + origin[0], posY + origin[1], colR, colG, colB, colA)

		if newPix is not None:
			c = (posX, posY, *newPix)
			clean_batch.append(c)

	# let the network know
	if PIXEL_HANDLER is not None:
		PIXEL_HANDLER(origin, clean_batch)

def handleClientMessagePutRect(data):
	x = int.from_bytes(data[1:5])
	y = int.from_bytes(data[5:9])
	w = int.from_bytes(data[9:11])
	h = int.from_bytes(data[11:13])

	colR = int.from_bytes(data[13:14])
	colG = int.from_bytes(data[14:15])
	colB = int.from_bytes(data[15:16])
	colA = int.from_bytes(data[16:17])

	if colA == 0:
		return

	for j in range(h):
		for i in range(w):
			tiles.SetPixel(x+i, y+j, colR, colG, colB, colA)

	# let the network know
	if PIXEL_RECT_HANDLER is not None:
		PIXEL_RECT_HANDLER(x, y, w, h, colR, colG, colB, colA)

def handleClientMessageErase(data):
	origin = (int.from_bytes(data[1:5], signed=True), int.from_bytes(data[5:9], signed=True))
	length = int.from_bytes(data[9:11])

	batch = []

	idx = 11
	for i in range(length):
		posX = int.from_bytes(data[idx+0:idx+2], signed=True)
		posY = int.from_bytes(data[idx+2:idx+4], signed=True)

		idx += 4 # posX + posY

		#print(posX, posY)

		newPix = tiles.SetPixel(origin[0] + posX, origin[1] + posY, 0, 0, 0, 0, False)
		if newPix is not None:
			batch.append((posX, posY))

	# let the network know
	if PIXEL_ERASE_HANDLER is not None:
		PIXEL_ERASE_HANDLER(origin, batch)

def handleClientMessageEraseRect(todo):
	pass

def handleClientMessageGetTile(data):
	posX = int.from_bytes(data[1:5], signed=True)
	posY = int.from_bytes(data[5:9], signed=True)

	#print("client asked for", posX, posY)
	return makeServerMessage(MsgTypesServer.TIL_Send, posX, posY)

def handleClientMessage(data):
	#print(data[0])
	match data[0]:
		case MsgTypesClient.PIX_Put: # put pixels
			return handleClientMessagePut(data)
		case MsgTypesClient.PIX_PutRect: # put rect of pixels
			return handleClientMessagePutRect(data)
		case MsgTypesClient.PIX_Erase: # erase pixels
			return handleClientMessageErase(data)
		case MsgTypesClient.PIX_EraseRect: # erase rect of pixels
			return handleClientMessageEraseRect(data)
		case MsgTypesClient.TIL_Get: # get tile
			return handleClientMessageGetTile(data)
		case _:
			print("cannot recieve a message of type", data[0])

	return None