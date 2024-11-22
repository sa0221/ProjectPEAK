import { useState } from 'react';
import { useQuery, QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Navbar } from './components/Navbar';
import { ControlPanel } from './components/ControlPanel';
import { SignalStats } from './components/SignalStats';
import { SignalChart } from './components/SignalChart';
import { SignalMap } from './components/SignalMap';
import { SignalList } from './components/SignalList';
import { SignalData } from './types';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: false,
      staleTime: 30000,
    },
  },
});

function AppContent() {
  const [isCollecting, setIsCollecting] = useState(false);
  const [selectedSignalType, setSelectedSignalType] = useState<string>('all');

  const { data: signalData, refetch } = useQuery<SignalData[]>({
    queryKey: ['signals'],
    queryFn: () => fetch('/api/data').then(res => res.json()),
    refetchInterval: isCollecting ? 2000 : false,
  });

  const handleStartCollection = async () => {
    await fetch('/api/start', { method: 'POST' });
    setIsCollecting(true);
  };

  const handleStopCollection = async () => {
    await fetch('/api/stop', { method: 'POST' });
    setIsCollecting(false);
  };

  const handleResetData = async () => {
    await fetch('/api/reset', { method: 'POST' });
    refetch();
  };

  const handleSaveData = async () => {
    await fetch('/api/save', { method: 'POST' });
  };

  const filteredData = signalData?.filter(signal => 
    selectedSignalType === 'all' || signal.type === selectedSignalType
  ) || [];

  return (
    <div className="min-h-screen bg-gray-100">
      <Navbar />
      <main className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
        <ControlPanel
          isCollecting={isCollecting}
          selectedSignalType={selectedSignalType}
          onStartCollection={handleStartCollection}
          onStopCollection={handleStopCollection}
          onResetData={handleResetData}
          onSaveData={handleSaveData}
          onSignalTypeChange={setSelectedSignalType}
        />
        <SignalStats signalData={signalData} />
        <SignalChart filteredData={filteredData} />
        <SignalMap filteredData={filteredData} />
        <SignalList filteredData={filteredData} />
      </main>
    </div>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AppContent />
    </QueryClientProvider>
  );
}