import L, {Map, CRS, ImageOverlay, TileLayer, GridLayer, Control} from 'leaflet';

function jankyColorGetter(col) {
	var ctx = document.createElement("canvas").getContext("2d");
	ctx.fillStyle = col;
	let hex = ctx.fillStyle; // hex code version!
	let arr = new Uint8Array(3);
	arr.setFromHex(hex.substring(1))
	return arr;
}

function arrToRGBHex(arr) {
	// https://stackoverflow.com/a/34310051
	return "#" + Array.from(arr, function (byte) {
		return ('0' + (byte & 0xFF).toString(16)).slice(-2);
	}).join('');
}

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

		// clear layer if desired
		if (this.options.clearLayer) {
			let ctx = tile.getContext("2d");
			ctx.fillStyle = "white";
			//ctx.fillRect(0, 0, tile.width, tile.height);

			if (SpanDex.debug) {
				ctx.fillStyle = "black";
				ctx.font = "16px monospace";
				ctx.fillText(`${coords.x}:${coords.y}`,0,16,SpanDex.tileSize);
			}
		}

		// draw something asynchronously and pass the tile to the done() callback
		// do this when a server exists
		/*setTimeout(function() {
			done(error, tile);
		}, 10);*/

		SpanDex.GetTile(coords);

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
			tileSize: SpanDex.tileSize,
			minNativeZoom: 0,
			maxNativeZoom: 0,
			className: "pointFiltered",
			attribution: `<span id="txtPosition">-, -</span>`,
			clearLayer: true
		}).addTo(this.map);

		if (SpanDex.debug) {
			this.canvasLayerDebug = new CanvasLayer({
				tileSize: SpanDex.tileSize,
				minNativeZoom: 0,
				maxNativeZoom: 0,
				className: "pointFiltered"
			}).addTo(this.map);

			this.canvasLayerDebugInterval = setInterval(UI.DebugLayerOpacityTickdown, 20);
		}
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

	static DebugLayerOpacityTickdown() {
		if (!UI.canvasLayerDebug)
			return;

		for (const key in UI.canvasLayerDebug._tiles) {
			const tile = UI.canvasLayerDebug._tiles[key].el;
			// skip if we don't have a valid tile
			if (!tile || !tile.lastDraw || tile.lastDraw == -1)
				continue;

			// we'll want to clear anything outside of 5 sec, then invalidate it for later checks
			let clear = false;
			if (Math.abs(tile.lastDraw - Date.now()) > 5000) {
				//console.debug(`clearing ${key} after ${Math.abs(tile.lastDraw - Date.now())}ms`);
				tile.lastDraw = -1;
				clear = true;
			}

			const ctx = tile.getContext("2d");
			let imageData = ctx.getImageData(0, 0, SpanDex.tileSize, SpanDex.tileSize);
			for (var i = 0; i < imageData.data.length; i += 4) {
				//imageData.data[i+3] *= clear ? 0 : 0.96;
				imageData.data[i+3] -= clear ? 255 : 3;
			}
			ctx.putImageData(imageData, 0, 0);
		}
	}

	static OnMapMove(e) {
		/*let pos = UI.map.getCenter();
		let posPixel = [Math.floor(pos.lng), -Math.floor(pos.lat)];
		document.getElementById("txtPosition").innerText = `${posPixel}`;*/
	}

	static OnPointerMove(e) {
		let pos = e.latlng;
		let posPixel = [Math.floor(pos.lng), -Math.floor(pos.lat)];
		document.getElementById("txtPosition").innerText = `${posPixel}`;
	}

	static GetCanvasTileAtCoord(coord, canvasLayer) {
		if (!canvasLayer)
			canvasLayer = UI.canvasLayer;

		// this is what Leaflet does lol
		let key = `${coord[0]}:${coord[1]}:0`;
		if (key in canvasLayer._tiles)
			return canvasLayer._tiles[key].el;
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
		//console.debug(msg.data);
		if (msg.data instanceof ArrayBuffer) {
			msg = new Uint8Array(msg.data);
			//console.debug(msg);

			if (msg[0] & 0b1000000 == 0) {
				console.error("somehow recieved a client message?");
				return;
			}

			let dv = new DataView(msg.buffer);

			switch(msg[0]) {
				case 0b1000001:
					SpanDex.tileSize = dv.getUint16(1);
					//console.debug("config", "\ntileSize", SpanDex.tileSize);
					UI.Initialize();
					break;
				case 0b1010001:
					var coord = [dv.getInt32(1), dv.getInt32(5)]
					//console.debug("tile", coord);
					var canv = UI.GetCanvasTileAtCoord(coord)
					if (canv) {
						var ctx = canv.getContext("2d");
						var imageData = ctx.getImageData(0, 0, SpanDex.tileSize, SpanDex.tileSize);
						var startOffset = 9;
						for (var i = startOffset; i < startOffset + imageData.data.length; i++) {
							imageData.data[i-startOffset] = dv.getUint8(i);
						}
						ctx.putImageData(imageData, 0, 0);
					}
					break;
				case 0b1001001:
					var pos = [dv.getInt32(1), dv.getInt32(5)]
					var col = [dv.getUint8(9), dv.getUint8(10), dv.getUint8(11), dv.getUint8(12)]
					//console.debug("pixel", "\npos", pos, "\ncol", col);
					SpanDex.PutColorAtPos(pos, col, true);
					break;
				case 0b1001010:
					var len = dv.getUint16(1)
					//console.debug("pixel batch", "\nlength", len);
					
					var offset = 3
					for (var i = 0; i < len; i++, offset += 12) {
						var pos = [dv.getInt32(offset+0), dv.getInt32(offset+4)]
						var col = [dv.getUint8(offset+8), dv.getUint8(offset+9), dv.getUint8(offset+10), dv.getUint8(offset+11)]
					
						SpanDex.PutColorAtPos(pos, col, true);
					}
					break;
				default:
					console.warn("Recieved a strange message:", msg[0].toString(2))
			}
		}
	}

	static SendMessage(msg) {
		if (msg instanceof Array)
			msg = new Uint8Array(msg);

		this.websocket.send(msg);
	}
};

