import React, { useState, useEffect } from 'react';
import MapGL, { Marker } from 'react-map-gl/mapbox';
import 'mapbox-gl/dist/mapbox-gl.css';

const MAPBOX_TOKEN = 'pk.eyJ1IjoicmljYXJkb2NtYWNoYWRvIiwiYSI6ImNtMm56a3h4bTAxYXgyanIxc245dndpdXMifQ.Mzuf4AP-Xu4l9bmpfUFZUg';

const TRAFFIC_LIGHTS = [
  { id: 'west', lat: 38.726273, lon: -9.135082, signalGroup: 4 },
  { id: 'north', lat: 38.726467, lon: -9.135025, signalGroup: 1 },
  { id: 'east', lat: 38.726350, lon: -9.134775, signalGroup: 2 },
  { id: 'south', lat: 38.726210, lon: -9.134818, signalGroup: 3 },
];

const getVehicleRotation = (lat, lon, isAmbulance) => {
  const centerLat = 38.726349;
  const centerLon = -9.134933;
  
  const isNorthRoad = lat > centerLat + 0.0001;
  const isSouthRoad = lat < centerLat - 0.0001;
  const isEastRoad = lon > centerLon + 0.0001;
  const isWestRoad = lon < centerLon - 0.0001;
  
  if (isAmbulance) {
    if (isNorthRoad) return 0;
    if (isSouthRoad) return 180;
    if (isEastRoad) return 90;
    if (isWestRoad) return -90;
  } else {
    if (isNorthRoad) return 90;
    if (isSouthRoad) return -90;
    if (isEastRoad) return 180;
    if (isWestRoad) return 0;
  }
  
  return 0; 
};

export default function App() {
  const [vehicles, setVehicles] = useState({});
  const [greenLight, setGreenLight] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [vehiclesResponse, lightsResponse] = await Promise.all([
          fetch('http://localhost:5000/api/v1/vehicles'),
          fetch('http://localhost:5000/api/v1/green')
        ]);

        if (vehiclesResponse.ok && lightsResponse.ok) {
          const vehiclesData = await vehiclesResponse.json();
          const lightsData = await lightsResponse.json();
          
          setVehicles(vehiclesData);
          setGreenLight(lightsData.semáforo_verde);
        }
      } catch (error) {
        console.error('API Error:', error);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 2000);
    return () => clearInterval(interval);
  }, []);

  const viewState = {
    longitude: -9.134933,
    latitude: 38.726349,
    zoom: 18.5,
    bearing: 5,
    pitch: 0,
  };

  return (
    <div className="app-container" style={{ backgroundColor: '#333', height: '100vh', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
      <header className="app-header" style={{ padding: '1rem', color: '#fff' }}>

      </header>

      <div style={{ backgroundColor: '#444', padding: '1rem', borderRadius: '8px', boxShadow: '0 0 20px rgba(0,0,0,0.5)' }}>
        <MapGL
          {...viewState}
          mapboxAccessToken={MAPBOX_TOKEN}
          mapStyle="mapbox://styles/mapbox/dark-v11"
          style={{ width: 1400, height: 600, borderRadius: '6px' }}
          dragPan={false}
          dragRotate={false}
          scrollZoom={false}
          doubleClickZoom={false}
          touchZoomRotate={false}
          interactive={false}
        >
          {TRAFFIC_LIGHTS.map(light => (
            <Marker key={light.id} longitude={light.lon} latitude={light.lat} anchor="bottom">
              <img
                src={greenLight === light.signalGroup ? "/green.png" : "/red.png"}
                alt={`Traffic Light - ${light.id}`}
                style={{ width: 40, height: 40 }}
              />
            </Marker>
          ))}

          {Object.entries(vehicles).map(([id, vehicle]) => {
            const rotation = getVehicleRotation(vehicle.latitude, vehicle.longitude, vehicle.isAmbulance);
            
            return (
              <Marker 
                key={id} 
                longitude={vehicle.longitude} 
                latitude={vehicle.latitude} 
                anchor="center"
              >
                <div style={{ position: 'relative' }}>
                  <img
                    src={vehicle.isAmbulance ? "/ambulance.png" : "/car.png"}
                    alt={vehicle.isAmbulance ? 'Ambulância' : 'Carro'}
                    style={{ 
                      width: vehicle.isAmbulance ? 35 : 30, 
                      height: vehicle.isAmbulance ? 35 : 30,
                      transform: `rotate(${rotation}deg)`,
                      transition: 'transform 0.3s ease',
                      animation: vehicle.isAmbulance ? 'pulse 2s infinite' : 'none'
                    }}
                  />
                  
                  {vehicle.isAmbulance && (
                    <div style={{
                      position: 'absolute',
                      top: '-5px',
                      right: '-5px',
                      fontSize: '12px',
                      animation: 'blink 1s infinite'
                    }}>
                    </div>
                  )}
                </div>
              </Marker>
            );
          })}
        </MapGL>
      </div>
    </div>
  );
}
