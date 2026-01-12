'use client';

import { GenerationMode } from '@/lib/types';

interface ModeSidebarProps {
  currentMode: GenerationMode;
  onModeChange: (mode: GenerationMode) => void;
}

export default function ModeSidebar({ currentMode, onModeChange }: ModeSidebarProps) {
  const modes = [
    {
      id: 'full' as GenerationMode,
      name: '完整模式',
      icon: '📝',
    },
    {
      id: 'quick' as GenerationMode,
      name: '快速模式',
      icon: '⚡',
    },
  ];

  return (
    <div className="w-16 h-full bg-white dark:bg-gray-900 border-r border-gray-300 dark:border-gray-700 flex flex-col items-center py-4 gap-4">
      {modes.map((mode) => (
        <button
          key={mode.id}
          onClick={() => onModeChange(mode.id)}
          title={mode.name}
          className={`
            w-9 h-9 rounded-lg transition-all duration-200
            flex items-center justify-center
            ${
              currentMode === mode.id
                ? 'bg-gray-800 text-white shadow-md hover:bg-gray-900'
                : 'bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-gray-100 hover:bg-gray-200 dark:hover:bg-gray-750 border border-gray-300 dark:border-gray-700'
            }
          `}
        >
          <span className="text-xl">{mode.icon}</span>
        </button>
      ))}
    </div>
  );
}
