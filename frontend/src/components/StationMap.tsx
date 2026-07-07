import Feature from "ol/Feature.js";
import type { FeatureLike } from "ol/Feature.js";
import OLMap from "ol/Map.js";
import View from "ol/View.js";
import { boundingExtent } from "ol/extent.js";
import Point from "ol/geom/Point.js";
import TileLayer from "ol/layer/Tile.js";
import VectorLayer from "ol/layer/Vector.js";
import { fromLonLat } from "ol/proj.js";
import Cluster from "ol/source/Cluster.js";
import OSM from "ol/source/OSM.js";
import VectorSource from "ol/source/Vector.js";
import { Circle, Fill, Icon, Stroke, Style, Text } from "ol/style.js";
import { useEffect, useId, useMemo, useRef } from "react";

import type { Coordinates } from "../lib/geo";
import { getFuelStatus, statusTone } from "../lib/status";
import type { FuelType, Station } from "../types/domain";

const SARATOV_CENTER = fromLonLat([46.0343, 51.5336]);

type StationMapProps = {
  stations: Station[];
  selectedStationId: number | null;
  fuelType: FuelType;
  userLocation: Coordinates | null;
  onSelect: (station: Station) => void;
};

const toneColors = {
  positive: "#159c61",
  negative: "#d05248",
  unknown: "#d58a1f",
  expired: "#8b8a84",
};

const styleCache = new globalThis.Map<string, Style>();
const clusterStyleCache = new globalThis.Map<string, Style>();
const userLocationStyle = new Style({
  image: new Circle({
    radius: 8,
    fill: new Fill({ color: "#216c95" }),
    stroke: new Stroke({ color: "#ffffff", width: 3 }),
  }),
  zIndex: 20,
});

function markerSvg(color: string, isSelected: boolean): string {
  const stroke = isSelected ? "#1f2d33" : "#ffffff";
  const strokeWidth = isSelected ? 3 : 2;
  const scale = isSelected ? 1.08 : 1;
  return `
    <svg xmlns="http://www.w3.org/2000/svg" width="34" height="42" viewBox="0 0 34 42">
      <g transform="translate(17 19) scale(${scale}) translate(-17 -19)">
        <ellipse cx="17" cy="38" rx="7" ry="2.6" fill="rgba(31,45,51,.22)"/>
        <path d="M17 39C11 30.7 6 25.2 6 17.3 6 10.8 10.9 6 17 6s11 4.8 11 11.3c0 7.9-5 13.4-11 21.7Z" fill="${color}" stroke="${stroke}" stroke-width="${strokeWidth}" />
        <circle cx="17" cy="17.5" r="5.2" fill="#fff" fill-opacity=".94"/>
        <path d="M14.6 14.2h4.1c.8 0 1.4.6 1.4 1.4v5.1h-6.9v-5.1c0-.8.6-1.4 1.4-1.4Zm.4 2.1h3.3v-1H15v1Zm5.1.2 1.7 1.4v3.2c0 .5.4.9.9.9s.9-.4.9-.9v-4.8l-1.1-.9" fill="none" stroke="${color}" stroke-width="1.15" stroke-linecap="round" stroke-linejoin="round"/>
      </g>
    </svg>
  `;
}

function makePointStyle(tone: keyof typeof toneColors, isSelected: boolean): Style {
  const cacheKey = `${tone}-${isSelected ? "selected" : "idle"}`;
  const cached = styleCache.get(cacheKey);
  if (cached) {
    return cached;
  }

  const svg = markerSvg(toneColors[tone], isSelected);
  const style = new Style({
    image: new Icon({
      anchor: [0.5, 1],
      crossOrigin: "anonymous",
      scale: isSelected ? 1.02 : 0.86,
      src: `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(svg)}`,
    }),
    zIndex: isSelected ? 10 : 1,
  });
  styleCache.set(cacheKey, style);
  return style;
}

function stationLayerStyle(feature: FeatureLike): Style {
  const clusteredFeatures = feature.get("features") as Array<Feature<Point>> | undefined;
  if (clusteredFeatures && clusteredFeatures.length > 1) {
    return makeClusterStyle(clusteredFeatures);
  }

  const stationFeature = clusteredFeatures?.[0] ?? feature;
  const tone = stationFeature.get("tone") as keyof typeof toneColors;
  const isSelected = Boolean(stationFeature.get("isSelected"));
  return makePointStyle(tone, isSelected);
}

function createTileLayer(): TileLayer<OSM> {
  return new TileLayer({
    source: new OSM({
      attributions: "© OpenStreetMap",
    }),
    className: "station-map__tiles",
  });
}

function fitInitialView(map: OLMap, source: VectorSource<Feature<Point>>): void {
  const extent = source.getExtent();
  if (!extent || extent.some((value) => !Number.isFinite(value))) {
    return;
  }

  map.getView().fit(extent, {
    duration: 240,
    maxZoom: 12,
    padding: [42, 42, 190, 42],
  });
}

function updateCursor(map: OLMap): void {
  map.on("pointermove", (event) => {
    const target = map.getTargetElement();
    target.style.cursor = map.hasFeatureAtPixel(event.pixel) ? "pointer" : "";
  });
}

function makeClusterStyle(features: Array<Feature<Point>>): Style {
  const hasFreshPositive = features.some((feature) => feature.get("tone") === "positive");
  const hasFreshUnknown = features.some((feature) => feature.get("tone") === "unknown");
  const tone = hasFreshPositive ? "positive" : hasFreshUnknown ? "unknown" : "expired";
  const size = features.length;
  const radius = Math.min(24, 15 + Math.log(size) * 4);
  const cacheKey = `${tone}-${size}`;
  const cached = clusterStyleCache.get(cacheKey);
  if (cached) {
    return cached;
  }

  const color = toneColors[tone];
  const style = new Style({
    image: new Circle({
      radius,
      fill: new Fill({ color }),
      stroke: new Stroke({ color: "#ffffff", width: 3 }),
    }),
    text: new Text({
      fill: new Fill({ color: "#ffffff" }),
      font: "700 12px Inter, system-ui, sans-serif",
      text: String(size),
    }),
    zIndex: 5,
  });
  clusterStyleCache.set(cacheKey, style);
  return style;
}

