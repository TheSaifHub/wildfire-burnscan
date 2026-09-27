"use client";

import { MapContainer, TileLayer, ImageOverlay, LayersControl } from "react-leaflet";
import "leaflet/dist/leaflet.css";

export default function FireMap({ bounds, images, apiBase }) {
  const leafletBounds = [
    [bounds.south, bounds.west],
    [bounds.north, bounds.east],
  ];
  const center = [
    (bounds.south + bounds.north) / 2,
    (bounds.west + bounds.east) / 2,
  ];

  return (
    <MapContainer
      center={center}
      bounds={leafletBounds}
      style={{ height: "500px", width: "100%" }}
      className="rounded-lg border"
    >
      <LayersControl position="topright">
        <LayersControl.BaseLayer checked name="Map">
          <TileLayer
            attribution='&copy; OpenStreetMap contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
        </LayersControl.BaseLayer>

        <LayersControl.Overlay checked name="Burn Severity (U-Net)">
          <ImageOverlay url={`${apiBase}${images.severity}`} bounds={leafletBounds} />
        </LayersControl.Overlay>

        <LayersControl.Overlay name="Before (satellite)">
          <ImageOverlay url={`${apiBase}${images.before}`} bounds={leafletBounds} />
        </LayersControl.Overlay>

        <LayersControl.Overlay name="After (satellite)">
          <ImageOverlay url={`${apiBase}${images.after}`} bounds={leafletBounds} />
        </LayersControl.Overlay>
      </LayersControl>
    </MapContainer>
  );
}
