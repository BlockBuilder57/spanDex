import atexit
import os
import signal
import sys

from PIL import Image, ImageOps

TILE_SIZE = 512
LOADED_TILES = {}
MODIFIED_TILES = {}

def LoadTilesFromFolder():
	allPossible = [f for f in os.listdir("tiles/") if os.path.isfile(os.path.join("tiles/", f))]
	for f in allPossible:
		fSplit = f[:-4]
		x, y = fSplit.split("_")
		x = int(x)
		y = int(y)
		
		newTile = Image.open(os.path.join("tiles/", f))
		newTile = newTile.convert("RGBA")
		LOADED_TILES[(x, y)] = newTile

def CreateTile(coord):
	if coord in LOADED_TILES:
		return LOADED_TILES[coord]

	LOADED_TILES[coord] = Image.new("RGBA", (TILE_SIZE, TILE_SIZE), (0, 0, 0, 0))
	return LOADED_TILES[coord]

def GetOrCreateTile(coord):
	if coord not in LOADED_TILES:
		CreateTile(coord)
	return LOADED_TILES[coord]

def PosToTileCoordAndPos(x, y):
	tileCoordX = x // TILE_SIZE
	tileCoordY = y // TILE_SIZE
	tilePosX = x % TILE_SIZE
	tilePosX = TILE_SIZE + tilePosX if tilePosX < 0 else tilePosX
	tilePosY = y % TILE_SIZE
	tilePosY = TILE_SIZE + tilePosY if tilePosY < 0 else tilePosY

	return (tileCoordX, tileCoordY, tilePosX, tilePosY)

def CreateOnePixelForBlending(Ar, Ag, Ab, Aa, Br, Bg, Bb, Ba):
	A = Image.new("RGBA", (1, 1), (Ar, Ag, Ab, Aa))
	B = Image.new("RGBA", (1, 1), (Br, Bg, Bb, Ba))
	return Image.alpha_composite(B, A).getpixel((0, 0))

def SetPixel(x, y, r, g, b, a, blendDontReplace = True):
	existing = GetPixel(x, y)

	tileCoordX, tileCoordY, tilePosX, tilePosY = PosToTileCoordAndPos(x, y)
	returnNewPixel = False

	tile = GetOrCreateTile((tileCoordX, tileCoordY))
	if tile is not None:
		if a != 0xFF and blendDontReplace:
			r, g, b, a = CreateOnePixelForBlending(r, g, b, a, *existing)
		
		newPixels = (r, g, b, a)

		# when the blended pixel is different, or we're not forcibly not blending
		if newPixels != existing or not blendDontReplace:
			tile.putpixel((tilePosX, tilePosY), newPixels)
			returnNewPixel = True

		MODIFIED_TILES[(tileCoordX, tileCoordY)] = tile

	if returnNewPixel:
		return newPixels

def GetPixel(x, y):
	tileCoordX, tileCoordY, tilePosX, tilePosY = PosToTileCoordAndPos(x, y)

	tile = GetOrCreateTile((tileCoordX, tileCoordY))
	if tile is not None:
		return tile.getpixel((tilePosX, tilePosY))

# save when exit

def exit_handler():
	for x, y in MODIFIED_TILES:
		print("saving modified tile", x, y)
		MODIFIED_TILES[(x, y)].save(f"tiles/{x}_{y}.png")

def kill_handler(*args):
	sys.exit(0)

atexit.register(exit_handler)
signal.signal(signal.SIGINT, kill_handler)
signal.signal(signal.SIGTERM, kill_handler)