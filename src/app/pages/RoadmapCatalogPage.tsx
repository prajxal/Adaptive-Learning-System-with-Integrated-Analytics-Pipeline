import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useRoadmaps } from "../../hooks/useRoadmaps";
import { getAllProgress, Progress } from "../../services/progressApi";
import { usePostHog } from "@posthog/react";

function RoadmapCard({ roadmap, progress }: { roadmap: any; progress: Progress | null }) {
    const posthog = usePostHog();

    const getAccentColor = (title: string) => {
        const t = title.toLowerCase();
        if (t.includes('ai') || t.includes('machine learning')) return '#6366f1'; // indigo
        if (t.includes('backend') || t.includes('back-end')) return '#3b82f6'; // blue
        if (t.includes('frontend') || t.includes('front-end')) return '#ec4899'; // pink
        if (t.includes('devops') || t.includes('cloud')) return '#10b981'; // emerald
        if (t.includes('data')) return '#f59e0b'; // amber
        if (t.includes('mobile')) return '#06b6d4'; // cyan
        // default fallback
        return 'var(--accent-primary)';
    };

    const hasProgress = !!progress;
    const score = hasProgress ? Math.round(progress.trust_score) : 800;

    return (
        <Link
            to={`/roadmap/${roadmap.id}`}
            onClick={() => posthog?.capture('roadmap_selected', { roadmap_id: roadmap.id, has_progress: !!progress })}
            className="roadmap-card rounded-xl p-6 group cursor-pointer relative"
        >
            <div className="flex justify-between items-start mb-2">
                <div className="flex items-center gap-2.5">
                    <div
                        className="w-2.5 h-2.5 rounded-full"
                        style={{ backgroundColor: getAccentColor(roadmap.id) }}
                    />
                    <h3 className="roadmap-title text-xl font-bold capitalize" style={{ color: 'var(--text-primary)' }}>
                        {roadmap.id.replace(/-/g, ' ')}
                    </h3>
                </div>

                <div
                    className="opacity-0 group-hover:opacity-100 transition-opacity duration-200"
                    style={{ color: 'var(--text-muted)' }}
                >
                    <span className="text-xl leading-none">→</span>
                </div>
            </div>

            <div className="text-sm mb-8" style={{ color: 'var(--text-muted)' }}>
                {roadmap.topic_count} topics
            </div>

            <div className="mt-auto flex flex-col gap-3">
                <div className="flex items-center justify-between">
                    {score !== 800 ? (
                        <div
                            className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold border"
                            style={{
                                backgroundColor: 'rgba(99,102,241,0.1)',
                                color: 'var(--accent-primary)',
                                borderColor: 'rgba(99,102,241,0.2)'
                            }}
                        >
                            Score: {score}
                        </div>
                    ) : (
                        <div
                            className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border"
                            style={{ backgroundColor: 'var(--bg-primary)', color: 'var(--text-muted)', borderColor: 'var(--border)' }}
                        >
                            <span style={{ fontSize: '8px' }}>●</span> Not Started
                        </div>
                    )}

                    {hasProgress ? (
                        <span className="text-xs font-semibold" style={{ color: 'var(--text-muted)' }}>
                            {progress.completed_courses} / {progress.total_courses}
                        </span>
                    ) : (
                        <span className="text-xs font-semibold" style={{ color: 'var(--text-muted)' }}>
                            0 / {roadmap.topic_count}
                        </span>
                    )}
                </div>

                {hasProgress ? (
                    <div className="w-full h-[3px] rounded-full overflow-hidden" style={{ backgroundColor: 'var(--border)' }}>
                        <div
                            className="h-full rounded-full"
                            style={{
                                backgroundColor: 'var(--accent-primary)',
                                width: `${Math.min(100, (progress.completed_courses / Math.max(1, progress.total_courses)) * 100)}%`,
                                transition: 'width 0.5s ease-in-out'
                            }}
                        />
                    </div>
                ) : (
                    <div className="w-full h-[3px] rounded-full overflow-hidden" style={{ backgroundColor: 'var(--border)' }}>
                        <div
                            className="h-full rounded-full"
                            style={{ backgroundColor: 'var(--accent-primary)', width: '0%' }}
                        />
                    </div>
                )}
            </div>
        </Link>
    );
}

