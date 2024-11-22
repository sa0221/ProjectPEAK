import { Radio } from 'lucide-react';

export function Navbar() {
  return (
    <nav className="bg-white shadow-lg">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          <div className="flex items-center">
            <Radio className="h-8 w-8 text-indigo-600" />
            <span className="ml-2 text-xl font-bold">Signal Collection Dashboard</span>
          </div>
        </div>
      </div>
    </nav>
  );
}