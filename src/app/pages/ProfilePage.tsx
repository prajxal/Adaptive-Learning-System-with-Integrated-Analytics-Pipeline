import React, { useEffect, useState } from 'react';
import { Trophy, Target, Flame, Award, Github, FileText, Activity, Check, Brain } from 'lucide-react';
import { getUserProfile } from '../../services/userApi';
import { useNavigate } from 'react-router-dom';

export function ProfilePage() {
  const [profile, setProfile] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    getUserProfile()
      .then(data => {
        setProfile(data);
      })
      .catch(err => {
        console.error(err);
      })
      .finally(() => {
        setLoading(false);
      });
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#00FFB2]"></div>
      </div>
    );
  }

  if (!profile) {
    return <div className="text-white text-center">Failed to load profile.</div>;
  }

  return (
    <div className="space-y-8 dashboard-profile pb-10">
      <style>{`
        .dashboard-profile {
          --bg-card: #111118;
          --border: #1e1e2e;
          --accent: #00FFB2;
          font-family: 'DM Sans', sans-serif;
        }
        .dark-card {
          background-color: var(--bg-card);
          border: 1px solid var(--border);
          border-radius: 0.75rem;
        }
        .font-sora {
          font-family: 'Sora', sans-serif;
        }
      `}</style>

      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-white mb-2 font-sora">Your Profile</h1>
        <p className="text-gray-400">Track your learning journey and connected accounts</p>
      </div>

      {/* Profile Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="dark-card p-6 flex flex-col items-center justify-center text-center transition-all hover:border-[#00FFB2]/50 hover:shadow-[0_0_15px_rgba(0,255,178,0.1)]">
          <div className="w-16 h-16 rounded-full bg-indigo-500/10 border border-indigo-500/30 flex items-center justify-center mb-4">
            <Trophy className="w-8 h-8 text-indigo-400" />
          </div>
          <h3 className="text-3xl font-bold text-white mb-1">{Math.round(profile.global_elo_rating || 1000)}</h3>
          <p className="text-sm text-gray-400 font-mono">Global Elo Rating</p>
        </div>

        <div className="dark-card p-6 flex flex-col items-center justify-center text-center transition-all hover:border-[#00FFB2]/50 hover:shadow-[0_0_15px_rgba(0,255,178,0.1)]">
          <div className="w-16 h-16 rounded-full bg-[#00FFB2]/10 border border-[#00FFB2]/30 flex items-center justify-center mb-4">
            <Target className="w-8 h-8 text-[#00FFB2]" />
          </div>
          <h3 className="text-3xl font-bold text-white mb-1">{profile.completed_courses || 0}</h3>
          <p className="text-sm text-gray-400 font-mono">Courses Completed</p>
        </div>

        <div className="dark-card p-6 flex flex-col items-center justify-center text-center transition-all hover:border-[#00FFB2]/50 hover:shadow-[0_0_15px_rgba(0,255,178,0.1)]">
          <div className="w-16 h-16 rounded-full bg-blue-500/10 border border-blue-500/30 flex items-center justify-center mb-4">
            <Flame className="w-8 h-8 text-blue-400" />
          </div>
          <h3 className="text-xl font-bold text-white mb-1 capitalize">
            {profile.top_skills?.length > 0 ? profile.top_skills[0].replace(/-/g, ' ') : "None yet"}
          </h3>
          <p className="text-sm text-gray-400 font-mono">Top Skill Area</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Integrations Card */}
        <div className="dark-card p-6">
          <h3 className="text-xl font-semibold mb-6 text-white font-sora">Connected Accounts</h3>

          <div className="space-y-4">
            <div className="flex items-center justify-between p-4 bg-[#0A0A0F] border border-white/5 rounded-lg">
              <div className="flex items-center gap-4">
                <Github className="w-6 h-6 text-white" />
                <div>
                  <p className="font-medium text-white">GitHub</p>
                  <p className="text-xs text-gray-400 mt-1">
                    {profile.github_sync_status === 'completed' ? 'Skills analyzed from repositories' :
                      profile.github_sync_status === 'syncing' ? 'Analyzing repositories...' :
                        'Not connected'}
                  </p>
                </div>
              </div>
              <div>
                {profile.github_sync_status === 'completed' ? (
                  <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-green-500/10 text-green-400 border border-green-500/20">
                    <Check className="w-3 h-3" /> GitHub skills updated
                  </span>
                ) : profile.github_sync_status === 'syncing' ? (
                  <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-yellow-500/10 text-yellow-400 border border-yellow-500/20 animate-pulse">
                    <Activity className="w-3 h-3" /> Syncing...
                  </span>
                ) : (
                  <button onClick={() => navigate('/dashboard')} className="text-sm text-[#00FFB2] hover:underline">Connect</button>
                )}
              </div>
            </div>

            <div className="flex items-center justify-between p-4 bg-[#0A0A0F] border border-white/5 rounded-lg">
              <div className="flex items-center gap-4">
                <FileText className="w-6 h-6 text-blue-400" />
                <div>
                  <p className="font-medium text-white">Resume</p>
                  <p className="text-xs text-gray-400 mt-1">Extraction of professional experience</p>
                </div>
              </div>
              <div>
                {profile.resume_status === 'completed' ? (
                  <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-green-500/10 text-green-400 border border-green-500/20">
                    <Check className="w-3 h-3" /> Uploaded
                  </span>
                ) : profile.resume_status === 'processing' ? (
                  <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-yellow-500/10 text-yellow-400 border border-yellow-500/20 animate-pulse">
                    <Activity className="w-3 h-3" /> Processing...
                  </span>
                ) : (
                  <button onClick={() => navigate('/dashboard')} className="text-sm text-[#00FFB2] hover:underline">Upload</button>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Top Skills Breakdown */}
        <div className="dark-card p-6">
          <h3 className="text-xl font-semibold mb-6 text-white font-sora">Top Skill Areas</h3>

          {profile.top_skills && profile.top_skills.length > 0 ? (
            <div className="space-y-4">
              {profile.top_skills.map((skill: string, idx: number) => (
                <div key={skill} className="p-4 bg-[#0A0A0F] border border-white/5 rounded-lg flex items-center justify-between transition-all hover:border-[#00FFB2]/30">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded bg-white/5 flex items-center justify-center text-[#00FFB2] font-mono text-xs border border-white/10">
                      #{idx + 1}
                    </div>
                    <span className="font-medium text-white capitalize">{skill.replace(/-/g, ' ')}</span>
                  </div>
                  <Award className="w-5 h-5 text-gray-500" />
                </div>
              ))}
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center h-40 text-center">
              <Brain className="w-8 h-8 text-gray-600 mb-3" />
              <p className="text-sm text-gray-400">No skills assessed yet.<br />Complete roadmaps to build your profile.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
