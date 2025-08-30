from enum import Enum
import tiles

class MsgTypesClient:
	SYS_Ping = 0b0_000_000

	PIX_Put = 0b0_001_000
	PIX_PutBatch = 0b0_001_001
	PIX_PutRect = 0b0_001_010
	PIX_Erase = 0b0_001_011
	PIX_EraseRect = 0b0_001_100

	TIL_Get = 0b0_010_000

class MsgTypesServer:
	SYS_Pong = 0b1_000_000
	SYS_Config = 0b1_000_001

	PIX_Send = 0b1_001_000
	PIX_SendBatch = 0b1_001_001
	PIX_SendRect = 0b1_001_010
	PIX_SendErase = 0b1_001_011
	PIX_SendEraseRect = 0b1_001_100

	TIL_Send = 0b1_010_000

#
# Network Handlers
#

PIXEL_HANDLER = None
PIXEL_BATCH_HANDLER = None
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

def makeServerMessagePixel(x, y, r, g, b, a):
	type = MsgTypesServer.PIX_Send
	tileData = type.to_bytes(1)

	tileData += int(x).to_bytes(4, signed=True)
	tileData += int(y).to_bytes(4, signed=True)

	tileData += int(r).to_bytes(1)
	tileData += int(g).to_bytes(1)
	tileData += int(b).to_bytes(1)
	tileData += int(a).to_bytes(1)

	#print("made a pixel message")
	
	return tileData

def makeServerMessagePixelBatch(batch):
	type = MsgTypesServer.PIX_SendBatch
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

	#print("made a pixel batch message")
	
	return tileData

def makeServerMessagePixelRect(x, y, w, h, r, g, b, a):
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

def makeServerMessageErase(x, y):
	type = MsgTypesServer.PIX_SendErase
	tileData = type.to_bytes(1)

	tileData += int(x).to_bytes(4, signed=True)
	tileData += int(y).to_bytes(4, signed=True)

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
		case MsgTypesServer.PIX_Send: # send pixel
			return makeServerMessagePixel(*data)
		case MsgTypesServer.PIX_SendBatch: # send pixel batch
			return makeServerMessagePixelBatch(*data)
		case MsgTypesServer.PIX_SendRect: # send pixel rect
			return makeServerMessagePixelRect(*data)
		case MsgTypesServer.PIX_SendErase: # send pixel rect
			return makeServerMessageErase(*data)
		case MsgTypesServer.PIX_SendEraseRect: # send pixel rect
			return makeServerMessageEraseRect(*data)
		case MsgTypesServer.TIL_Send: # send tile
			return makeServerMessageTile(*data)
		case _:
			print("cannot make a message of type", type)
	
	return None

#
# Client
#

def handleClientMessagePutPixel(data):
	posX = int.from_bytes(data[1:5], signed=True)
	posY = int.from_bytes(data[5:9], signed=True)

	colR = int.from_bytes(data[9:10])
	colG = int.from_bytes(data[10:11])
	colB = int.from_bytes(data[11:12])
	colA = int.from_bytes(data[12:13])

	#print(posX, posY, colR, colG, colB, colA)

	if colA == 0:
		return

	existing = tiles.GetPixel(posX, posY)

	if (colR, colG, colB) != (existing[0], existing[1], existing[2]) or colA != 0xFF:
		tiles.SetPixel(posX, posY, colR, colG, colB, colA)

		# let the network know
		if PIXEL_HANDLER is not None:
			PIXEL_HANDLER(posX, posY, colR, colG, colB, colA)

def handleClientMessagePutPixelBatch(data):
	length = int.from_bytes(data[1:3])

	batch = []
	clean_batch = []

	idx = 2
	for i in range(length):
		posX = int.from_bytes(data[idx+1:idx+5], signed=True)
		posY = int.from_bytes(data[idx+5:idx+9], signed=True)

		colR = int.from_bytes(data[idx+9:idx+10])
		colG = int.from_bytes(data[idx+10:idx+11])
		colB = int.from_bytes(data[idx+11:idx+12])
		colA = int.from_bytes(data[idx+12:idx+13])

		idx += 12 # posX + posY + colRGBA

		#print(posX, posY, colR, colG, colB, colA)

		if colA == 0:
			continue

		batch.append((posX, posY, colR, colG, colB, colA))

	# check for duplicate pixels

	#subtract = 0

	for c in batch:
		posX, posY, colR, colG, colB, colA = c
		newPix = tiles.SetPixel(posX, posY, colR, colG, colB, colA)

		if newPix is not None:
			c = (posX, posY, *newPix)
			clean_batch.append(c)

	# let the network know
	if PIXEL_BATCH_HANDLER is not None:
		PIXEL_BATCH_HANDLER(clean_batch)

def handleClientMessagePutPixelRect(data):
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
	x = int.from_bytes(data[1:5])
	y = int.from_bytes(data[5:9])

	tiles.SetPixel(x, y, 0, 0, 0, 0)

	if PIXEL_ERASE_HANDLER is not None:
		PIXEL_ERASE_HANDLER(x, y)

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
		case MsgTypesClient.PIX_Put: # put pixel
			return handleClientMessagePutPixel(data)
		case MsgTypesClient.PIX_PutBatch: # put pixel batch
			return handleClientMessagePutPixelBatch(data)
		case MsgTypesClient.PIX_PutRect: # put rect of pixels
			return handleClientMessagePutPixelRect(data)
		case MsgTypesClient.PIX_Erase: # erase pixel
			return handleClientMessageErase(data)
		case MsgTypesClient.PIX_EraseRect: # erase rect of pixels
			return handleClientMessageEraseRect(data)
		case MsgTypesClient.TIL_Get: # get tile
			return handleClientMessageGetTile(data)
		case _:
			print("cannot recieve a message of type", data[0])

	return None