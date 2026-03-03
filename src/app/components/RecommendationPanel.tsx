import React, { useEffect, useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import BACKEND_URL from '../../services/api';
import './RecommendationPanel.css';
import { Play, TrendingUp, Compass, Award, AlertCircle } from 'lucide-react';
import { LemonButton } from './LemonButton';

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

export const RecommendationPanel: React.FC<RecommendationPanelProps> = ({ currentRoadmapId }) => {
    const navigate = useNavigate();
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
                const token = localStorage.getItem("token") || localStorage.getItem("access_token");
                console.log("DEBUG: token =", token);
                console.log("DEBUG: BACKEND_URL =", BACKEND_URL);

                const res = await fetch(
                    `${BACKEND_URL}/recommend/recommend?current_roadmap_id=${currentRoadmapId}`,
                    {
                        headers: {
                            "Content-Type": "application/json",
                            ...(token ? { Authorization: `Bearer ${token}` } : {})
                        }
                    }
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
            <div className="recommendation-panel rounded-xl p-6 text-white min-h-[400px] flex flex-col space-y-6">
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
            <div className="recommendation-panel rounded-xl p-6 text-white flex flex-col items-center justify-center min-h-[400px] border border-red-500/30">
                <AlertCircle className="w-12 h-12 text-red-400 mb-4" />
                <p className="text-gray-400 text-center font-mono">{error}</p>
            </div>
        );
    }

    // Render State: Hidden (if no data)
    if (!data) return null;

    // Render State: Populated
    return (
        <div className="recommendation-panel rounded-xl p-6 text-white flex flex-col space-y-8 shadow-2xl relative z-0">

            {/* ZONE 1: User Elo Badge */}
            <div className="flex items-center space-x-6 pb-6 border-b border-gray-800 relative z-10">
                <div className="elo-badge bg-black/50 border border-[#00FFB2]/50 p-4 rounded-full shadow-lg flex items-center justify-center">
                    <Award className="w-8 h-8 text-[#00FFB2]" />
                </div>
                <div>
                    <div className="text-gray-400 text-sm font-medium tracking-widest uppercase mb-1">
                        Skill Rating
                    </div>
                    <div className="elo-font text-4xl text-[#00FFB2] tracking-tight">
                        <AnimatedNumber value={data.user_elo} />
                    </div>
                </div>
            </div>

            {/* ZONE 2: Continue Learning */}
            <div className="relative z-10 flex flex-col flex-grow">
                <div className="flex items-center mb-4 text-gray-300">
                    <TrendingUp className="w-5 h-5 mr-2 text-indigo-400" />
                    <h3 className="font-semibold text-lg tracking-wide">Continue Learning</h3>
                </div>

                {data.next_in_current_roadmap.length === 0 ? (
                    <div className="bg-gray-900/50 rounded-lg p-6 text-center border border-gray-800">
                        <span className="text-gray-400 text-sm">
                            No courses available right now. Try exploring a new roadmap below.
                        </span>
                    </div>
                ) : (
                    <div className="space-y-3">
                        {data.next_in_current_roadmap.map((node) => (
                            <div
                                key={node.id}
                                className="hover-glow bg-gray-900/60 border border-gray-800 rounded-lg p-4 flex flex-col sm:flex-row sm:items-center justify-between group cursor-default gap-4"
                            >
                                <div>
                                    <h4 className="font-medium text-gray-100 group-hover:text-white transition-colors">
                                        {node.title}
                                    </h4>
                                    <div className="mt-1 flex items-center">
                                        <span className="text-xs text-gray-500 mr-2 uppercase tracking-wide">Difficulty</span>
                                        <DifficultyPips difficulty={node.difficulty} />
                                    </div>
                                </div>

                                <LemonButton
                                    onClick={() => navigate(`/course/${node.id}`)}
                                    className="bg-[#00FFB2]/10 hover:bg-[#00FFB2]/20 text-[#00FFB2] border border-[#00FFB2]/30 text-xs px-4 py-2 w-full sm:w-auto flex-shrink-0"
                                >
                                    <Play className="w-3 h-3 mr-1.5" /> Start
                                </LemonButton>
                            </div>
                        ))}
                    </div>
                )}
            </div>

            {/* ZONE 3: Explore New Roadmaps */}
            {data.suggested_new_roadmaps.length > 0 && (
                <div className="relative z-10 pt-4 border-t border-gray-800">
                    <div className="flex items-center mb-4 text-gray-300">
                        <Compass className="w-5 h-5 mr-2 text-amber-400" />
                        <h3 className="font-semibold text-lg tracking-wide">Explore New Paths</h3>
                    </div>

                    <div className="flex flex-wrap gap-3">
                        {data.suggested_new_roadmaps.map(roadmapId => (
                            <button
                                key={roadmapId}
                                className="hover-glow bg-gray-900/80 border border-gray-800 rounded-full px-4 py-2 flex items-center cursor-pointer transition-colors hover:border-amber-400/50 group"
                                onClick={() => navigate(`/roadmaps/${roadmapId}`)}
                            >
                                <span className="text-sm text-gray-300 capitalize group-hover:text-amber-400 transition-colors">
                                    {roadmapId.replace(/-/g, ' ')}
                                </span>
                            </button>
                        ))}
                    </div>
                </div>
            )}

        </div>
    );
};
