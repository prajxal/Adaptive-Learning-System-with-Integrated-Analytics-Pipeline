import React, { useEffect, useState } from "react";
import { Link, useNavigate, useLocation } from "react-router-dom";
import { getGithubStatus, redirectToGithubConnect } from "../../services/githubApi";
import { uploadResume, checkResumeStatus } from "../../services/resumeApi";
import { getUserSkills } from "../../services/userApi";
import { getToken } from "../../services/auth";
import { useProgress } from "../hooks/useProgress";
import { Brain, Check } from "lucide-react";
import { usePostHog } from "@posthog/react";

export default function DashboardPage() {
  const token = getToken();
  const navigate = useNavigate();
  const location = useLocation();
  const posthog = usePostHog();
  const [githubSuccess, setGithubSuccess] = useState(false);

  useEffect(() => {
    if (!token) {
      navigate('/signin', { replace: true });
    }
  }, [token, navigate]);

  // Consolidating skills state
  const [skills, setSkills] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Onboarding UI hooks
  const [githubConnected, setGithubConnected] = useState(false);
  const [githubUsername, setGithubUsername] = useState("");
  const [resumeUploading, setResumeUploading] = useState(false);
  const pollingIntervalRef = React.useRef<ReturnType<typeof setInterval> | null>(null);

  const { getLastAccessed } = useProgress();
  const lastAccessed = getLastAccessed();

  useEffect(() => {
    return () => {
      if (pollingIntervalRef.current) clearInterval(pollingIntervalRef.current);
    };
  }, []);

  useEffect(() => {
    const params = new URLSearchParams(location.search);
    if (params.get("github") === "connected") {
      setGithubSuccess(true);
      // Clean up URL without refreshing
      window.history.replaceState({}, document.title, location.pathname);
      setTimeout(() => setGithubSuccess(false), 5000);
    }
  }, [location]);

  useEffect(() => {
    if (!token) return;

    getGithubStatus()
      .then(data => {
        setGithubConnected(data.connected);
        setGithubUsername(data.username || "");
      })
      .catch(console.error);

    getUserSkills()
      .then(data => {
        setSkills(data.skills || []);
      })
      .catch((e: any) => {
        console.error("Skill load error:", e);
        setSkills([]);
        setError(null);
      })
      .finally(() => {
        setLoading(false);
      });

  }, [token]);

  const startPolling = () => {
    pollingIntervalRef.current = setInterval(async () => {
      try {
        const res = await checkResumeStatus();
        if (res.status === "completed" || res.status === "failed") {
          if (pollingIntervalRef.current) clearInterval(pollingIntervalRef.current);
          setResumeUploading(false);

          if (res.status === "completed") {
            const updatedSkills = await getUserSkills();
            setSkills(updatedSkills.skills || []);
          } else {
            posthog?.capture('resume_processing_failed');
            alert("Resume processing failed.");
          }
        }
      } catch (err: any) {
        console.error("Polling error", err);
        if (pollingIntervalRef.current) clearInterval(pollingIntervalRef.current);
        setResumeUploading(false);
      }
    }, 3000);
  };

  async function handleResumeUpload(e: React.ChangeEvent<HTMLInputElement>) {
    if (!e.target.files?.length || !token) return;

    const file = e.target.files[0];
    setResumeUploading(true);

    try {
      await uploadResume(file);
      posthog?.capture('resume_uploaded', { file_name: file.name, file_size: file.size });
      startPolling();
    } catch (err: any) {
      console.error(err);
      posthog?.captureException(err);
      alert("Resume upload failed");
      setResumeUploading(false);
    }
  }

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

  return (
    <div className="dashboard-root">
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Sora:wght@400;500;600;700;800&display=swap');
        
        .dashboard-root {
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

        .dashboard-bg {
          position: absolute;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background: radial-gradient(ellipse at 20% 0%, rgba(99,102,241,0.06) 0%, transparent 60%);
          pointer-events: none;
          z-index: 0;
        }

        .dashboard-content {
          position: relative;
          z-index: 1;
          max-width: 1000px;
          margin: 0 auto;
          padding: 3rem 1.5rem;
        }

        .title-font {
          font-family: 'Sora', sans-serif;
        }

        .dark-card {
          background-color: var(--bg-card);
          border: 1px solid var(--border);
          border-radius: 0.75rem;
        }
        
        /* Specific components styled per prompt */
        .upload-zone {
          border: 1px dashed var(--border);
          transition: border-color 0.2s ease;
        }
        .upload-zone:hover {
          border-color: var(--accent-primary);
          cursor: pointer;
        }
        .upload-btn {
          background-color: #16161f;
          border: 1px solid var(--border);
          color: var(--text-primary);
          transition: border-color 0.2s ease;
        }
        .upload-btn:hover {
          border-color: var(--accent-primary);
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
      `}</style>

      <div className="dashboard-bg"></div>

      <div className="dashboard-content">
        <div className="mb-10">
          <h1 className="title-font text-4xl md:text-5xl font-bold tracking-tight mb-2">
            Dashboard
          </h1>
          <p className="text-lg" style={{ color: 'var(--text-muted)' }}>
            Your learning command center.
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8 mt-10">
          {/* Account Setup Card */}
          <div className="dark-card p-6 flex flex-col">
            <div className="flex justify-between items-center mb-6">
              <h2 className="title-font text-xl font-semibold">Account Setup</h2>
              {githubSuccess && (
                <span className="text-sm font-medium text-green-400 bg-green-400/10 px-3 py-1 rounded-full">
                  GitHub Linked Successfully!
                </span>
              )}
            </div>

            <div className="mb-6">
              {githubConnected ? (
                <div
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium"
                  style={{ backgroundColor: 'rgba(34, 197, 94, 0.1)', color: '#22c55e', border: '1px solid rgba(34, 197, 94, 0.2)' }}
                >
                  <Check className="w-4 h-4" />
                  Connected to GitHub as {githubUsername}
                </div>
              ) : (
                <button
                  onClick={() => { posthog?.capture('github_connect_clicked'); redirectToGithubConnect(); }}
                  className="upload-btn px-4 py-2 text-sm rounded-md font-medium"
                >
                  Connect GitHub
                </button>
              )}
            </div>

            <div className="mt-auto">
              <label className="block mb-2 font-medium text-sm" style={{ color: 'var(--text-muted)' }}>Upload Resume (PDF)</label>
              <div className="upload-zone rounded-lg relative overflow-hidden flex items-center p-1">
                <input
                  type="file"
                  accept=".pdf"
                  onChange={handleResumeUpload}
                  className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10"
                />
                <div className="flex w-full items-center">
                  <div className="upload-btn px-4 py-2 rounded-md text-sm font-medium z-0 pointer-events-none">
                    Choose file
                  </div>
                  <div className="flex-1 flex items-center px-4 text-sm z-0" style={{ color: 'var(--text-muted)' }}>
                    {resumeUploading ? "Processing..." : "No file chosen"}
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Your Skill Profile Card */}
          <div className="dark-card p-6 flex flex-col h-full">
            <h2 className="title-font text-xl font-semibold mb-6">Your Skill Profile</h2>

            {loading ? (
              <div className="flex-1 flex items-center justify-center" style={{ color: 'var(--text-muted)' }}>Loading skills...</div>
            ) : error ? (
              <div className="flex-1 flex items-center justify-center text-red-400">{error}</div>
            ) : skills.length === 0 ? (
              <div className="flex-1 flex flex-col items-center justify-center py-6 text-center">
                <div
                  className="w-12 h-12 rounded-xl mb-4 flex items-center justify-center"
                  style={{ backgroundColor: 'rgba(99,102,241,0.1)', color: 'var(--accent-primary)' }}
                >
                  <Brain className="w-6 h-6" />
                </div>
                <h3 className="font-semibold mb-1" style={{ color: 'var(--text-primary)' }}>Complete your first quiz to unlock your skill profile</h3>
                <p className="text-sm" style={{ color: 'var(--text-muted)' }}>Your adaptive scores will appear here as you learn</p>
              </div>
            ) : (
              <div className="space-y-4 flex-1">
                {skills.map(skill => (
                  <div key={skill.roadmap_id + "_profile"} className="mb-4 last:mb-0">
                    <div className="flex justify-between items-end mb-2">
                      <span className="capitalize font-medium text-sm" style={{ color: 'var(--text-primary)' }}>
                        {skill.roadmap_id.replace(/-/g, ' ')}
                      </span>
                      <span className="text-xs font-medium" style={{ color: 'var(--text-muted)' }}>
                        Confidence: {skill.proficiency_level ? (skill.proficiency_level * 100).toFixed(0) : 0}%
                      </span>
                    </div>
                    <div className="w-full h-[4px] rounded-full overflow-hidden" style={{ backgroundColor: 'var(--border)' }}>
                      <div
                        className="h-full rounded-full"
                        style={{
                          backgroundColor: 'var(--accent-primary)',
                          width: `${skill.proficiency_level ? skill.proficiency_level * 100 : 0}%`,
                          transition: 'width 0.5s ease-in-out'
                        }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Continue Learning Feature */}
        <div className="mb-10">
          <div
            className="rounded-xl p-6 sm:p-8 flex flex-col sm:flex-row justify-between items-start sm:items-center relative overflow-hidden"
            style={{ backgroundImage: 'linear-gradient(135deg, #4f46e5, #6366f1)' }}
          >
            {lastAccessed && lastAccessed.courseId && lastAccessed.resourceId ? (
              <>
                <div className="z-10 relative mb-4 sm:mb-0">
                  <p
                    className="text-[11px] font-bold tracking-[0.08em] uppercase mb-2"
                    style={{ color: 'rgba(255,255,255,0.6)' }}
                  >
                    ACTIVE COURSE MODULE
                  </p>
                  <h3 className="title-font text-2xl font-bold text-white tracking-tight">
                    {lastAccessed.courseTitle}
                  </h3>
                </div>
                <button
                  onClick={() => {
                    posthog?.capture('continue_learning_clicked', { course_title: lastAccessed.courseTitle, course_id: lastAccessed.courseId });
                    navigate(`/course/${lastAccessed.courseId}/resource/${lastAccessed.resourceId}`);
                  }}
                  className="z-10 relative bg-white text-[#6366f1] hover:bg-[#6366f1] hover:text-white border border-transparent hover:border-white font-bold py-2.5 px-6 rounded-lg transition-all shadow-sm whitespace-nowrap"
                >
                  Resume ↗
                </button>
              </>
            ) : (
              <div className="z-10 relative w-full flex flex-col sm:flex-row justify-between items-start sm:items-center">
                <div className="mb-4 sm:mb-0">
                  <p
                    className="text-[11px] font-bold tracking-[0.08em] uppercase mb-2"
                    style={{ color: 'rgba(255,255,255,0.6)' }}
                  >
                    CONTINUE LEARNING
                  </p>
                  <h3 className="title-font text-2xl font-bold text-white tracking-tight">
                    Start a roadmap to begin learning
                  </h3>
                </div>
              </div>
            )}
          </div>
        </div>

        <div className="mb-8 mt-12">
          <h2 className="title-font text-2xl font-semibold mb-6">Learning Tracks Progress</h2>

          {loading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {[1, 2].map(i => (
                <div key={i} className="dark-card h-[160px] animate-pulse" />
              ))}
            </div>
          ) : error ? (
            <div className="p-6 text-center text-red-400 border border-red-900 rounded-xl" style={{ backgroundColor: 'rgba(239,68,68,0.05)' }}>
              {error}
            </div>
          ) : skills.length === 0 ? (
            <div className="dark-card p-10 flex flex-col items-center justify-center text-center">
              <p className="mb-4" style={{ color: 'var(--text-muted)' }}>No tracks started yet.</p>
              <button
                onClick={() => navigate('/roadmaps')}
                className="px-5 py-2.5 rounded-md font-medium transition-colors text-sm"
                style={{
                  backgroundColor: 'transparent',
                  border: '1px solid var(--accent-primary)',
                  color: 'var(--accent-primary)'
                }}
                onMouseOver={(e) => {
                  e.currentTarget.style.backgroundColor = 'rgba(99,102,241,0.1)';
                }}
                onMouseOut={(e) => {
                  e.currentTarget.style.backgroundColor = 'transparent';
                }}
              >
                Browse Roadmaps
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {skills.map((skill) => {
                const score = Math.round(skill.trust_score || 0);

                return (
                  <Link
                    key={skill.roadmap_id}
                    to={`/roadmap/${skill.roadmap_id}`}
                    className="roadmap-card rounded-xl p-6 group cursor-pointer relative"
                  >
                    <div className="flex justify-between items-start mb-2">
                      <div className="flex items-center gap-2.5">
                        <div
                          className="w-2.5 h-2.5 rounded-full"
                          style={{ backgroundColor: getAccentColor(skill.roadmap_id) }}
                        />
                        <h3 className="title-font text-xl font-bold capitalize" style={{ color: 'var(--text-primary)' }}>
                          {skill.roadmap_id.replace(/-/g, ' ')}
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
                      {skill.total_courses || 0} topics
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

                        <span className="text-xs font-semibold" style={{ color: 'var(--text-muted)' }}>
                          {skill.completed_courses || 0} / {skill.total_courses || 0}
                        </span>
                      </div>

                      <div className="w-full h-[3px] rounded-full overflow-hidden" style={{ backgroundColor: 'var(--border)' }}>
                        <div
                          className="h-full rounded-full"
                          style={{
                            backgroundColor: 'var(--accent-primary)',
                            width: `${skill.progress_percent || 0}%`,
                            transition: 'width 0.5s ease-in-out'
                          }}
                        />
                      </div>
                    </div>
                  </Link>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
