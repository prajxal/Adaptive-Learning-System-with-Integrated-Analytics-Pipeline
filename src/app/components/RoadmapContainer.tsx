import React from 'react';
import { RoadmapNode, NodeStatus } from './RoadmapNode';

export interface RoadmapTopic {
  id: string;
  title: string;
  description: string;
  status: NodeStatus;
  /** Numeric difficulty on the ELO scale (800–2000). Optional to avoid breaking callers without the field. */
  difficultyLevel?: number | null;
  stage: number;
  mastery?: number;
  confidence?: number;
  isSkipLoading?: boolean;
  reason?: string;
  onSkip?: () => void;
  onFastTrack?: () => void;
}

interface RoadmapContainerProps {
  topics: RoadmapTopic[];
  onTopicClick: (topic: RoadmapTopic) => void;
}

export function RoadmapContainer({ topics, onTopicClick }: RoadmapContainerProps) {
  // Group topics by stage
  const stages = topics.reduce((acc, topic) => {
    if (!acc[topic.stage]) {
      acc[topic.stage] = [];
    }
    acc[topic.stage].push(topic);
    return acc;
  }, {} as Record<number, RoadmapTopic[]>);

  const stageNumbers = Object.keys(stages).map(Number).sort((a, b) => a - b);

  return (
    <div className="space-y-8">
      {stageNumbers.map((stageNum, index) => (
        <div key={stageNum} className="relative">
          {/* Stage Label */}
          <div className="flex items-center gap-3 mb-4">
            <div className="w-8 h-8 rounded-full bg-accent text-accent-foreground flex items-center justify-center font-medium">
              {stageNum}
            </div>
            <h3 className="font-medium">Stage {stageNum}</h3>
          </div>

          {/* Topics Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pl-11">
            {stages[stageNum].map((topic) => (
              <RoadmapNode
                key={topic.id}
                id={topic.id}
                title={topic.title}
                description={topic.description}
                status={topic.status}
                difficultyLevel={topic.difficultyLevel}
                mastery={topic.mastery}
                confidence={topic.confidence}
                isSkipLoading={topic.isSkipLoading}
                reason={topic.reason}
                onSkip={topic.onSkip}
                onFastTrack={topic.onFastTrack}
                onClick={() => onTopicClick(topic)}
              />
            ))}
          </div>

          {/* Connector Line */}
          {index < stageNumbers.length - 1 && (
            <div className="absolute left-4 top-12 bottom-0 w-0.5 bg-border" />
          )}
        </div>
      ))}
    </div>
  );
}
