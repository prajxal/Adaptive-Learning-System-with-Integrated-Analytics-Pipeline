import React from 'react';
import { ArrowLeft, ExternalLink, CheckCircle, Book, Video, FileText } from 'lucide-react';
import { LemonButton } from '../components/LemonButton';
import { LemonCard } from '../components/LemonCard';
import { RoadmapTopic } from '../components/RoadmapContainer';
import { CourseDifficultyBadge } from '../components/CourseDifficultyBadge';

interface Resource {
  id: string;
  title: string;
  type: 'article' | 'video' | 'course';
  url: string;
  duration?: string;
}

interface TopicDetailPageProps {
  topic: RoadmapTopic;
  onBack: () => void;
  onMarkComplete: () => void;
}

const mockResources: Resource[] = [
  {
    id: '1',
    title: 'Official Documentation',
    type: 'article',
    url: '#',
    duration: '30 min read',
  },
  {
    id: '2',
    title: 'Interactive Video Tutorial',
    type: 'video',
    url: '#',
    duration: '45 min',
  },
  {
    id: '3',
    title: 'Comprehensive Course',
    type: 'course',
    url: '#',
    duration: '2 hours',
  },
  {
    id: '4',
    title: 'Practical Examples Guide',
    type: 'article',
    url: '#',
    duration: '20 min read',
  },
];

const resourceIcons = {
  article: FileText,
  video: Video,
  course: Book,
};

export function TopicDetailPage({ topic, onBack, onMarkComplete }: TopicDetailPageProps) {
  const isCompleted = topic.status === 'completed';
  
  return (
    <div className="space-y-6">
      {/* Back Button */}
      <LemonButton variant="tertiary" size="small" onClick={onBack}>
        <ArrowLeft className="w-4 h-4" />
        Back to Roadmap
      </LemonButton>
      
      {/* Topic Header */}
      <div className="space-y-3">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1">
            <div className="flex items-center gap-3 mb-2">
              <h1>{topic.title}</h1>
              {isCompleted && (
                <div className="flex items-center gap-1 px-2 py-1 bg-[#388600]/10 text-[#388600] rounded-[6px]">
                  <CheckCircle className="w-4 h-4" />
                  <span className="text-sm font-medium">Completed</span>
                </div>
              )}
            </div>
            <p className="text-muted-foreground">{topic.description}</p>
          </div>
          <span className="text-sm px-3 py-1.5 bg-muted text-muted-foreground rounded-[6px] whitespace-nowrap">
            <CourseDifficultyBadge difficultyLevel={topic.difficultyLevel} />
          </span>
        </div>
      </div>
      
      {/* Learning Resources */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2>Learning Resources</h2>
          <span className="text-sm text-muted-foreground">{mockResources.length} resources</span>
        </div>
        
        <div className="grid grid-cols-1 gap-3">
          {mockResources.map((resource) => {
            const Icon = resourceIcons[resource.type];
            
            return (
              <LemonCard key={resource.id} hoverable>
                <a 
                  href={resource.url}
                  className="flex items-center justify-between gap-4 -m-6 p-6"
                  onClick={(e) => e.preventDefault()}
                >
                  <div className="flex items-start gap-3 flex-1">
                    <div className="w-10 h-10 bg-accent/10 rounded-[6px] flex items-center justify-center flex-shrink-0">
                      <Icon className="w-5 h-5 text-accent" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <h4 className="font-medium mb-1">{resource.title}</h4>
                      <div className="flex items-center gap-2 text-sm text-muted-foreground">
                        <span className="capitalize">{resource.type}</span>
                        {resource.duration && (
                          <>
                            <span>•</span>
                            <span>{resource.duration}</span>
                          </>
                        )}
                      </div>
                    </div>
                  </div>
                  <ExternalLink className="w-5 h-5 text-muted-foreground flex-shrink-0" />
                </a>
              </LemonCard>
            );
          })}
        </div>
      </div>
      
      {/* Action Button */}
      {!isCompleted && (
        <LemonCard>
          <div className="flex items-center justify-between gap-4">
            <div>
              <h4 className="font-medium mb-1">Mark as Complete</h4>
              <p className="text-sm text-muted-foreground">
                Unlock the next topic in your learning path
              </p>
            </div>
            <LemonButton variant="primary" onClick={onMarkComplete}>
              <CheckCircle className="w-5 h-5" />
              Complete
            </LemonButton>
          </div>
        </LemonCard>
      )}
    </div>
  );
}
