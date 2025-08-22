import tiles

PIXEL_HANDLER = None
PIXEL_BATCH_HANDLER = None

def makeServerMessageConfig():
	type = 0b1000001
	tile_size = tiles.TILE_SIZE
	
	return type.to_bytes(1) + tile_size.to_bytes(2)

def makeServerMessageTile(x, y):
	# todo: an image format, maybe? :P

	type = 0b1010001
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

def makeServerMessagePixel(x, y, r, g, b, a):
	type = 0b1001001
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
	type = 0b1001010
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

	#print("made a pixel message")
	
	return tileData

def makeServerMessage(type, *data):
	match type:
		case 0b1000001: # send config
			return makeServerMessageConfig()
		case 0b1010001: # send tile
			return makeServerMessageTile(*data)
		case 0b1001001: # send pixel
			return makeServerMessagePixel(*data)
		case 0b1001010: # send pixel batch
			return makeServerMessagePixelBatch(*data)
		case _:
			print("cannot make a message of type", type)
	
	return None

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

	if (colR, colG, colB) != (existing[0], existing[1], existing[2]):
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

		idx += 12 # 4 + 4 + 4

		#print(posX, posY, colR, colG, colB, colA)

		if colA == 0:
			continue

		batch.append((posX, posY, colR, colG, colB, colA))

	# check for duplicate pixels

	#subtract = 0

	for c in batch:
		posX, posY, colR, colG, colB, colA = c

		existing = tiles.GetPixel(posX, posY)

		if (colR, colG, colB) != (existing[0], existing[1], existing[2]):
			tiles.SetPixel(posX, posY, colR, colG, colB, colA)
			clean_batch.append(c)
		#else:
		#	subtract += 1

	#print("difference", length, "vs", len(clean_batch), "vs", length-subtract)

	# let the network know
	if PIXEL_BATCH_HANDLER is not None:
		PIXEL_BATCH_HANDLER(clean_batch)

def handleClientMessageGetTile(data):
	posX = int.from_bytes(data[1:5], signed=True)
	posY = int.from_bytes(data[5:9], signed=True)

	#print("client asked for", posX, posY)
	return makeServerMessage(0b1010001, posX, posY)

def handleClientMessage(data):
	#print(data[0])
	match data[0]:
		case 0b0001001: # put pixel
			return handleClientMessagePutPixel(data)
		case 0b0001010: # put pixel batch
			return handleClientMessagePutPixelBatch(data)
		case 0b0010001: # get tile
			return handleClientMessageGetTile(data)
		case _:
			print("cannot recieve a message of type", type)

	return None