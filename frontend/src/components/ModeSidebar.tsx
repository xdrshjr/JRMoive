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
    <div className="w-full h-full bg-white dark:bg-gray-900 border-r border-gray-200 dark:border-gray-700 flex flex-col">
      {/* Header */}
      <div className="p-6 border-b border-gray-200 dark:border-gray-700">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
          生成模式
        </h2>
      </div>

      {/* Mode List */}
      <div className="flex-1 p-4 space-y-2">
        {modes.map((mode) => (
          <button
            key={mode.id}
            onClick={() => onModeChange(mode.id)}
            className={`
              w-full text-left px-4 py-3 rounded-lg transition-all duration-200
              flex items-center gap-3
              ${
                currentMode === mode.id
                  ? 'bg-blue-600 text-white shadow-md hover:bg-blue-700'
                  : 'bg-gray-50 dark:bg-gray-800 text-gray-900 dark:text-gray-100 hover:bg-gray-100 dark:hover:bg-gray-750 border border-gray-200 dark:border-gray-700'
              }
            `}
          >
            {/* Icon */}
            <span className="text-2xl flex-shrink-0">{mode.icon}</span>

            {/* Name */}
            <span className="font-medium text-base">{mode.name}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
