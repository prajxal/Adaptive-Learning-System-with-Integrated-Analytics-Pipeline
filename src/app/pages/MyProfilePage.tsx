import React, { useEffect, useRef, useState } from "react";
import { useLocation } from "react-router-dom";
import { useUser } from "@clerk/clerk-react";
import { usePostHog } from "@posthog/react";
import { Check, RefreshCw, Unlink } from "lucide-react";
import { getGithubAnalysis, getGithubStatus, redirectToGithubConnect } from "../../services/githubApi";
import { uploadResume, checkResumeStatus as getResumeStatus } from "../../services/resumeApi";
import BACKEND_URL, { fetchWithAuth } from "../../services/api";
import GithubInsightsCard from "../../components/dashboard/GithubInsightsCard";

interface GithubAnalysis {
  connected?: boolean;
  username?: string;
  languages?: { skill: string; weight: number; confidence: number }[];
  last_sync?: string | null;
  repo_count?: number;
  repositories?: unknown[];
}

const PAGE_STYLES = `
  @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Sora:wght@400;500;600;700;800&display=swap');
  .profile-root {
    --bg-primary: #0a0a0f;
    --bg-card: #111118;
    --bg-card-hover: #16161f;
    --accent-primary: #6366f1;
    --text-primary: #f1f5f9;
    --text-muted: #64748b;
    --border: #1e1e2e;
    background-color: var(--bg-primary);
    color: var(--text-primary);
    font-family: 'DM Sans', sans-serif;
    min-height: 100vh;
    position: relative;
  }
  .profile-bg {
    position: absolute; top: 0; left: 0; right: 0; bottom: 0;
    background: radial-gradient(ellipse at 20% 0%, rgba(99,102,241,0.06) 0%, transparent 60%);
    pointer-events: none; z-index: 0;
  }
  .profile-content {
    position: relative; z-index: 1;
    max-width: 800px; margin: 0 auto; padding: 3rem 1.5rem;
  }
  .title-font { font-family: 'Sora', sans-serif; }
  .dark-card {
    background-color: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 0.75rem;
  }
  .upload-zone {
    border: 1px dashed var(--border);
    transition: border-color 0.2s ease;
  }
  .upload-zone:hover { border-color: var(--accent-primary); cursor: pointer; }
  .upload-btn {
    background-color: #16161f;
    border: 1px solid var(--border);
    color: var(--text-primary);
    transition: border-color 0.2s ease;
  }
  .upload-btn:hover { border-color: var(--accent-primary); }
  .action-btn {
    background-color: #16161f;
    border: 1px solid var(--border);
    color: var(--text-primary);
    transition: border-color 0.2s ease, opacity 0.2s ease;
    padding: 0.5rem 1rem;
    border-radius: 0.375rem;
    font-size: 0.875rem;
    font-weight: 500;
    display: inline-flex;
    align-items: center;
    gap: 0.375rem;
  }
  .action-btn:hover:not(:disabled) { border-color: var(--accent-primary); }
  .action-btn:disabled { opacity: 0.5; cursor: not-allowed; }
  .danger-btn {
    background-color: #16161f;
    border: 1px solid var(--border);
    color: #ef4444;
    transition: border-color 0.2s ease, opacity 0.2s ease;
    padding: 0.5rem 1rem;
    border-radius: 0.375rem;
    font-size: 0.875rem;
    font-weight: 500;
    display: inline-flex;
    align-items: center;
    gap: 0.375rem;
  }
  .danger-btn:hover:not(:disabled) { border-color: #ef4444; }
  .danger-btn:disabled { opacity: 0.5; cursor: not-allowed; }
`;

