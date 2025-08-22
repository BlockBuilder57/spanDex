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
		
		LOADED_TILES[(x, y)] = Image.open(os.path.join("tiles/", f))

def CreateTile(coord):
	if coord in LOADED_TILES:
		return LOADED_TILES[coord]

	LOADED_TILES[coord] = Image.new("RGBA", (TILE_SIZE, TILE_SIZE), (0, 0, 0, 0))
	return LOADED_TILES[coord]

def GetOrCreateTile(coord):
	if coord not in LOADED_TILES:
		CreateTile(coord)
	return LOADED_TILES[coord]

def SetPixel(x, y, r, g, b, a):
	tileCoordX = x // TILE_SIZE
	tileCoordY = y // TILE_SIZE
	tilePosX = x % TILE_SIZE
	tilePosX = TILE_SIZE + tilePosX if tilePosX < 0 else tilePosX
	tilePosY = y % TILE_SIZE
	tilePosY = TILE_SIZE + tilePosY if tilePosY < 0 else tilePosY

	tile = GetOrCreateTile((tileCoordX, tileCoordY))
	if tile is not None:
		tile.putpixel((tilePosX, tilePosY), (r, g, b, a))
		MODIFIED_TILES[(tileCoordX, tileCoordY)] = tile

def GetPixel(x, y):
	tileCoordX = x // TILE_SIZE
	tileCoordY = y // TILE_SIZE
	tilePosX = x % TILE_SIZE
	tilePosX = TILE_SIZE + tilePosX if tilePosX < 0 else tilePosX
	tilePosY = y % TILE_SIZE
	tilePosY = TILE_SIZE + tilePosY if tilePosY < 0 else tilePosY

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