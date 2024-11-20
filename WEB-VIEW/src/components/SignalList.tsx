import { Bluetooth, Wifi, Radio } from 'lucide-react';
import { SignalData } from '../types';

interface SignalListProps {
  filteredData: SignalData[];
}

export function SignalList({ filteredData }: SignalListProps) {
  return (
    <div className="bg-white rounded-lg shadow overflow-hidden">
      <div className="px-6 py-4 border-b border-gray-200">
        <h2 className="text-lg font-semibold">Recent Signals</h2>
      </div>
      <div className="divide-y divide-gray-200">
        {filteredData.map((signal, index) => (
          <div key={index} className="px-6 py-4">
            <div className="flex items-center">
              {signal.type === 'Bluetooth' && <Bluetooth className="h-5 w-5 text-blue-600" />}
              {signal.type === 'Wi-Fi' && <Wifi className="h-5 w-5 text-green-600" />}
              {signal.type === 'ADS-B' && <Radio className="h-5 w-5 text-purple-600" />}
              <div className="ml-4">
                <h3 className="text-sm font-medium">{signal.name_address}</h3>
                <p className="text-sm text-gray-500">
                  Signal Strength: {signal.signal_strength} | Time: {signal.timestamp}
                </p>
                {signal.additional_info && (
                  <p className="text-sm text-gray-500">{signal.additional_info}</p>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}