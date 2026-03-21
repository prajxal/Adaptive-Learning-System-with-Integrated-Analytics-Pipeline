import React, { useEffect, useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { fetchWithAuth } from '../../services/api';
import BACKEND_URL from '../../services/api';
import './RecommendationPanel.css';
import { Play, TrendingUp, Compass, Award, AlertCircle, Star } from 'lucide-react';
import { LemonButton } from './LemonButton';
import { usePostHog } from '@posthog/react';
import { ROUTES } from '../constants/routes';

// Types
interface RoadmapNode {
    id: string;
    title: string;
    difficulty: number;
    roadmap_id: string;
}

interface RecommendationResponse {
    user_elo: number;
    next_in_current_roadmap: RoadmapNode[];
    suggested_new_roadmaps: string[];
}

interface RecommendationPanelProps {
    currentRoadmapId?: string;
    recommendedStart?: { id: string; title: string } | null;
    alternativeStarts?: { id: string; title: string }[];
}

// Utility to normalize difficulty
const normalizeDifficulty = (difficulty: number) => {
    return Math.min(Math.max((difficulty - 800) / 1200, 0), 1);
};

// Animated Number Component
const AnimatedNumber: React.FC<{ value: number }> = ({ value }) => {
    const [displayValue, setDisplayValue] = useState(0);

    useEffect(() => {
        let startTime: number;
        const duration = 1000; // 1 second
        const startValue = 0;

        const animate = (timestamp: number) => {
            if (!startTime) startTime = timestamp;
            const progress = timestamp - startTime;
            const percentage = Math.min(progress / duration, 1);

            // Easing function (easeOutExpo)
            const easePercentage = percentage === 1 ? 1 : 1 - Math.pow(2, -10 * percentage);
            const currentVal = startValue + (value - startValue) * easePercentage;

            setDisplayValue(currentVal);

            if (progress < duration) {
                requestAnimationFrame(animate);
            } else {
                setDisplayValue(value);
            }
        };

        requestAnimationFrame(animate);
    }, [value]);

    return <span>{Math.round(displayValue)}</span>;
};

// Difficulty Pips Component
const DifficultyPips: React.FC<{ difficulty: number }> = ({ difficulty }) => {
    const normalized = normalizeDifficulty(difficulty);
    const totalPips = 5;
    const activePips = Math.ceil(normalized * totalPips) || 1; // At least 1 pip

    return (
        <div className="flex space-x-1 mt-1">
            {Array.from({ length: totalPips }).map((_, i) => (
                <div
                    key={i}
                    className={`h-1.5 w-4 rounded-sm transition-colors ${i < activePips ? 'bg-[#00FFB2]' : 'bg-gray-700'
                        }`}
                />
            ))}
        </div>
    );
};

export const RecommendationPanel: React.FC<RecommendationPanelProps> = ({ currentRoadmapId, recommendedStart, alternativeStarts }) => {
    const navigate = useNavigate();
    const posthog = usePostHog();
    const [data, setData] = useState<RecommendationResponse | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const hasFetched = useRef<string | null>(null);

    useEffect(() => {
        if (!currentRoadmapId) return;
        if (hasFetched.current === currentRoadmapId) return;

        const fetchRecommendations = async () => {
            hasFetched.current = currentRoadmapId;
            setLoading(true);
            setError(null);

            try {
                const res = await fetchWithAuth(
                    `${BACKEND_URL}/recommend/recommend?current_roadmap_id=${currentRoadmapId}`
                );

                console.log("DEBUG: status =", res.status);

                const text = await res.text();
                console.log("DEBUG: raw response =", text);

                if (!res.ok) {
                    if (res.status === 401) {
                        throw new Error("unauthorized");
                    } else if (res.status === 404) {
                        throw new Error("unavailable");
                    } else if (res.status >= 500) {
                        throw new Error("offline");
                    } else {
                        throw new Error(`Request failed: ${res.status}`);
                    }
                }

                const data = JSON.parse(text);
                console.log("DEBUG: parsed data =", data);
                setData(data);
            } catch (err: any) {
                if (err.message === "unauthorized") {
                    setError("Session expired. Please log in again.");
                } else if (err.message === "unavailable") {
                    setError("Recommendation service unavailable.");
                } else if (err.message === "offline") {
                    setError("Our systems are currently offline. Stand by.");
                } else {
                    setError(`Error: ${err.message}`);
                }
            } finally {
                setLoading(false);
            }
        };

        fetchRecommendations();
    }, [currentRoadmapId]);

    if (!currentRoadmapId) return null;

    // Render State: Loading
    if (loading) {
        return (
            <div className="recommendation-panel rounded-xl p-4 space-y-6 text-white min-h-[400px] flex flex-col">
                <div className="flex items-center space-x-4">
                    <div className="w-16 h-16 rounded-full bg-gray-800 animate-pulse" />
                    <div className="space-y-2">
                        <div className="w-24 h-4 bg-gray-800 rounded animate-pulse" />
                        <div className="w-16 h-6 bg-gray-800 rounded animate-pulse" />
                    </div>
                </div>
                <div className="space-y-3">
                    {[1, 2, 3].map(i => (
                        <div key={i} className="w-full h-20 bg-gray-800 rounded-lg animate-pulse" />
                    ))}
                </div>
            </div>
        );
    }

    // Render State: Error
    if (error) {
        return (
            <div className="recommendation-panel rounded-xl p-4 space-y-6 text-white flex flex-col items-center justify-center min-h-[400px] border border-red-500/30">
                <AlertCircle className="w-12 h-12 text-red-400 mb-4" />
                <p className="text-gray-400 text-center font-mono">{error}</p>
            </div>
        );
    }

    // Render State: Hidden (if no data)
    if (!data) return null;

    // Render State: Populated
    return (
        <div className="recommendation-panel rounded-xl p-4 space-y-6 text-white flex flex-col shadow-2xl relative z-0">

            {/* ZONE 1: User Elo Badge */}
            <div className="relative z-10 space-y-3 pb-6 border-b border-gray-800">
                <div className="flex items-center gap-4">
                    <div className="elo-badge bg-black/50 border border-[#00FFB2]/50 p-4 rounded-full shadow-lg flex items-center justify-center">
                        <Award className="w-8 h-8 text-[#00FFB2]" />
                    </div>
                    <div className="flex flex-col">
                        <span className="text-xs tracking-widest text-white/40 uppercase">Skill Rating</span>
                        <div className="elo-font text-4xl text-[#00FFB2] tracking-tight">
                            <AnimatedNumber value={data.user_elo} />
                        </div>
                    </div>
                </div>
            </div>

            {/* ZONE 2: Recommended Start */}
            {recommendedStart && (
                <div className="relative z-10 flex flex-col space-y-3">
                    <div className="flex items-center gap-2 pb-2 border-b border-white/10 text-gray-300">
                        <Star className="w-5 h-5 text-amber-400 fill-amber-400" />
                        <h3 className="text-sm font-semibold tracking-wide uppercase text-white/70">
                            Recommended Start
                        </h3>
                    </div>

                    <div
                        className="hover-glow bg-gray-900/60 border border-[#00FFB2]/30 rounded-lg p-4 flex items-center justify-between gap-3 w-full group cursor-default shadow-[0_0_16px_rgba(0,255,178,0.06)]"
                    >
                        <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium line-clamp-2 break-words text-gray-100 group-hover:text-white transition-colors">
                                {recommendedStart.title}
                            </p>
                            <p className="text-xs text-gray-500 mt-1">
                                Best starting point based on prerequisite graph
                            </p>
                        </div>

                        <button
                            type="button"
                            onClick={() => {
                                posthog?.capture('recommended_start_clicked', {
                                    course_id: recommendedStart.id,
                                    course_title: recommendedStart.title,
                                    current_roadmap_id: currentRoadmapId,
                                });
                                navigate(ROUTES.COURSE(recommendedStart.id));
                            }}
                            className="shrink-0 px-3 py-1.5 text-xs rounded-md bg-[#00FFB2]/10 hover:bg-[#00FFB2]/20 text-[#00FFB2] border border-[#00FFB2]/30 flex items-center gap-1.5 transition-all hover:shadow-[0_0_12px_rgba(0,255,178,0.4)]"
                        >
                            <Play className="w-3 h-3" /> Start Learning
                        </button>
                    </div>
                </div>
            )}

            {/* ZONE 2b: Alternative Starting Points */}
            {alternativeStarts && alternativeStarts.length > 0 && (
                <div className="relative z-10 flex flex-col space-y-3">
                    <div className="flex items-center gap-2 pb-2 border-b border-white/10 text-gray-300">
                        <TrendingUp className="w-5 h-5 text-indigo-400" />
                        <h3 className="text-sm font-semibold tracking-wide uppercase text-white/70">
                            Other Good Starting Points
                        </h3>
                    </div>

                    <div className="space-y-3">
                        {alternativeStarts.map((alt) => (
                            <div
                                key={alt.id}
                                className="hover-glow bg-gray-900/60 border border-gray-800 rounded-lg p-4 flex items-center justify-between gap-3 w-full group cursor-default"
                            >
                                <div className="flex-1 min-w-0">
                                    <p className="text-sm font-medium line-clamp-2 break-words text-gray-100 group-hover:text-white transition-colors">
                                        {alt.title}
                                    </p>
                                </div>

                                <button
                                    type="button"
                                    onClick={() => {
                                        posthog?.capture('alternative_start_clicked', {
                                            course_id: alt.id,
                                            course_title: alt.title,
                                            current_roadmap_id: currentRoadmapId,
                                        });
                                        navigate(ROUTES.COURSE(alt.id));
                                    }}
                                    className="shrink-0 px-3 py-1.5 text-xs rounded-md bg-[#00FFB2]/10 hover:bg-[#00FFB2]/20 text-[#00FFB2] border border-[#00FFB2]/30 flex items-center gap-1.5 transition-all hover:shadow-[0_0_12px_rgba(0,255,178,0.4)]"
                                >
                                    <Play className="w-3 h-3" /> Start
                                </button>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* ZONE 3: Explore New Roadmaps */}
            {data.suggested_new_roadmaps.length > 0 && (
                <div className="relative z-10 pt-4 border-t border-gray-800 space-y-3">
                    <div className="flex items-center gap-2 pb-2 border-b border-white/10 text-gray-300">
                        <Compass className="w-5 h-5 text-amber-400" />
                        <h3 className="text-sm font-semibold tracking-wide uppercase text-white/70">
                            Explore New Paths
                        </h3>
                    </div>

                    <div className="flex flex-wrap gap-2">
                        {data.suggested_new_roadmaps.map(roadmapId => (
                            <button
                                key={roadmapId}
                                className="px-3 py-1.5 text-xs rounded-full border border-white/20 hover:border-[#00FFB2] whitespace-nowrap bg-gray-900/80 text-gray-300 capitalize transition-colors hover:text-[#00FFB2]"
                                onClick={() => {
                                    posthog?.capture('recommended_roadmap_explored', {
                                        suggested_roadmap_id: roadmapId,
                                        current_roadmap_id: currentRoadmapId,
                                    });
                                    navigate(`/roadmaps/${roadmapId}`);
                                }}
                            >
                                {roadmapId.replace(/-/g, ' ')}
                            </button>
                        ))}
                    </div>
                </div>
            )}

        </div>
    );
};
