import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';
import { SignalData } from '../types';

interface SignalMapProps {
  filteredData: SignalData[];
}

export function SignalMap({ filteredData }: SignalMapProps) {
  return (
    <div className="bg-white rounded-lg shadow p-6 mb-6">
      <h2 className="text-lg font-semibold mb-4">Signal Locations</h2>
      <div className="h-96">
        <MapContainer
          center={[51.505, -0.09]}
          zoom={13}
          className="h-full w-full rounded-lg"
        >
          <TileLayer
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          />
          {filteredData.map((signal, index) => (
            <Marker
              key={index}
              position={[51.505, -0.09]} // Replace with actual coordinates from signal data
            >
              <Popup>
                <div>
                  <h3 className="font-semibold">{signal.type}</h3>
                  <p>Address: {signal.name_address}</p>
                  <p>Strength: {signal.signal_strength}</p>
                  <p>Time: {signal.timestamp}</p>
                </div>
              </Popup>
            </Marker>
          ))}
        </MapContainer>
      </div>
    </div>
  );
}