class UI {
	static Initialize() {
		this.map = new L.Map("map", {
			crs: L.CRS.Simple,
			minZoom: 1,
			maxZoom: 8
		});
		this.map.setView( [256, 256], 1);
		//new L.ImageOverlay("res/img/uv.png", [[0, 0], [512, 512]], {className: "pointFiltered"}).addTo(this.map);
		/*new L.TileLayer("res/img/uv.png", {
			tileSize: 512,
			minNativeZoom: 0,
			maxNativeZoom: 0,
			className: "pointFiltered"
		}).addTo(this.map);*/

		this.canvasLayer = new CanvasLayer({
			tileSize: 512,
			minNativeZoom: 0,
			maxNativeZoom: 0,
			className: "pointFiltered"
		}).addTo(this.map);
		this.canvasLayer.on("tileunload", (e) => {
			console.log(e);
		});

		let controls = document.getElementById("controls");
		if (controls != null) {
			for (let i = 0; i < controls.children.length; i++) {
				let child = controls.children[i];
				let ctrl = new SpanDexControl(child);
				ctrl.addTo(this.map);
			}
		}

		document.getElementById("btnRecenter").onclick = () => { UI.map.setView([0, 0], 0); }
	}

	static GetCanvasTileAtPoint(point) {
		console.log(this.canvasLayer);
	}
}

export default {UI};