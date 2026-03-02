import React, { useEffect, useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useProgress } from '../hooks/useProgress';
import { getToken } from '../../services/auth';
import BACKEND_URL from "../../services/api";

export default function MyProgressPage() {
    const navigate = useNavigate();
    const { getRoadmapProgress } = useProgress();
    const [skills, setSkills] = useState<any[]>([]);
    const [roadmaps, setRoadmaps] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchData = async () => {
            const token = getToken();
            try {
                // Fetch User Skills to display exact adaptive scores
                const tokenStr = localStorage.getItem("access_token");
                const headers: Record<string, string> = { "Content-Type": "application/json" };
                if (tokenStr) headers["Authorization"] = `Bearer ${tokenStr}`;

                const userRes = await fetch(`${BACKEND_URL}/auth/me`, { headers });
                const userData = await userRes.json();

                const skillsRes = await fetch(`${BACKEND_URL}/users/me/skills`, { headers });
                const skillsData = await skillsRes.json();
                setSkills(skillsData.skills || []);

                // Fetch Roadmaps to match against local progress
                const roadmapsRes = await fetch(`${BACKEND_URL}/roadmaps`, { headers });
                const roadmapsData = await roadmapsRes.json();
                setRoadmaps(roadmapsData);
            } catch (err) {
                console.error("Failed to fetch progress data", err);
            } finally {
                setLoading(false);
            }
        };

        fetchData();
    }, []);

    const getAccentColor = (title: string) => {
        const t = title.toLowerCase();
        if (t.includes('ai') || t.includes('machine learning')) return '#6366f1'; // indigo
        if (t.includes('backend') || t.includes('back-end')) return '#3b82f6'; // blue
        if (t.includes('frontend') || t.includes('front-end')) return '#ec4899'; // pink
        if (t.includes('devops') || t.includes('cloud')) return '#10b981'; // emerald
        if (t.includes('data')) return '#f59e0b'; // amber
        if (t.includes('mobile')) return '#06b6d4'; // cyan
        return 'var(--accent-primary)';
    };

    if (loading) {
        return (
            <div className="progress-root flex items-center justify-center min-h-[50vh]">
                <style>{`
                    .progress-root {
                        --bg-primary: #0a0a0f;
                        --text-muted: #64748b;
                        background-color: var(--bg-primary);
                    }
                `}</style>
                <div style={{ color: 'var(--text-muted)' }}>Loading progress...</div>
            </div>
        );
    }

    return (
        <div className="progress-root">
            <style>{`
                @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Sora:wght@400;500;600;700;800&display=swap');
                
                .progress-root {
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
                    position: relative;
                }

                .progress-bg {
                    position: absolute;
                    top: 0;
                    left: 0;
                    right: 0;
                    bottom: 0;
                    background: radial-gradient(ellipse at 20% 0%, rgba(99,102,241,0.06) 0%, transparent 60%);
                    pointer-events: none;
                    z-index: 0;
                }

                .progress-content {
                    position: relative;
                    z-index: 1;
                    max-width: 1000px;
                    margin: 0 auto;
                    padding: 3rem 1.5rem;
                }

                .title-font {
                    font-family: 'Sora', sans-serif;
                }

                .roadmap-grid {
                    display: grid;
                    gap: 16px;
                    align-items: stretch;
                }

                @media (min-width: 1024px) {
                    .roadmap-grid {
                        grid-template-columns: repeat(2, 1fr);
                    }
                }
                @media (max-width: 1023px) {
                    .roadmap-grid {
                        grid-template-columns: repeat(1, 1fr);
                    }
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

                .dark-card {
                    background-color: var(--bg-card);
                    border: 1px solid var(--border);
                    border-radius: 0.75rem;
                }
            `}</style>

            <div className="progress-bg"></div>

            <div className="progress-content space-y-12">
                <div>
                    <h1 className="title-font text-4xl md:text-5xl font-bold mb-3 tracking-tight">My Progress</h1>
                    <p className="text-lg" style={{ color: 'var(--text-muted)' }}>Track your learning journey and skill development.</p>
                </div>

                <div>
                    <h2 className="title-font text-2xl font-semibold mb-6">Roadmaps Overview</h2>
                    {roadmaps.length === 0 ? (
                        <div className="dark-card p-10 text-center" style={{ color: 'var(--text-muted)' }}>
                            No roadmaps available yet.
                        </div>
                    ) : (
                        <div className="roadmap-grid">
                            {roadmaps.map(roadmap => {
                                // Extract courses from roadmap data if possible, fallback to dummy for visual
                                const coursesData = roadmap.topics?.map((t: any) => ({
                                    id: `course_${t.id}`,
                                    total_resources: 5 // mock estimate
                                })) || [];

                                const progress = getRoadmapProgress(roadmap.id, coursesData);
                                const calculatedPercentage = Math.min(progress.percentage || 0, 100);
                                const score = Math.round(skills.find(s => s.roadmap_id === roadmap.id)?.trust_score || 800);

                                return (
                                    <div
                                        key={roadmap.id}
                                        className="roadmap-card rounded-xl p-6 group cursor-pointer relative"
                                        onClick={() => navigate(`/roadmap/${roadmap.id}`)}
                                    >
                                        <div className="flex justify-between items-start mb-2">
                                            <div className="flex items-center gap-2.5">
                                                <div
                                                    className="w-2.5 h-2.5 rounded-full"
                                                    style={{ backgroundColor: getAccentColor(roadmap.id) }}
                                                />
                                                <h3 className="title-font text-xl font-bold capitalize" style={{ color: 'var(--text-primary)' }}>
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

                                        <div className="flex justify-between items-center mb-8">
                                            <span className="text-sm font-semibold" style={{ color: 'var(--text-muted)' }}>
                                                {progress.completedResources || 0} Resources
                                            </span>
                                            <span
                                                className="px-2 py-0.5 rounded text-[11px] font-bold"
                                                style={{ backgroundColor: 'var(--bg-primary)', color: 'var(--text-muted)' }}
                                            >
                                                {calculatedPercentage}%
                                            </span>
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
                                            </div>

                                            <div className="w-full h-[3px] rounded-full overflow-hidden" style={{ backgroundColor: 'var(--border)' }}>
                                                <div
                                                    className="h-full rounded-full"
                                                    style={{
                                                        backgroundColor: 'var(--accent-primary)',
                                                        width: `${calculatedPercentage}%`,
                                                        transition: 'width 0.5s ease-in-out'
                                                    }}
                                                />
                                            </div>
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    )}
                </div>

                <div>
                    <h2 className="title-font text-2xl font-semibold mb-6">Skill Proficiency Profiles</h2>
                    <div className="dark-card p-6">
                        {skills.length === 0 ? (
                            <p className="text-center py-8" style={{ color: 'var(--text-muted)' }}>Start learning to build your skill profile.</p>
                        ) : (
                            <div className="space-y-6">
                                {skills.map((skill, index) => {
                                    const maxScore = 1500; // Arbitrary max for visualization
                                    const percentage = Math.min(Math.round(((skill.trust_score || 0) / maxScore) * 100), 100);

                                    return (
                                        <div key={index} className="space-y-2">
                                            <div className="flex justify-between items-end">
                                                <div>
                                                    <h4 className="title-font font-semibold capitalize text-lg" style={{ color: 'var(--text-primary)' }}>{skill.roadmap_id.replace('-', ' ')}</h4>
                                                    <p className="text-xs font-medium mt-1" style={{ color: 'var(--text-muted)' }}>Proficiency: {skill.proficiency_level ? (skill.proficiency_level * 100).toFixed(0) + '%' : '0%'}</p>
                                                </div>
                                                <div className="text-right">
                                                    <span className="font-bold text-xl" style={{ color: 'var(--text-primary)' }}>{Math.round(skill.trust_score || 0)}</span>
                                                    <span className="text-xs ml-1 font-semibold" style={{ color: 'var(--text-muted)' }}>elo</span>
                                                </div>
                                            </div>
                                            <div className="w-full rounded-full h-[4px] overflow-hidden" style={{ backgroundColor: 'var(--border)' }}>
                                                <div
                                                    className="h-[4px] rounded-full transition-all"
                                                    style={{
                                                        backgroundColor: percentage > 60 ? '#10b981' : percentage > 30 ? '#3b82f6' : '#f59e0b',
                                                        width: `${percentage}%`
                                                    }}
                                                ></div>
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