class Paint {
	// http://www.softwareandfinance.com/Turbo_C/DrawCircle.html
	static DrawCircle(x, y, radius, col) {
		for (let i = 0; i < 360; i += 0.1)
		{
			let x1 = radius * Math.cos(i * Math.PI / 180.0);
			let y1 = radius * Math.sin(i * Math.PI / 180.0);

			SpanDex.PutColorAtPos([x + x1, y + y1], col);
		}
	}
}

class SpanDex {
	static Initialize() {
		console.log("<span>Dex init");
		this.tileSize = 512;
		this.localDrawing = false;
		this.debug = true;
		//this.testInterval = setInterval(this.TestInterval, 10);
	}

	static TestInterval() {
		const multy = SpanDex.tileSize / 4;

		for (let i = 0; i < 100000; i++) {
			let x = Math.floor(((Math.random() * 2) - 1) * multy);
			let y = Math.floor(((Math.random() * 2) - 1) * multy);

			SpanDex.PutColorAtPos([y, x], "#0047ab");
		}
	}

	static PutColorAtPos(pos, col, fromSrv) {
		// find tile pos
		//console.debug(pos, col);

		if (col instanceof Array) {
			col = arrToRGBHex(col);
		}

		if (fromSrv || SpanDex.localDrawing) {
			let tileCoord = [Math.floor(pos[0] / SpanDex.tileSize), Math.floor(pos[1] / SpanDex.tileSize)];

			let tilePos = [Math.floor(pos[0] % SpanDex.tileSize), Math.floor(pos[1] % SpanDex.tileSize)];
			tilePos[0] = tilePos[0] < 0 ? SpanDex.tileSize + tilePos[0] : tilePos[0];
			tilePos[1] = tilePos[1] < 0 ? SpanDex.tileSize + tilePos[1] : tilePos[1];

			//console.debug("Getting tile", tileCoord, "pos", tilePos);
			let tileCanvas = UI.GetCanvasTileAtCoord(tileCoord);
			// we don't know if the tile is on screen, so just draw there anyway
			if (tileCanvas) {
				tileCanvas.lastDraw = Date.now();
				let ctx = tileCanvas.getContext("2d");
				
				// direct method, v slow
				/*var imageData = ctx.getImageData(tilePos[0], tilePos[1], 1, 1);
				for (var i = 0; i < 4; i++)
					imageData.data[i] = col[i];
				ctx.putImageData(imageData, tilePos[0], tilePos[1]);*/

				ctx.fillStyle = col;
				ctx.clearRect(tilePos[0], tilePos[1], 1, 1);
				ctx.fillRect(tilePos[0], tilePos[1], 1, 1);
				//console.debug("put pixel at", tilePos);
			}

			if (SpanDex.debug) {
				let tileCanvas = UI.GetCanvasTileAtCoord(tileCoord, UI.canvasLayerDebug);
				if (tileCanvas) {
					tileCanvas.lastDraw = Date.now();
					let ctx = tileCanvas.getContext("2d");
					ctx.fillStyle = fromSrv ? "#ff00ff" : "#ffff00";
					ctx.fillRect(tilePos[0], tilePos[1], 1, 1);
				}
			}
		}

		// tell the network
		if (!fromSrv && !SpanDex.localDrawing) {
			let msg = new Uint8Array(12);
			let dv = new DataView(msg.buffer);
			dv.setUint8(0, 0b0001001);
			dv.setInt32(1, pos[0]);
			dv.setInt32(5, pos[1]);

			let colArr = jankyColorGetter(col);

			dv.setUint8(9, colArr[0]);
			dv.setUint8(10, colArr[1]);
			dv.setUint8(11, colArr[2]);
			WebSock.SendMessage(msg);
		}
	}

	static GetTile(coord) {
		let msg = new Uint8Array(9);
		let dv = new DataView(msg.buffer);
		dv.setUint8(0, 0b0010001);
		dv.setInt32(1, coord.x);
		dv.setInt32(5, coord.y);
		WebSock.SendMessage(msg);
	}
};

document.addEventListener("DOMContentLoaded", () => {
	SpanDex.Initialize();
	WebSock.Connect();

	// nasty... can I avoid this?
	window.UI = UI;
	window.Paint = Paint;
	window.SpanDex = SpanDex;
	window.WebSock = WebSock;
});