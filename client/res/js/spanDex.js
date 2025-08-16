import L, {Map, CRS, ImageOverlay, TileLayer} from 'leaflet';

class UI {
	static Initialize() {
		this.map = new Map("map", {
			crs: CRS.Simple,
			minZoom: -2,
			maxZoom: 8
		});
		this.map.setView( [256, 256], 0);
		new ImageOverlay("https://block57.net/_res/img/test.png", [[0, 0], [512, 512]], {className: "pointFiltered"}).addTo(this.map);
	}
}

class SpanDex {
	static Initialize() {
		console.log("bepis");
	}
}

document.addEventListener("DOMContentLoaded", () => {
	UI.Initialize();
	SpanDex.Initialize();
});


