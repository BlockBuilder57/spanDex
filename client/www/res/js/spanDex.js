import L, {Map, CRS, ImageOverlay, TileLayer, GridLayer, Control} from 'leaflet';

function byteArrToHex(arr) {
	// https://stackoverflow.com/a/34310051
	return "#" + Array.from(arr, function (byte) {
		return ('0' + (byte & 0xFF).toString(16)).slice(-2);
	}).join('');
}

function hextoByteArr(hex, argb) {
	if (hex.startsWith("#"))
		hex = hex.substring(1);

	hex = hex.padStart(8, "0");

	if (argb) // turn argb into rgba
		hex = hex.substring(2, 8) + hex.substring(0, 2);
	
	let arr = new Uint8Array(4);
	arr.setFromHex(hex);
	return arr;
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
			let diff = Math.abs(tile.lastDraw - Date.now()) / 1000;

			if (diff > 5.0) {
				//console.debug(`clearing ${key} after ${Math.abs(tile.lastDraw - Date.now())}ms`);
				tile.lastDraw = -1;
				clear = true;
			}

			let opacityCap = Math.floor((1.0 - (diff / 5.0)) * 255);

			const ctx = tile.getContext("2d");
			let imageData = ctx.getImageData(0, 0, SpanDex.tileSize, SpanDex.tileSize);
			for (var i = 0; i < imageData.data.length; i += 4) {
				if (imageData.data[i + 3] <= 0)
					continue;

				imageData.data[i + 3] = (clear ? 0 : Math.min(opacityCap, imageData.data[i + 3] - 3));
			}
			ctx.putImageData(imageData, 0, 0);
		}
	}

	// Why.
	static RoundProperlyForPositionCoordinates(x) {
		return x < 0 ? -Math.ceil(-x) : Math.floor(x);
	};

	static OnMapMove(e) {
		/*let pos = UI.map.getCenter();
		let posPixel = [UI.RoundProperlyForPositionCoordinates(pos.lng), UI.RoundProperlyForPositionCoordinates(-pos.lat)];
		document.getElementById("txtPosition").innerText = `${posPixel}`;*/
	}

	static OnPointerMove(e) {
		let pos = e.latlng;
		let posPixel = [UI.RoundProperlyForPositionCoordinates(pos.lng), UI.RoundProperlyForPositionCoordinates(-pos.lat)];
		document.getElementById("txtPosition").innerText = `${posPixel}`;
	}

	static GetCanvasTileAtCoord(coord, canvasLayer) {
		if (!canvasLayer)
			canvasLayer = UI.canvasLayer;

		// this is what Leaflet does lol
		let key = `${coord[0]}:${coord[1]}:0`;
		//console.debug("GetCanvasTileAtCoord", key);
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
				case SpanDex.MsgTypesServer.SYS_Config:
					SpanDex.tileSize = dv.getUint16(1);
					//console.debug("config", "\ntileSize", SpanDex.tileSize);
					UI.Initialize();
					break;
				case SpanDex.MsgTypesServer.PIX_Send:
					var origin = [dv.getInt32(1), dv.getInt32(5)]
					var len = dv.getUint16(9)
					//console.debug("pixel batch", "\norigin", origin, "\nlength", len);
					
					var offset = 11
					for (var i = 0; i < len; i++, offset += 8) {
						var pos = [dv.getInt16(offset+0), dv.getInt16(offset+2)]
						var col = [dv.getUint8(offset+4), dv.getUint8(offset+5), dv.getUint8(offset+6), dv.getUint8(offset+7)]
					
						//console.debug("pixel", "\npos", pos, "\ncol", col);
						SpanDex.PutPixelAtPos([origin[0] + pos[0], origin[1] + pos[1]], col, true);
					}
					break;
				case SpanDex.MsgTypesServer.PIX_SendRect:
					var pos = [dv.getInt32(1), dv.getInt32(5)]
					var wh = [dv.getUint16(9), dv.getUint16(11)]
					var col = [dv.getUint8(13), dv.getUint8(14), dv.getUint8(15), dv.getUint8(16)]
					//console.debug("pixel rect", "\npos", pos, "\nwh", wh, "\ncol", col);
					
					for (var y = pos[0]; y < pos[0] + wh[1]; y++)
						for (var x = pos[1]; x < pos[1] + wh[0]; x++)
							SpanDex.PutPixelAtPos([x, y], col, true);
					break;
				case SpanDex.MsgTypesServer.PIX_SendErase:
					var origin = [dv.getInt32(1), dv.getInt32(5)]
					var len = dv.getUint16(9)
					//console.debug("erase batch", "\norigin", origin, "\nlength", len);

					var offset = 11
					for (var i = 0; i < len; i++, offset += 4) {
						var pos = [dv.getInt16(offset + 0), dv.getInt16(offset + 2)]
						pos = [origin[0] + pos[0], origin[1] + pos[1]]
					
						//console.debug("erase", "\npos", pos);
						SpanDex.PutPixelAtPos(pos, null, true, true);
					}
					break;
				case SpanDex.MsgTypesServer.PIX_SendEraseRect:
					var pos = [dv.getInt32(1), dv.getInt32(5)]
					var wh = [dv.getUint16(9), dv.getUint16(11)]
					//console.debug("erase rect", "\npos", pos, "\nwh", wh);
					
					for (var y = pos[0]; y < pos[0] + wh[1]; y++)
						for (var x = pos[1]; x < pos[1] + wh[0]; x++)
							SpanDex.PutPixelAtPos([x, y], null, true);
					break;
				case SpanDex.MsgTypesServer.TIL_Send:
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
	// https://zingl.github.io/bresenham.html
	static DrawCircle(xm, ym, r, col) {
		let x = -r, y = 0, err = 2-2*r; /* II. Quadrant */ 
		do {
			SpanDex.PutPixelAtPos([xm-x, ym+y], col); /*   I. Quadrant */
			SpanDex.PutPixelAtPos([xm-y, ym-x], col); /*  II. Quadrant */
			SpanDex.PutPixelAtPos([xm+x, ym-y], col); /* III. Quadrant */
			SpanDex.PutPixelAtPos([xm+y, ym+x], col); /*  IV. Quadrant */
			r = err;
			if (r <= y) err += ++y*2+1;           /* e_xy+e_y < 0 */
			if (r > x || err > y) err += ++x*2+1; /* e_xy+e_x > 0 or no 2nd y-step */
		} while (x < 0);
	}
}

