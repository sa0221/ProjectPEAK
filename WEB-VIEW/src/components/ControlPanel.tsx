import { PlayCircle, StopCircle, RotateCw, Save } from 'lucide-react';

interface ControlPanelProps {
  isCollecting: boolean;
  selectedSignalType: string;
  onStartCollection: () => void;
  onStopCollection: () => void;
  onResetData: () => void;
  onSaveData: () => void;
  onSignalTypeChange: (type: string) => void;
}

export function ControlPanel({
  isCollecting,
  selectedSignalType,
  onStartCollection,
  onStopCollection,
  onResetData,
  onSaveData,
  onSignalTypeChange,
}: ControlPanelProps) {
  return (
    <div className="bg-white rounded-lg shadow p-6 mb-6">
      <div className="flex space-x-4">
        <button
          onClick={isCollecting ? onStopCollection : onStartCollection}
          className={`flex items-center px-4 py-2 rounded-md ${
            isCollecting 
              ? 'bg-red-600 hover:bg-red-700 text-white'
              : 'bg-green-600 hover:bg-green-700 text-white'
          }`}
        >
          {isCollecting ? (
            <>
              <StopCircle className="h-5 w-5 mr-2" />
              Stop Collection
            </>
          ) : (
            <>
              <PlayCircle className="h-5 w-5 mr-2" />
              Start Collection
            </>
          )}
        </button>
        
        <button
          onClick={onResetData}
          className="flex items-center px-4 py-2 bg-yellow-600 hover:bg-yellow-700 text-white rounded-md"
        >
          <RotateCw className="h-5 w-5 mr-2" />
          Reset Data
        </button>
        
        <button
          onClick={onSaveData}
          className="flex items-center px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md"
        >
          <Save className="h-5 w-5 mr-2" />
          Save Data
        </button>

        <select
          value={selectedSignalType}
          onChange={(e) => onSignalTypeChange(e.target.value)}
          className="rounded-md border-gray-300 shadow-sm focus:border-indigo-300 focus:ring focus:ring-indigo-200 focus:ring-opacity-50"
        >
          <option value="all">All Signals</option>
          <option value="Bluetooth">Bluetooth</option>
          <option value="Wi-Fi">Wi-Fi</option>
          <option value="ADS-B">ADS-B</option>
        </select>
      </div>
    </div>
  );
}