import { Bluetooth, Wifi, Radio } from 'lucide-react';
import { SignalData } from '../types';

interface SignalStatsProps {
  signalData: SignalData[] | undefined;
}

export function SignalStats({ signalData }: SignalStatsProps) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center">
          <Bluetooth className="h-8 w-8 text-blue-600" />
          <div className="ml-4">
            <h3 className="text-lg font-semibold">Bluetooth Signals</h3>
            <p className="text-2xl font-bold">
              {signalData?.filter(s => s.type === 'Bluetooth').length || 0}
            </p>
          </div>
        </div>
      </div>
      
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center">
          <Wifi className="h-8 w-8 text-green-600" />
          <div className="ml-4">
            <h3 className="text-lg font-semibold">Wi-Fi Signals</h3>
            <p className="text-2xl font-bold">
              {signalData?.filter(s => s.type === 'Wi-Fi').length || 0}
            </p>
          </div>
        </div>
      </div>
      
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center">
          <Radio className="h-8 w-8 text-purple-600" />
          <div className="ml-4">
            <h3 className="text-lg font-semibold">ADS-B Signals</h3>
            <p className="text-2xl font-bold">
              {signalData?.filter(s => s.type === 'ADS-B').length || 0}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}