export default function RoadmapCatalogPage() {
    console.log("[RoadmapCatalogPage] Rendering. Pathname:", window.location.pathname);
    const { roadmaps, loading, error } = useRoadmaps();
    const [progressMap, setProgressMap] = useState<Record<string, Progress>>({});

    useEffect(() => {
        getAllProgress().then(items => {
            const map: Record<string, Progress> = {};
            for (const p of items) map[p.roadmap_id] = p;
            setProgressMap(map);
        });
    }, []);

    return (
        <div className="roadmap-catalog-root">
            <style>{`
                @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Sora:wght@400;500;600;700;800&display=swap');
                
                .roadmap-catalog-root {
                    --bg-primary: #0a0a0f;
                    --bg-card: #111118;
                    --bg-card-hover: #16161f;
                    --accent-primary: #6366f1;
                    --accent-secondary: #818cf8;
                    --text-primary: #f1f5f9;
                    --text-muted: #64748b;
                    --border: #1e1e2e;
                    
                    background-color: var(--bg-primary);
                    color: var(--text-primary);
                    font-family: 'DM Sans', sans-serif;
                    
                    min-height: 100vh;
                    padding: 4rem 2rem;
                    position: relative;
                }
                
                @media (max-width: 768px) {
                    .roadmap-catalog-root {
                        padding: 2rem 1rem;
                    }
                }

                .roadmap-catalog-bg {
                    position: absolute;
                    top: 0;
                    left: 0;
                    right: 0;
                    bottom: 0;
                    background: radial-gradient(ellipse at 20% 0%, rgba(99,102,241,0.06) 0%, transparent 60%);
                    pointer-events: none;
                    z-index: 0;
                }

                .roadmap-catalog-content {
                    position: relative;
                    z-index: 1;
                    max-width: 1200px;
                    margin: 0 auto;
                }

                .roadmap-card {
                    background-color: var(--bg-card);
                    border: 1px solid var(--border);
                    transition: all 0.2s ease;
                    display: flex;
                    flex-direction: column;
                    text-decoration: none;
                }

                .roadmap-card:hover {
                    background-color: var(--bg-card-hover);
                    border-color: var(--accent-primary);
                    box-shadow: 0 0 24px rgba(99,102,241,0.15);
                }
                
                .roadmap-title {
                    font-family: 'Sora', sans-serif;
                }

                .roadmap-grid {
                    display: grid;
                    gap: 16px;
                    align-items: stretch;
                }

                @media (min-width: 1024px) {
                    .roadmap-grid {
                        grid-template-columns: repeat(3, 1fr);
                    }
                }
                @media (min-width: 768px) and (max-width: 1023px) {
                    .roadmap-grid {
                        grid-template-columns: repeat(2, 1fr);
                    }
                }
                @media (max-width: 767px) {
                    .roadmap-grid {
                        grid-template-columns: repeat(1, 1fr);
                    }
                }
            `}</style>

            <div className="roadmap-catalog-bg"></div>

            <div className="roadmap-catalog-content">
                {loading ? (
                    <div className="text-center py-20" style={{ color: 'var(--text-muted)' }}>
                        Loading roadmaps...
                    </div>
                ) : error ? (
                    <div className="text-center py-20 text-red-500">
                        Error loading roadmaps
                    </div>
                ) : (
                    <>
                        <div className="mb-12">
                            <h1 className="roadmap-title text-4xl md:text-5xl font-bold mb-4 tracking-tight">
                                Engineering Roadmaps
                            </h1>
                            <p className="text-lg md:text-xl" style={{ color: 'var(--text-muted)' }}>
                                Choose a track. Learn adaptively.
                            </p>
                            <hr className="mt-8 border-t" style={{ borderColor: 'var(--border)' }} />
                        </div>

                        <div className="roadmap-grid">
                            {roadmaps.map((roadmap) => (
                                <RoadmapCard key={roadmap.id} roadmap={roadmap} progress={progressMap[roadmap.id] ?? null} />
                            ))}
                        </div>
                    </>
                )}
            </div>
        </div>
    );
}