export default function MyProfilePage() {
  const { user } = useUser();
  const location = useLocation();
  const posthog = usePostHog();

  const [githubConnected, setGithubConnected] = useState(false);
  const [githubUsername, setGithubUsername] = useState("");
  const [githubAnalysis, setGithubAnalysis] = useState<GithubAnalysis | null>(null);
  const [githubActionLoading, setGithubActionLoading] = useState(false);
  const [githubSuccess, setGithubSuccess] = useState(false);

  const [resumeStatus, setResumeStatus] = useState<string | null>(null);
  const [resumeUploading, setResumeUploading] = useState(false);

  const [rebuildLoading, setRebuildLoading] = useState(false);
  const [rebuildSuccess, setRebuildSuccess] = useState(false);

  const [loading, setLoading] = useState(true);

  const githubPollingRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    return () => {
      if (githubPollingRef.current) clearInterval(githubPollingRef.current);
    };
  }, []);

  // Handle OAuth callback redirect
  useEffect(() => {
    const params = new URLSearchParams(location.search);
    if (params.get("github") === "connected") {
      setGithubSuccess(true);
      window.history.replaceState({}, document.title, location.pathname);
      setTimeout(() => setGithubSuccess(false), 5000);
    }
  }, [location]);

  const fetchGithubData = async () => {
    const [statusResult, analysisResult] = await Promise.allSettled([
      getGithubStatus(),
      getGithubAnalysis(),
    ]);
    if (statusResult.status === "fulfilled") {
      setGithubConnected(statusResult.value.connected);
      setGithubUsername(statusResult.value.username || "");
      if (statusResult.value.sync_status === "syncing") startGithubPolling();
    }
    if (analysisResult.status === "fulfilled") {
      setGithubAnalysis(analysisResult.value);
    }
  };

  const fetchResumeStatus = async () => {
    try {
      const res = await getResumeStatus();
      setResumeStatus(res?.status || null);
    } catch {
      setResumeStatus(null);
    }
  };

  useEffect(() => {
    const init = async () => {
      try {
        await Promise.all([fetchGithubData(), fetchResumeStatus()]);
      } finally {
        setLoading(false);
      }
    };
    init();
  }, []);

  const startGithubPolling = () => {
    if (githubPollingRef.current) return;
    githubPollingRef.current = setInterval(async () => {
      try {
        const res = await getGithubStatus();
        if (res.sync_status === "completed" || res.sync_status === "failed") {
          clearInterval(githubPollingRef.current!);
          githubPollingRef.current = null;
          if (res.sync_status === "completed") {
            const analysis = await getGithubAnalysis();
            setGithubAnalysis(analysis);
            setGithubSuccess(true);
            posthog?.capture("github_synced", {
              repo_count: (analysis as any)?.repo_count,
              language_count: analysis?.languages?.length,
            });
            setTimeout(() => setGithubSuccess(false), 5000);
          } else {
            posthog?.capture("github_sync_failed");
            alert("GitHub processing failed.");
          }
        }
      } catch (err) {
        posthog?.captureException(err);
      }
    }, 5000);
  };

  const handleSyncGithub = async () => {
    try {
      setGithubActionLoading(true);
      const response = await fetchWithAuth(`${BACKEND_URL}/github/sync`, { method: "POST" });
      if (!response.ok) throw new Error(await response.text());
      await fetchGithubData();
    } catch {
      posthog?.capture("github_manual_sync_failed");
      alert("GitHub sync failed. Please try again.");
    } finally {
      setGithubActionLoading(false);
    }
  };

  const handleDisconnectGithub = async () => {
    try {
      setGithubActionLoading(true);
      const response = await fetchWithAuth(`${BACKEND_URL}/github/disconnect`, { method: "DELETE" });
      if (!response.ok) throw new Error(await response.text());
      setGithubConnected(false);
      setGithubUsername("");
      setGithubAnalysis(null);
    } catch {
      posthog?.capture("github_disconnect_failed");
      alert("GitHub disconnect failed. Please try again.");
    } finally {
      setGithubActionLoading(false);
    }
  };

  async function pollResumeStatus() {
    const maxAttempts = 20;
    try {
      for (let i = 0; i < maxAttempts; i++) {
        const response = await getResumeStatus();
        const status = response?.status;
        setResumeStatus(status);
        if (status === "completed") return;
        if (status === "failed") {
          posthog?.capture("resume_processing_failed");
          alert("Resume processing failed. Please try again.");
          return;
        }
        await new Promise((resolve) => setTimeout(resolve, 3000));
      }
      posthog?.capture("resume_processing_failed");
      alert("Resume processing timed out. Please try again.");
    } catch (err: any) {
      posthog?.captureException(err);
      alert("Resume processing failed. Please try again.");
    } finally {
      setResumeUploading(false);
    }
  }

  async function handleResumeUpload(e: React.ChangeEvent<HTMLInputElement>) {
    if (!e.target.files?.length) return;
    const file = e.target.files[0];
    setResumeUploading(true);
    setResumeStatus("processing");
    try {
      await uploadResume(file);
      posthog?.capture("resume_uploaded", { file_name: file.name, file_size: file.size });
      await pollResumeStatus();
    } catch (err: any) {
      posthog?.captureException(err);
      alert("Resume upload failed");
      setResumeUploading(false);
    }
  }

  const handleRebuildSkillProfile = async () => {
    try {
      setRebuildLoading(true);
      const response = await fetchWithAuth(`${BACKEND_URL}/users/me/skills/rebuild`, { method: "POST" });
      if (!response.ok) throw new Error(await response.text());
      setRebuildSuccess(true);
      posthog?.capture("skill_profile_rebuilt");
      setTimeout(() => setRebuildSuccess(false), 5000);
    } catch {
      alert("Failed to rebuild skill profile. Please try again.");
    } finally {
      setRebuildLoading(false);
    }
  };

  return (
    <div className="profile-root">
      <style>{PAGE_STYLES}</style>
      <div className="profile-bg" />
      <div className="profile-content">

        {/* Page Header */}
        <div className="mb-8">
          <h1 className="title-font text-4xl font-bold tracking-tight mb-2">My Profile</h1>
          <p className="text-lg" style={{ color: "var(--text-muted)" }}>
            Manage your account, integrations, and skill data.
          </p>
        </div>

        {/* ── 1. ACCOUNT ── */}
        <div className="dark-card p-6 mb-6">
          <h2 className="title-font text-xl font-semibold mb-5">Account</h2>
          {loading || !user ? (
            <div className="flex items-center gap-4">
              <div
                className="w-14 h-14 rounded-full animate-pulse shrink-0"
                style={{ backgroundColor: "var(--border)" }}
              />
              <div className="space-y-2 flex-1">
                <div className="h-4 w-40 rounded animate-pulse" style={{ backgroundColor: "var(--border)" }} />
                <div className="h-3 w-56 rounded animate-pulse" style={{ backgroundColor: "var(--border)" }} />
              </div>
            </div>
          ) : (
            <div className="flex items-center gap-4">
              {user.imageUrl ? (
                <img
                  src={user.imageUrl}
                  alt={user.fullName || "Avatar"}
                  className="w-14 h-14 rounded-full object-cover border shrink-0"
                  style={{ borderColor: "var(--border)" }}
                />
              ) : (
                <div
                  className="w-14 h-14 rounded-full flex items-center justify-center text-lg font-bold shrink-0"
                  style={{ backgroundColor: "rgba(99,102,241,0.15)", color: "var(--accent-primary)" }}
                >
                  {(user.fullName || user.primaryEmailAddress?.emailAddress || "?")[0].toUpperCase()}
                </div>
              )}
              <div>
                <p className="font-semibold" style={{ color: "var(--text-primary)" }}>
                  {user.fullName || "—"}
                </p>
                <p className="text-sm mt-0.5" style={{ color: "var(--text-muted)" }}>
                  {user.primaryEmailAddress?.emailAddress || "—"}
                </p>
              </div>
            </div>
          )}
        </div>

        {/* ── 2. CONNECTED ACCOUNTS ── */}
        <div className="dark-card p-6 mb-6">
          <div className="flex items-center justify-between mb-5">
            <h2 className="title-font text-xl font-semibold">Connected Accounts</h2>
            {githubSuccess && (
              <span className="text-sm font-medium text-green-400 bg-green-400/10 px-3 py-1 rounded-full">
                GitHub Linked!
              </span>
            )}
          </div>

          <div
            className="rounded-lg p-4"
            style={{ backgroundColor: "rgba(99,102,241,0.04)", border: "1px solid var(--border)" }}
          >
            <div className="flex items-center justify-between gap-4 flex-wrap">
              <div className="flex items-center gap-3">
                <div
                  className="w-9 h-9 rounded-lg flex items-center justify-center shrink-0"
                  style={{ backgroundColor: "var(--bg-card-hover)", border: "1px solid var(--border)" }}
                >
                  <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor" style={{ color: "var(--text-primary)" }}>
                    <path d="M12 0C5.374 0 0 5.373 0 12c0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23A11.509 11.509 0 0112 5.803c1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.929.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576C20.566 21.797 24 17.3 24 12c0-6.627-5.373-12-12-12z" />
                  </svg>
                </div>
                <div>
                  <p className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>GitHub</p>
                  {loading ? (
                    <div className="h-3 w-24 rounded animate-pulse mt-1" style={{ backgroundColor: "var(--border)" }} />
                  ) : githubConnected ? (
                    <span className="inline-flex items-center gap-1 text-xs font-medium mt-0.5" style={{ color: "#22c55e" }}>
                      <Check className="w-3 h-3" />
                      @{githubUsername}
                    </span>
                  ) : (
                    <p className="text-xs mt-0.5" style={{ color: "var(--text-muted)" }}>Not connected</p>
                  )}
                </div>
              </div>

              <div className="flex gap-2 flex-wrap">
                {githubConnected ? (
                  <>
                    <button
                      className="action-btn"
                      onClick={handleSyncGithub}
                      disabled={githubActionLoading}
                    >
                      <RefreshCw className={`w-3.5 h-3.5 ${githubActionLoading ? "animate-spin" : ""}`} />
                      {githubActionLoading ? "Syncing..." : "Sync"}
                    </button>
                    <button
                      className="danger-btn"
                      onClick={handleDisconnectGithub}
                      disabled={githubActionLoading}
                    >
                      <Unlink className="w-3.5 h-3.5" />
                      Disconnect
                    </button>
                  </>
                ) : (
                  <button
                    className="action-btn"
                    onClick={() => {
                      posthog?.capture("github_connect_clicked");
                      redirectToGithubConnect();
                    }}
                    disabled={loading}
                  >
                    Connect GitHub
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* ── 3. RESUME ── */}
        <div className="dark-card p-6 mb-6">
          <h2 className="title-font text-xl font-semibold mb-1">Resume</h2>
          <p className="text-sm mb-5" style={{ color: "var(--text-muted)" }}>
            Upload your PDF resume to auto-detect skills and improve recommendations.
          </p>

          {resumeStatus === "completed" && !resumeUploading && (
            <div
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium mb-4"
              style={{
                backgroundColor: "rgba(34,197,94,0.1)",
                color: "#22c55e",
                border: "1px solid rgba(34,197,94,0.2)",
              }}
            >
              <Check className="w-3.5 h-3.5" />
              Resume processed successfully
            </div>
          )}

          <div className="upload-zone rounded-lg relative overflow-hidden flex items-center p-1">
            <input
              type="file"
              accept=".pdf"
              onChange={handleResumeUpload}
              disabled={resumeUploading}
              className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10"
            />
            <div className="flex w-full items-center">
              <div className="upload-btn px-4 py-2 rounded-md text-sm font-medium z-0 pointer-events-none">
                Choose file
              </div>
              <div className="flex-1 flex items-center px-4 text-sm z-0" style={{ color: "var(--text-muted)" }}>
                {resumeUploading ? "Processing..." : "PDF only · No file chosen"}
              </div>
            </div>
          </div>
        </div>

        {/* ── 4. DEVELOPER PROFILE ── */}
        <div className="mb-6">
          <GithubInsightsCard githubAnalysis={githubAnalysis} loading={loading} />
        </div>

        {/* ── 5. SKILL PROFILE ── */}
        <div className="dark-card p-6">
          <div className="flex items-start justify-between gap-6 flex-wrap">
            <div>
              <h2 className="title-font text-xl font-semibold mb-1">Skill Profile</h2>
              <p className="text-sm" style={{ color: "var(--text-muted)" }}>
                Re-synthesize your skill profile from your GitHub and resume data.
                Use this after syncing new data to update your skill levels.
              </p>
            </div>
            <div className="flex flex-col items-end gap-2 shrink-0">
              <button
                className="action-btn"
                onClick={handleRebuildSkillProfile}
                disabled={rebuildLoading}
              >
                {rebuildLoading ? "Rebuilding..." : "Rebuild Skill Profile"}
              </button>
              {rebuildSuccess && (
                <span className="text-xs font-medium" style={{ color: "#22c55e" }}>
                  Skill profile rebuilt successfully!
                </span>
              )}
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}
