import React from 'react';
import { Lock, Check, Circle, ArrowRight, PlayCircle, Zap, SkipForward } from 'lucide-react';
import { LemonCard } from './LemonCard';
import { CourseDifficultyBadge } from './CourseDifficultyBadge';

export type NodeStatus = 'locked' | 'unlocked' | 'completed' | 'skippable' | 'fast_tracked';

interface RoadmapNodeProps {
  id: string;
  title: string;
  description: string;
  status: NodeStatus;
  difficultyLevel?: number | null;
  mastery?: number;
  confidence?: number;
  isSkipLoading?: boolean;
  reason?: string;
  onClick?: () => void;
  onSkip?: () => void;
  onFastTrack?: () => void;
}

import { useProgress } from '../hooks/useProgress';

export function RoadmapNode({ id, title, description, status, difficultyLevel, mastery, confidence, isSkipLoading, reason, onClick, onSkip, onFastTrack }: RoadmapNodeProps) {
  const isLocked = status === 'locked';
  const isCompleted = status === 'completed';
  const isUnlocked = status === 'unlocked';
  const isSkippable = status === 'skippable';
  const isFastTracked = status === 'fast_tracked';

  const { getCourseProgress } = useProgress();
  const courseProgress = getCourseProgress(id, 5);
  const percent = isCompleted ? 100 : Math.min(courseProgress.percentage, 99);

  const statusConfig: Record<NodeStatus, {
    icon: React.ComponentType<{ className?: string }>;
    bgColor: string;
    textColor: string;
    borderColor: string;
    iconColor: string;
  }> = {
    locked: {
      icon: Lock,
      bgColor: 'bg-muted',
      textColor: 'text-muted-foreground',
      borderColor: 'border-border',
      iconColor: 'text-muted-foreground',
    },
    unlocked: {
      icon: Circle,
      bgColor: 'bg-card',
      textColor: 'text-foreground',
      borderColor: 'border-border',
      iconColor: 'text-accent',
    },
    completed: {
      icon: Check,
      bgColor: 'bg-card',
      textColor: 'text-foreground',
      borderColor: 'border-[#388600]',
      iconColor: 'text-[#388600]',
    },
    skippable: {
      icon: SkipForward,
      bgColor: 'bg-card',
      textColor: 'text-foreground',
      borderColor: 'border-amber-400',
      iconColor: 'text-amber-500',
    },
    fast_tracked: {
      icon: Zap,
      bgColor: 'bg-card',
      textColor: 'text-foreground',
      borderColor: 'border-blue-400',
      iconColor: 'text-blue-500',
    },
  };

  const config = statusConfig[status];
  const Icon = config.icon;

  const iconBgClass = isCompleted
    ? 'bg-green-100'
    : isUnlocked
    ? 'bg-blue-100'
    : isSkippable
    ? 'bg-amber-100'
    : isFastTracked
    ? 'bg-blue-100'
    : 'bg-gray-200';

  const iconColorClass = isCompleted
    ? 'text-green-600'
    : isUnlocked
    ? 'text-blue-600'
    : isSkippable
    ? 'text-amber-500'
    : isFastTracked
    ? 'text-blue-600'
    : 'text-gray-500';

  const statusLabel = isCompleted
    ? '✓ Completed'
    : isUnlocked
    ? '● In Progress'
    : isSkippable
    ? '⟩ Skip Available'
    : isFastTracked
    ? '⚡ Fast Track'
    : '○ Locked';

  const statusLabelColor = isCompleted
    ? 'text-green-600'
    : isUnlocked
    ? 'text-blue-600'
    : isSkippable
    ? 'text-amber-500'
    : isFastTracked
    ? 'text-blue-500'
    : 'text-gray-500';

  return (
    <div
      className={`
        relative border ${config.borderColor} bg-card rounded-xl p-6
        transition-all duration-300 shadow-sm flex flex-col h-full
        ${!isLocked && 'hover:shadow-md hover:-translate-y-1 cursor-pointer hover:border-blue-300'}
        ${isLocked && 'opacity-70 cursor-not-allowed bg-muted/30'}
      `}
      onClick={!isLocked ? onClick : undefined}
    >
      <div className="flex items-start gap-4 mb-4">
        <div className={`flex-shrink-0 w-12 h-12 rounded-full ${iconBgClass} flex items-center justify-center`}>
          <Icon className={`w-6 h-6 ${iconColorClass}`} />
        </div>

        <div className="flex-1 min-w-0 pt-1">
          <h4 className={`font-semibold text-lg line-clamp-2 ${config.textColor}`}>{title}</h4>
        </div>
      </div>

      <p className={`text-sm mb-6 flex-1 line-clamp-3 ${isLocked ? 'text-gray-400' : 'text-gray-600'}`}>
        {description}
      </p>

      <div className="mt-auto space-y-4">

        {/* Progress Bar Injection */}
        {!isLocked && (
          <div className="space-y-3 mb-2">
            <div className="space-y-1.5">
              <div className="flex justify-between text-xs font-semibold text-gray-500">
                <span>Course Progress</span>
                <span className={isCompleted ? 'text-green-600' : 'text-blue-600'}>{percent}%</span>
              </div>
              <div className="w-full bg-gray-100 rounded-full h-1.5 overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-500 ${isCompleted ? 'bg-green-500' : 'bg-blue-600'}`}
                  style={{ width: `${percent}%` }}
                ></div>
              </div>
            </div>

            {(mastery !== undefined || confidence !== undefined) && (
              <div className="flex items-center gap-2 mt-2">
                <div className="bg-primary/10 border-primary/20 border px-2 py-1 rounded-md flex-1 text-center">
                  <div className="text-[9px] uppercase font-bold text-primary">Mastery</div>
                  <div className="text-sm font-bold">{Math.round(mastery || 0)}%</div>
                </div>
                <div className="bg-muted border px-2 py-1 rounded-md flex-1 text-center">
                  <div className="text-[9px] uppercase font-bold text-muted-foreground">Confidence</div>
                  <div className="text-sm font-bold">{Math.round((confidence || 0) * 100)}%</div>
                </div>
              </div>
            )}
          </div>
        )}

        <div className="flex items-center justify-between text-xs font-medium bg-gray-50 rounded-lg p-3 border">
          <div className="flex flex-col gap-1">
            <span className="text-gray-500 uppercase tracking-wider text-[10px]">Difficulty</span>
            <CourseDifficultyBadge requiredLevel={difficultyLevel} />
          </div>
          <div className="w-px h-8 bg-gray-200"></div>
          <div className="flex flex-col gap-1 items-end">
            <span className="text-gray-500 uppercase tracking-wider text-[10px]">Status</span>
            <span className={`${statusLabelColor} flex items-center gap-1`}>
              {statusLabel}
            </span>
          </div>
        </div>

        {!isLocked && (
          <div className="flex flex-col gap-2">
            {isSkippable && onSkip && (
              <button
                className="w-full flex items-center justify-center gap-2 py-2.5 rounded-lg font-medium transition-colors bg-amber-50 text-amber-700 hover:bg-amber-100 border border-amber-200 disabled:opacity-50 disabled:cursor-not-allowed"
                disabled={isSkipLoading}
                onClick={(e) => { e.stopPropagation(); onSkip(); }}
              >
                {isSkipLoading ? 'Skipping…' : 'Skip'}
                {!isSkipLoading && <SkipForward className="w-4 h-4" />}
              </button>
            )}
            {isFastTracked && onFastTrack && (
              <button
                className="w-full flex items-center justify-center gap-2 py-2.5 rounded-lg font-medium transition-colors bg-blue-600 text-white hover:bg-blue-700"
                onClick={(e) => { e.stopPropagation(); onFastTrack(); }}
              >
                → Quiz
                <Zap className="w-4 h-4" />
              </button>
            )}
            {!isSkippable && !isFastTracked && (
              <button className={`w-full flex items-center justify-center gap-2 py-2.5 rounded-lg font-medium transition-colors ${isCompleted ? 'bg-green-50 text-green-700 hover:bg-green-100' : 'bg-blue-600 text-white hover:bg-blue-700'}`}>
                {isCompleted ? 'Review Content' : 'Start Learning'}
                {isCompleted ? <ArrowRight className="w-4 h-4" /> : <PlayCircle className="w-4 h-4" />}
              </button>
            )}
          </div>
        )}

        {reason && (
          <p className="text-xs italic opacity-60 mt-1 truncate" title={reason}>{reason}</p>
        )}
      </div>

      {isCompleted && (
        <div className="absolute -top-2 -right-2 w-8 h-8 focus:outline-none shadow-sm border border-green-200 bg-green-500 rounded-full flex items-center justify-center translate-x-1/4 -translate-y-1/4">
          <Check className="w-5 h-5 text-white" />
        </div>
      )}
    </div>
  );
}
