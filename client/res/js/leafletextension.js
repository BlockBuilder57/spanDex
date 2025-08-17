import L, {Map, CRS, ImageOverlay, TileLayer, GridLayer, Control} from "leaflet";

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
	createTile(coords, done) {
		const error = null;

		// create a <canvas> element for drawing
		const tile = L.DomUtil.create("canvas", "leaflet-tile");

		// setup tile width and height according to the options
		const size = this.getTileSize();
		tile.width = size.x;
		tile.height = size.y;

		// draw something asynchronously and pass the tile to the done() callback
		setTimeout(function() {
			done(error, tile);
		}, 10);

		return tile;
	}
}

export {SpanDexControl, CanvasLayer};