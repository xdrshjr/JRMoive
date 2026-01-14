/**
 * StatusBadge Component
 *
 * Displays a color-coded status badge for projects with animations
 */

import React from 'react';
import { ProjectStatus } from '@/lib/types';

interface StatusBadgeProps {
  status: ProjectStatus;
  className?: string;
}

const statusConfig: Record<ProjectStatus, {
  label: string;
  bgColor: string;
  textColor: string;
  icon: string;
  animate?: boolean;
}> = {
  pending: {
    label: 'Pending',
    bgColor: 'bg-[#FF9500]',
    textColor: 'text-white',
    icon: '⏳',
  },
  processing: {
    label: 'Generating...',
    bgColor: 'bg-[#007AFF]',
    textColor: 'text-white',
    icon: '⚡',
    animate: true,
  },
  completed: {
    label: 'Completed',
    bgColor: 'bg-[#34C759]',
    textColor: 'text-white',
    icon: '✓',
  },
  failed: {
    label: 'Failed',
    bgColor: 'bg-[#FF3B30]',
    textColor: 'text-white',
    icon: '✕',
  },
  cancelled: {
    label: 'Cancelled',
    bgColor: 'bg-gray-500',
    textColor: 'text-white',
    icon: '⊘',
  },
};

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, className = '' }) => {
  const config = statusConfig[status];

  return (
    <div
      className={`
        inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full
        text-xs font-medium
        ${config.bgColor} ${config.textColor}
        ${config.animate ? 'animate-pulse' : ''}
        ${className}
      `}
    >
      <span className="text-sm">{config.icon}</span>
      <span>{config.label}</span>
    </div>
  );
};

export default StatusBadge;