class SpanDex {
	static Initialize() {
		console.log("<span>Dex init");
		this.tileSize = 512;
		this.localDrawing = true;
		this.debug = true;
		//this.testInterval = setInterval(this.TestInterval, 10);
	}

	static TestInterval() {
		const multy = SpanDex.tileSize / 4;

		for (let i = 0; i < 100000; i++) {
			let x = Math.floor(((Math.random() * 2) - 1) * multy);
			let y = Math.floor(((Math.random() * 2) - 1) * multy);

			SpanDex.PutPixelAtPos([x, y], 0xff0047ab);
		}
	}

	static PutPixelAtPos(pos, col, fromSrv = false, clear = true) {
		// find tile pos

		let erase = false;
		if (col instanceof Array || (col instanceof Uint8Array && col.length == 4) || (col instanceof Uint32Array && col.length == 1))
			col = byteArrToHex(col);
		else if (typeof(col) === "number")
			col = byteArrToHex(hextoByteArr(col.toString(16), true));
		else if (col == null)
			erase = true;
		else {
			console.error("invalid color value! ARGB hex number, a Uint8Array/byte array of length 4 | Uint32Array of length 1, or null only!");
			return;
		}

		// col will always be #aarrggbb here, so if the alpha byte is 00 we don't draw anything!
		/*if (col.startsWith("#00"))
			return;*/

		//console.debug("pos", pos, "\ncol", (col == null ? "(erasing)" : col), "\nclearing before?", clear);

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

				if (clear)
					ctx.clearRect(tilePos[0], tilePos[1], 1, 1);

				if (!erase)
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
		if (!fromSrv) {
			let msg = new Uint8Array(19);
			let dv = new DataView(msg.buffer);
			dv.setUint8(0, SpanDex.MsgTypesClient.PIX_Put);
			dv.setInt32(1, pos[0]);
			dv.setInt32(5, pos[1]);
			dv.setUint16(9, 1);

			let colArr = hextoByteArr(col);

			dv.setInt16(11, 0);
			dv.setInt16(13, 0);
			dv.setUint8(15, colArr[1]);
			dv.setUint8(16, colArr[1]);
			dv.setUint8(17, colArr[2]);
			dv.setUint8(18, colArr[3]);
			WebSock.SendMessage(msg);
		}
	}

	static GetTile(coord) {
		let msg = new Uint8Array(9);
		let dv = new DataView(msg.buffer);
		dv.setUint8(0, SpanDex.MsgTypesClient.TIL_Get);
		dv.setInt32(1, coord.x);
		dv.setInt32(5, coord.y);
		WebSock.SendMessage(msg);
	}
};

SpanDex.MsgTypesClient = Object.freeze({
	SYS_Ping: 0b0_000_000,

	PIX_Put: 0b0_001_000,
	PIX_PutRect: 0b0_001_001,
	PIX_Erase: 0b0_001_010,
	PIX_EraseRect: 0b0_001_011,

	TIL_Get: 0b0_010_000,
});

SpanDex.MsgTypesServer = Object.freeze({
	SYS_Pong: 0b1_000_000,
	SYS_Config: 0b1_000_001,

	PIX_Send: 0b1_001_000,
	PIX_SendRect: 0b1_001_001,
	PIX_SendErase: 0b1_001_010,
	PIX_SendEraseRect: 0b1_001_011,

	TIL_Send: 0b1_010_000,
});

document.addEventListener("DOMContentLoaded", () => {
	SpanDex.Initialize();
	WebSock.Connect();

	// nasty... can I avoid this?
	window.UI = UI;
	window.Paint = Paint;
	window.SpanDex = SpanDex;
	window.WebSock = WebSock;
});