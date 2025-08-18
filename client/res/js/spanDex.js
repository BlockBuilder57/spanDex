import L, {Map, CRS, ImageOverlay, TileLayer, GridLayer, Control} from 'leaflet';
const TILE_SIZE = 512;

const SpanDexControl = Control.extend({
	initialize(elem) {
		this.elem = elem;
	},

	onAdd: function(map) {
		this.options.position = this.elem.getAttribute("leaflet-alignment");
		return this.elem;
	},

	onRemove: function(map) {
		// Nothing to do here
	}
});

class CanvasLayer extends GridLayer {
	createTile(coords/*, done*/) {
		const error = null;

		// create a <canvas> element for drawing
		const tile = L.DomUtil.create("canvas", "leaflet-tile");

		// setup tile width and height according to the options
		const size = this.getTileSize();
		tile.width = size.x;
		tile.height = size.y;

		let ctx = tile.getContext("2d");
		ctx.fillStyle = "white";
		ctx.fillRect(0, 0, tile.width, tile.height);

		if (SpanDex.debug) {
			ctx.fillStyle = "black";
			ctx.font = "16px monospace";
			ctx.fillText(`${coords.x}:${coords.y}`,0,16,TILE_SIZE);
		}

		// draw something asynchronously and pass the tile to the done() callback
		// do this when a server exists
		/*setTimeout(function() {
			done(error, tile);
		}, 10);*/

		return tile;
	}
}

class UI {
	static InitializeLeaflet() {
		this.map = new Map("map", {
			crs: CRS.Simple,
			minZoom: 0,
			maxZoom: 6
		});
		this.map.setView( [0, 0], 0);
		this.map.on("move", UI.OnMapMove);
		this.map.on("pointermove", UI.OnPointerMove);

		this.canvasLayer = new CanvasLayer({
			tileSize: TILE_SIZE,
			minNativeZoom: 0,
			maxNativeZoom: 0,
			className: "pointFiltered",
			attribution: `<span id="txtPosition">-, -</span>`
		}).addTo(this.map);
	}

	static Initialize() {
		this.InitializeLeaflet();

		let controls = document.getElementById("controls");
		if (controls != null) {
			for (let i = 0; i < controls.children.length; i++) {
				let child = controls.children[i];
				let ctrl = new SpanDexControl(child);
				ctrl.addTo(this.map);
			}
		}

		this.btnRecenter = document.getElementById("btnRecenter");
		this.btnRecenter.onclick = () => { UI.map.setView([0, 0], 0); }
	}

	static OnMapMove(e) {
		/*let pos = UI.map.getCenter();
		let posPixel = [Math.floor(pos.lng), Math.floor(pos.lat)];
		document.getElementById("txtPosition").innerText = `${posPixel}`;*/
	}

	static OnPointerMove(e) {
		let pos = e.latlng;
		let posPixel = [Math.floor(pos.lng), Math.floor(pos.lat)];
		document.getElementById("txtPosition").innerText = `${posPixel}`;
	}

	static GetCanvasTileAtCoord(coord) {
		// this is what Leaflet does lol
		let key = `${coord[0]}:${coord[1]}:0`;
		if (key in this.canvasLayer._tiles)
			return this.canvasLayer._tiles[key].el;
	}
};

class WebSock {
	static Connect() {
		if (this.websocket)
			this.websocket.close();
		
		this.websocket = new WebSocket("ws://localhost:5702");
		this.websocket.binaryType = "arraybuffer";
		
		this.websocket.onopen = () => {console.log("WebSocket connected!");};
		this.websocket.onclose = () => {console.log("WebSocket disconnected! Retry in a little bit...");};
		this.websocket.onmessage = this.OnMessage;
	}

	static OnMessage(msg) {
		console.debug(msg);
	}

	static SendMessage(msg) {
		if (msg instanceof Array)
			msg = new Uint8Array(msg);
		
		this.websocket.send(msg);
	}
};

class SpanDex {
	static Initialize() {
		console.log("<span>Dex init");
		this.debug = true;
		//this.testInterval = setInterval(this.TestInterval, 10);
	}

	static TestInterval() {
		const multy = TILE_SIZE / 2;

		for (let i = 0; i < 10; i++) {
			let x = Math.floor(((Math.random() * 2) - 1) * multy);
			let y = Math.floor(((Math.random() * 2) - 1) * multy);

			SpanDex.PutColorAtPos([y, x], "#0047ab");
		}
	}

	static PutColorAtPos(pos, col) {
		// find tile pos
		let tileCoord = [Math.floor(pos[0] / TILE_SIZE), Math.floor(pos[1] / TILE_SIZE)];

		let tilePos = [Math.floor(pos[0] % TILE_SIZE), Math.floor(pos[1] % TILE_SIZE)];
		tilePos[0] = tilePos[0] < 0 ? TILE_SIZE + tilePos[0] : tilePos[0];
		tilePos[1] = tilePos[1] < 0 ? TILE_SIZE + tilePos[1] : tilePos[1];

		//console.debug("Getting tile", tileCoord, "pos", tilePos);
		let tileCanvas = UI.GetCanvasTileAtCoord(tileCoord);
		// we don't know if the tile is on screen, so just draw there anyway
		if (tileCanvas) {
			let ctx = tileCanvas.getContext("2d");
			ctx.fillStyle = col;
			ctx.fillRect(tilePos[0], tilePos[1], 1, 1);
			//console.debug("put pixel at", tilePos);
		}

		// tell the network
	}
};

document.addEventListener("DOMContentLoaded", () => {
	SpanDex.Initialize();
	UI.Initialize();
	WebSock.Connect();

	// nasty... can I avoid this?
	window.UI = UI;
	window.SpanDex = SpanDex;
	window.WebSock = WebSock;
});