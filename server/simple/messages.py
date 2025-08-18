TILE_SIZE = 1024
pixels = []

PIXEL_HANDLER = None

def makeServerMessageConfig():
	type = 0b1000001
	tile_size = TILE_SIZE
	
	return type.to_bytes(1) + tile_size.to_bytes(2)

def makeServerMessageTile(x, y):
	# todo: an image format, maybe? :P

	type = 0b1000010
	tileData = type.to_bytes(1)

	# tile position
	tileData += int(x).to_bytes(4, signed=True)
	tileData += int(y).to_bytes(4, signed=True)

	#print("okay sending this tile:", tileData)

	tileData += bytes(pixels)

	#print("made the data yay")
	
	return tileData

def makeServerMessagePixel(x, y, r, g, b):
	type = 0b1000011
	tileData = type.to_bytes(1)

	tileData += int(x).to_bytes(4, signed=True)
	tileData += int(y).to_bytes(4, signed=True)

	tileData += int(r).to_bytes(1)
	tileData += int(g).to_bytes(1)
	tileData += int(b).to_bytes(1)

	print("made a pixel message")
	
	return tileData

def makeServerMessage(type, *data):
	match type:
		case 0b1000001: # send config
			return makeServerMessageConfig()
		case 0b1000010: # send tile
			return makeServerMessageTile(*data)
		case 0b1000011: # send pixel
			return makeServerMessagePixel(*data)
		#default:
		#    print("dunno what kind of message that is")

def handleClientMessagePutPixel(data):
	posX = int.from_bytes(data[1:5], signed=True)
	posY = int.from_bytes(data[5:9], signed=True)

	colR = int.from_bytes(data[9:10])
	colG = int.from_bytes(data[10:11])
	colB = int.from_bytes(data[11:12])

	# todo: actually do different tiles
	posX = posX % TILE_SIZE
	posY = posY % TILE_SIZE

	#print(posX, posY, colR, colG, colB)

	idx = (posX + (posY * TILE_SIZE)) * 3

	pixels[idx+0] = colR
	pixels[idx+1] = colG
	pixels[idx+2] = colB

	if PIXEL_HANDLER is not None:
		PIXEL_HANDLER(posX, posY, colR, colG, colB)

def handleClientMessageGetTile(data):
	posX = int.from_bytes(data[1:5], signed=True)
	posY = int.from_bytes(data[5:9], signed=True)

	print("client asked for", posX, posY)
	return makeServerMessage(0b1000010, posX, posY)

def handleClientMessage(data):
	print(data)
	match data[0]:
		case 0b000001: # put pixel
			return handleClientMessagePutPixel(data)
		case 0b000010: # get tile
			return handleClientMessageGetTile(data)

	return None