function zoomToCluster(map: OLMap, features: Array<Feature<Point>>): void {
  const coordinates = features
    .map((feature) => feature.getGeometry()?.getCoordinates())
    .filter((coordinate): coordinate is [number, number] => Array.isArray(coordinate));

  if (coordinates.length < 2) {
    return;
  }

  map.getView().fit(boundingExtent(coordinates), {
    duration: 220,
    maxZoom: 15,
    padding: [64, 64, 210, 64],
  });
}

function addStationClickHandler(
  map: OLMap,
  stationById: globalThis.Map<number, Station>,
  onSelect: (station: Station) => void,
): void {
  map.on("click", (event) => {
    const feature = map.forEachFeatureAtPixel(event.pixel, (candidate) => candidate, {
      hitTolerance: 8,
    });
    const clusteredFeatures = feature?.get("features") as Array<Feature<Point>> | undefined;
    if (clusteredFeatures && clusteredFeatures.length > 1) {
      zoomToCluster(map, clusteredFeatures);
      return;
    }

    const stationFeature = clusteredFeatures?.[0] ?? feature;
    const stationId = stationFeature?.get("stationId") as number | undefined;
    if (!stationId) {
      return;
    }

    const station = stationById.get(stationId);
    if (station) {
      onSelect(station);
    }
  });
}

function stationToFeature(station: Station, fuelType: FuelType, selectedStationId: number | null): Feature<Point> {
  const status = getFuelStatus(station, fuelType);
  const tone = statusTone(status);
  const feature = new Feature({
    geometry: new Point(fromLonLat([Number(station.lon), Number(station.lat)])),
    stationId: station.id,
    tone,
    isSelected: station.id === selectedStationId,
  });
  feature.setId(station.id);
  return feature;
}

function createUserLocationFeature(userLocation: Coordinates): Feature<Point> {
  return new Feature({
    geometry: new Point(fromLonLat([userLocation.lon, userLocation.lat])),
  });
}

export function StationMap({ stations, selectedStationId, fuelType, userLocation, onSelect }: StationMapProps) {
  const reactId = useId();
  const mapElementId = `station-map-${reactId.replaceAll(":", "")}`;
  const mapRef = useRef<OLMap | null>(null);
  const sourceRef = useRef<VectorSource<Feature<Point>> | null>(null);
  const userSourceRef = useRef<VectorSource<Feature<Point>> | null>(null);
  const hasFitInitialViewRef = useRef(false);

  const stationById = useMemo(() => {
    return new globalThis.Map<number, Station>(stations.map((station) => [station.id, station]));
  }, [stations]);

  useEffect(() => {
    const source = new VectorSource<Feature<Point>>();
    const clusterSource = new Cluster({
      distance: 34,
      minDistance: 14,
      source,
    });
    const stationLayer = new VectorLayer({
      source: clusterSource,
      style: stationLayerStyle,
      updateWhileAnimating: true,
      updateWhileInteracting: true,
    });
    const userSource = new VectorSource<Feature<Point>>();
    const userLocationLayer = new VectorLayer({
      source: userSource,
      style: userLocationStyle,
      updateWhileAnimating: true,
      updateWhileInteracting: true,
    });

    const map = new OLMap({
      target: mapElementId,
      layers: [createTileLayer(), stationLayer, userLocationLayer],
      view: new View({
        center: SARATOV_CENTER,
        zoom: 11,
      }),
      controls: [],
    });

    updateCursor(map);
    addStationClickHandler(map, stationById, onSelect);

    mapRef.current = map;
    sourceRef.current = source;
    userSourceRef.current = userSource;

    return () => {
      map.setTarget(undefined);
      mapRef.current = null;
      sourceRef.current = null;
      userSourceRef.current = null;
    };
  }, [mapElementId, onSelect, stationById]);

  useEffect(() => {
    const source = sourceRef.current;
    if (!source) {
      return;
    }

    const features = stations.map((station) => stationToFeature(station, fuelType, selectedStationId));

    source.clear();
    source.addFeatures(features);

    const map = mapRef.current;
    if (map && !hasFitInitialViewRef.current && features.length > 0) {
      fitInitialView(map, source);
      hasFitInitialViewRef.current = true;
    }
  }, [stations, selectedStationId, fuelType]);

  useEffect(() => {
    const map = mapRef.current;
    const userSource = userSourceRef.current;
    if (!map || !userSource) {
      return;
    }

    userSource.clear();
    if (!userLocation) {
      return;
    }

    userSource.addFeature(createUserLocationFeature(userLocation));
    map.getView().animate({
      center: fromLonLat([userLocation.lon, userLocation.lat]),
      zoom: Math.max(map.getView().getZoom() ?? 11, 12),
      duration: 240,
    });
  }, [userLocation]);

  useEffect(() => {
    const map = mapRef.current;
    const selected = stations.find((station) => station.id === selectedStationId);
    if (!map || !selected) {
      return;
    }

    map.getView().animate({
      center: fromLonLat([Number(selected.lon), Number(selected.lat)]),
      zoom: Math.max(map.getView().getZoom() ?? 11, 13),
      duration: 220,
    });
  }, [selectedStationId, stations]);

  return <div id={mapElementId} className="station-map" />;
}
