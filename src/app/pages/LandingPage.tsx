import React, { useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Sparkles, ArrowRight, BookOpen, Target, TrendingUp, Search, Layout, Play, Activity } from 'lucide-react';
import { getToken } from '../../services/auth';

export function LandingPage() {
  const navigate = useNavigate();
  const token = getToken() || localStorage.getItem("access_token");

  useEffect(() => {
    if (token) {
      navigate('/dashboard');
    }
  }, [token, navigate]);

  const scrollToSection = (id: string) => {
    const el = document.getElementById(id);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth' });
    }
  };

  const monoStyle = { fontFamily: '"IBM Plex Mono", monospace' };

  return (
    <div className="min-h-screen bg-[#0A0A0F] font-sans text-white relative overflow-x-hidden">
      {/* Scanline / noise texture overlay */}
      <div className="pointer-events-none fixed inset-0 z-0 opacity-50" style={{
        backgroundImage: `repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0, 255, 178, 0.03) 2px, rgba(0, 255, 178, 0.03) 4px)`
      }}></div>

      {/* SECTION 1 — Navbar */}
      <nav className="sticky top-0 z-50 w-full border-b border-[#00FFB2]/20 bg-[#0A0A0F]/80 backdrop-blur-md">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 bg-[#111118] border border-[#00FFB2]/30 rounded-lg flex items-center justify-center shadow-[0_0_10px_rgba(0,255,178,0.1)]">
                <Layout className="w-5 h-5 text-[#00FFB2]" />
              </div>
              <span className="text-xl font-bold tracking-tight">LearnPath<span className="text-[#00FFB2]">AI</span></span>
            </div>

            <div className="hidden md:flex items-center gap-6">
              <button onClick={() => scrollToSection('features')} className="text-sm font-medium text-gray-300 hover:text-[#00FFB2] transition-colors">Features</button>
              <button onClick={() => scrollToSection('how-it-works')} className="text-sm font-medium text-gray-300 hover:text-[#00FFB2] transition-colors">How It Works</button>
              <button onClick={() => scrollToSection('roadmaps')} className="text-sm font-medium text-gray-300 hover:text-[#00FFB2] transition-colors">Roadmaps</button>
            </div>

            <div className="flex items-center gap-3">
              {token ? (
                <Link to="/dashboard" className="text-sm font-medium bg-[#111118] border border-[#00FFB2]/50 text-[#00FFB2] px-4 py-2 rounded-md hover:bg-[#00FFB2]/10 transition-colors shadow-[0_0_10px_rgba(0,255,178,0.1)]">
                  Dashboard
                </Link>
              ) : (
                <>
                  <Link to="/signin" className="text-sm font-medium text-gray-300 hover:text-[#00FFB2] transition-colors px-3 py-2 hidden sm:block">
                    Sign In
                  </Link>
                  <Link to="/signup" className="text-sm font-medium bg-transparent border border-[#00FFB2]/50 text-[#00FFB2] px-4 py-2 rounded-md hover:bg-[#00FFB2]/10 transition-colors shadow-[0_0_10px_rgba(0,255,178,0.1)]">
                    Get Started
                  </Link>
                </>
              )}
            </div>
          </div>
        </div>
      </nav>

      {/* SECTION 2 — Hero Section */}
      <div className="relative overflow-hidden py-20 lg:py-32">
        {/* Subtle animated gradient mesh background relative to hero */}
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-[#00FFB2]/10 rounded-full blur-[120px] pointer-events-none -z-10 animate-pulse"></div>
        <div className="absolute bottom-1/4 right-1/4 w-[30rem] h-[30rem] bg-indigo-600/10 rounded-full blur-[150px] pointer-events-none -z-10 animate-pulse delay-1000"></div>

        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
            <div className="space-y-8">
              <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-[#111118] border border-[rgba(0,255,178,0.3)] rounded-full backdrop-blur-sm shadow-[0_0_10px_rgba(0,255,178,0.1)]">
                <Sparkles className="w-4 h-4 text-[#00FFB2]" />
                <span className="text-sm font-medium text-gray-200" style={monoStyle}>Introducing Next-Gen Learning</span>
              </div>
              <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight leading-tight text-white">
                <span className="text-[#00FFB2] drop-shadow-[0_0_15px_rgba(0,255,178,0.3)]">AI-Powered</span> Personalized Engineering Learning Paths
              </h1>
              <p className="text-lg sm:text-xl text-gray-400 max-w-2xl">
                Master engineering skills faster with adaptive roadmaps, curated resources, and intelligent progress tracking — tailored specifically to your skill level.
              </p>
              <div className="flex flex-col sm:flex-row gap-4">
                <Link to="/signup" className="flex items-center justify-center gap-2 bg-transparent border border-[#00FFB2]/70 text-[#00FFB2] px-6 py-3 rounded-lg font-bold hover:bg-[#00FFB2]/10 transition-colors shadow-[0_0_15px_rgba(0,255,178,0.15)] hover:shadow-[0_0_20px_rgba(0,255,178,0.3)]">
                  Get Started Free
                  <ArrowRight className="w-5 h-5" />
                </Link>
                <Link to="/roadmaps" className="flex items-center justify-center gap-2 bg-[#111118]/80 border border-white/10 text-white px-6 py-3 rounded-lg font-bold hover:border-white/30 transition-colors backdrop-blur-sm">
                  Explore Roadmaps
                </Link>
              </div>
            </div>

            <div className="relative mx-auto w-full max-w-md lg:max-w-full">
              {/* Dashboard Preview Mockup */}
              <div className="aspect-[4/3] rounded-2xl bg-[#0A0A0F] border border-[rgba(0,255,178,0.2)] shadow-[0_0_30px_rgba(0,255,178,0.1)] p-4 overflow-hidden transform md:-rotate-2 hover:rotate-0 transition-transform duration-500 relative">
                <div className="absolute inset-0 bg-gradient-to-t from-[#0A0A0F] to-transparent z-10 pointer-events-none"></div>
                <div className="flex items-center gap-2 mb-4">
                  <div className="w-3 h-3 rounded-full bg-red-500/80"></div>
                  <div className="w-3 h-3 rounded-full bg-yellow-500/80"></div>
                  <div className="w-3 h-3 rounded-full bg-[#00FFB2]/80 shadow-[0_0_8px_rgba(0,255,178,0.5)]"></div>
                </div>
                <div className="space-y-4">
                  <div className="h-8 bg-[#111118] border border-white/5 rounded w-1/3"></div>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="h-24 bg-[#111118] border border-[rgba(0,255,178,0.15)] rounded-lg p-3 relative overflow-hidden">
                      <div className="absolute top-0 right-0 w-16 h-16 bg-[#00FFB2]/5 blur-2xl"></div>
                      <div className="h-4 bg-gray-700/50 w-1/2 rounded mb-2"></div>
                      <div className="h-2 bg-gray-800 w-full rounded mt-4">
                        <div className="h-2 bg-[#00FFB2] w-3/4 rounded shadow-[0_0_8px_rgba(0,255,178,0.5)]"></div>
                      </div>
                    </div>
                    <div className="h-24 bg-[#111118] rounded-lg p-3 border border-white/10">
                      <div className="h-4 bg-gray-700/50 w-2/3 rounded mb-2"></div>
                      <div className="h-2 bg-gray-800 w-full rounded mt-4">
                        <div className="h-2 bg-indigo-500 w-1/4 rounded"></div>
                      </div>
                    </div>
                  </div>
                  <div className="h-32 bg-[#111118] rounded-lg border border-[rgba(0,255,178,0.1)] p-4 relative z-0">
                    <div className="h-4 bg-gray-700/50 w-1/4 rounded mb-4"></div>
                    <div className="flex gap-2">
                      <div className="w-10 h-10 rounded-full bg-[#00FFB2]/10 border border-[#00FFB2]/30 flex items-center justify-center shadow-[0_0_10px_rgba(0,255,178,0.1)]">
                        <Play className="w-4 h-4 text-[#00FFB2]" />
                      </div>
                      <div className="flex-1 space-y-2 py-1">
                        <div className="h-3 bg-gray-700/50 rounded w-3/4"></div>
                        <div className="h-3 bg-gray-700/50 rounded w-1/2"></div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* SECTION 3 — Problem Section */}
      <div className="py-24 bg-[#0A0A0F] border-t border-white/5 relative z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-4xl font-bold text-white">Learning engineering skills is overwhelming</h2>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="bg-[#111118] p-8 rounded-2xl border border-[rgba(0,255,178,0.15)] flex flex-col items-center text-center transition-all hover:shadow-[0_0_15px_rgba(0,255,178,0.15),inset_0_0_8px_rgba(0,255,178,0.05)] hover:border-[rgba(0,255,178,0.4)]">
              <div className="w-12 h-12 bg-red-500/10 border border-red-500/20 text-red-400 rounded-xl flex items-center justify-center mb-6">
                <Search className="w-6 h-6" />
              </div>
              <h3 className="text-xl font-semibold mb-3 text-white">Too many resources, no clear path</h3>
              <p className="text-gray-400">Endless tutorials and documentation make it impossible to know where to start or what to learn next.</p>
            </div>
            <div className="bg-[#111118] p-8 rounded-2xl border border-[rgba(0,255,178,0.15)] flex flex-col items-center text-center transition-all hover:shadow-[0_0_15px_rgba(0,255,178,0.15),inset_0_0_8px_rgba(0,255,178,0.05)] hover:border-[rgba(0,255,178,0.4)]">
              <div className="w-12 h-12 bg-yellow-500/10 border border-yellow-500/20 text-yellow-400 rounded-xl flex items-center justify-center mb-6">
                <Target className="w-6 h-6" />
              </div>
              <h3 className="text-xl font-semibold mb-3 text-white">No personalized guidance</h3>
              <p className="text-gray-400">Generic courses don't adapt to your prior knowledge, forcing you to re-learn basics or skip advanced topics.</p>
            </div>
            <div className="bg-[#111118] p-8 rounded-2xl border border-[rgba(0,255,178,0.15)] flex flex-col items-center text-center transition-all hover:shadow-[0_0_15px_rgba(0,255,178,0.15),inset_0_0_8px_rgba(0,255,178,0.05)] hover:border-[rgba(0,255,178,0.4)]">
              <div className="w-12 h-12 bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 rounded-xl flex items-center justify-center mb-6">
                <Activity className="w-6 h-6" />
              </div>
              <h3 className="text-xl font-semibold mb-3 text-white">No progress tracking or feedback</h3>
              <p className="text-gray-400">Without a clear way to visualize progress, it's easy to lose motivation and give up halfway through.</p>
            </div>
          </div>
        </div>
      </div>

      {/* SECTION 4 — Solution Section */}
      <div id="features" className="py-24 bg-[#0A0A0F] border-t border-white/5 relative z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-4xl font-bold mb-4 text-white">Learn smarter with AI-guided learning paths</h2>
            <p className="text-xl text-gray-400 max-w-2xl mx-auto">Our intelligent platform creates the perfect curriculum for your unique journey.</p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="flex flex-col space-y-4 p-6 rounded-2xl hover:bg-[#111118]/50 border border-transparent hover:border-white/5 transition-all">
              <div className="w-12 h-12 bg-indigo-500/10 border border-indigo-500/30 text-indigo-400 rounded-xl flex items-center justify-center shadow-[0_0_10px_rgba(99,102,241,0.2)]">
                <Target className="w-6 h-6" />
              </div>
              <h3 className="text-xl font-bold text-white">Adaptive Learning Paths</h3>
              <p className="text-gray-400">
                Automatically adjusts difficulty based on your progress. Focus on what you need to learn, skip what you already know.
              </p>
            </div>
            <div className="flex flex-col space-y-4 p-6 rounded-2xl hover:bg-[#111118]/50 border border-transparent hover:border-white/5 transition-all">
              <div className="w-12 h-12 bg-blue-500/10 border border-blue-500/30 text-blue-400 rounded-xl flex items-center justify-center shadow-[0_0_10px_rgba(59,130,246,0.2)]">
                <BookOpen className="w-6 h-6" />
              </div>
              <h3 className="text-xl font-bold text-white">Curated Resources</h3>
              <p className="text-gray-400">
                Hand-picked, high-quality videos and documentation from trusted sources, perfectly aligned with each topic.
              </p>
            </div>
            <div className="flex flex-col space-y-4 p-6 rounded-2xl hover:bg-[#111118]/50 border border-transparent hover:border-white/5 transition-all">
              <div className="w-12 h-12 bg-[#00FFB2]/10 border border-[#00FFB2]/30 text-[#00FFB2] rounded-xl flex items-center justify-center shadow-[0_0_10px_rgba(0,255,178,0.2)]">
                <TrendingUp className="w-6 h-6" />
              </div>
              <h3 className="text-xl font-bold text-white">Progress Tracking</h3>
              <p className="text-gray-400">
                Track your learning journey and skill growth visually. Stay motivated with continuous feedback and mastery levels.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* SECTION 5 — Product Preview Section */}
      <div className="py-24 bg-[#0A0A0F] border-t border-white/5 overflow-hidden relative z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="bg-[#111118] rounded-3xl shadow-[0_0_30px_rgba(0,255,178,0.05)] border border-[rgba(0,255,178,0.15)] overflow-hidden transition-all hover:shadow-[0_0_30px_rgba(0,255,178,0.1)]">
            <div className="flex items-center gap-2 px-6 py-4 border-b border-white/5 bg-[#0A0A0F]/50">
              <div className="w-3 h-3 rounded-full bg-red-500/80"></div>
              <div className="w-3 h-3 rounded-full bg-yellow-500/80"></div>
              <div className="w-3 h-3 rounded-full bg-[#00FFB2]/80"></div>
              <div className="ml-4 text-sm font-medium text-gray-500 flex-1 text-center" style={monoStyle}>app.learnpathai.com/dashboard</div>
            </div>
            <div className="p-8 bg-[#111118] relative">
              <div className="grid grid-cols-1 lg:grid-cols-4 gap-8 relative z-10">
                {/* Sidebar Mock */}
                <div className="hidden lg:flex flex-col gap-4">
                  <div className="h-8 w-8 bg-[#00FFB2]/20 border border-[#00FFB2]/50 rounded-lg mb-8 shadow-[0_0_10px_rgba(0,255,178,0.1)]"></div>
                  <div className="h-10 bg-[#00FFB2]/10 border border-[#00FFB2]/20 rounded-md w-full"></div>
                  <div className="h-10 bg-white/5 border border-white/10 rounded-md w-full"></div>
                  <div className="h-10 bg-white/5 border border-white/10 rounded-md w-full"></div>
                </div>
                {/* Main Content Mock */}
                <div className="lg:col-span-3 space-y-8">
                  <div className="flex justify-between items-center">
                    <div className="h-8 bg-gray-800 rounded w-1/3"></div>
                    <div className="h-10 bg-[#00FFB2]/20 border border-[#00FFB2]/30 rounded w-32"></div>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                    <div className="bg-[#0A0A0F] p-6 rounded-xl border border-white/10 shadow-sm flex flex-col">
                      <div className="h-6 bg-gray-800 rounded w-1/2 mb-4"></div>
                      <div className="h-4 bg-gray-900 rounded w-full mb-2"></div>
                      <div className="h-4 bg-gray-900 rounded w-2/3 mb-6"></div>
                      <div className="mt-auto">
                        <div className="flex justify-between text-sm mb-2 text-gray-400" style={monoStyle}>
                          <span>Progress</span>
                          <span className="text-[#00FFB2]">75%</span>
                        </div>
                        <div className="h-2 bg-gray-900 rounded-full w-full overflow-hidden">
                          <div className="h-full bg-[#00FFB2] w-3/4 shadow-[0_0_10px_rgba(0,255,178,0.5)]"></div>
                        </div>
                      </div>
                    </div>
                    <div className="bg-[#0A0A0F] p-6 rounded-xl border border-white/10 shadow-sm flex flex-col">
                      <div className="h-6 bg-gray-800 rounded w-2/3 mb-4"></div>
                      <div className="h-4 bg-gray-900 rounded w-full mb-2"></div>
                      <div className="h-4 bg-gray-900 rounded w-3/4 mb-6"></div>
                      <div className="mt-auto">
                        <div className="flex justify-between text-sm mb-2 text-gray-400" style={monoStyle}>
                          <span>Progress</span>
                          <span className="text-indigo-400">30%</span>
                        </div>
                        <div className="h-2 bg-gray-900 rounded-full w-full overflow-hidden">
                          <div className="h-full bg-indigo-500 w-1/3"></div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* SECTION 6 — How It Works Section */}
      <div id="how-it-works" className="py-24 bg-[#0A0A0F] border-t border-white/5 relative z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-4xl font-bold mb-4 text-white">How it works</h2>
            <p className="text-xl text-gray-400">Your journey to mastery in 3 simple steps</p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-12 relative">
            <div className="hidden md:block absolute top-12 left-[15%] right-[15%] h-0.5 bg-gray-800"></div>

            <div className="relative flex flex-col items-center text-center z-10">
              <div className="w-24 h-24 bg-[#111118] border-2 border-indigo-500/20 shadow-[0_0_15px_rgba(99,102,241,0.15)] rounded-full flex items-center justify-center mb-6">
                <Target className="w-10 h-10 text-indigo-400" />
              </div>
              <h3 className="text-xl font-bold mb-3 text-white" style={monoStyle}>1. Choose a roadmap</h3>
              <p className="text-gray-400">Select your target engineering discipline and let AI assess your current skill level.</p>
            </div>

            <div className="relative flex flex-col items-center text-center z-10">
              <div className="w-24 h-24 bg-[#111118] border-2 border-blue-500/20 shadow-[0_0_15px_rgba(59,130,246,0.15)] rounded-full flex items-center justify-center mb-6">
                <BookOpen className="w-10 h-10 text-blue-400" />
              </div>
              <h3 className="text-xl font-bold mb-3 text-white" style={monoStyle}>2. Learn from curated resources</h3>
              <p className="text-gray-400">Dive into the right materials at the right time, perfectly matched to your progression.</p>
            </div>

            <div className="relative flex flex-col items-center text-center z-10">
              <div className="w-24 h-24 bg-[#111118] border-2 border-[#00FFB2]/30 shadow-[0_0_15px_rgba(0,255,178,0.2)] rounded-full flex items-center justify-center mb-6">
                <TrendingUp className="w-10 h-10 text-[#00FFB2]" />
              </div>
              <h3 className="text-xl font-bold mb-3 text-white" style={monoStyle}>3. Track progress and improve</h3>
              <p className="text-gray-400">Monitor your proficiency, pass assessments, and visually see your engineering skills grow.</p>
            </div>
          </div>
        </div>
      </div>

      {/* SECTION 7 — Roadmaps Section */}
      <div id="roadmaps" className="py-24 bg-[#111118]/40 border-t border-white/5 relative z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-4xl font-bold mb-4 text-white">Explore our roadmaps</h2>
            <p className="text-xl text-gray-400">Comprehensive technical paths for modern engineers</p>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {['Backend', 'AI Engineering', 'Full Stack', 'DevOps', 'Cloud', 'Computer Science'].map((category) => (
              <Link
                key={category}
                to="/signup"
                className="group p-8 bg-[#111118] border border-[rgba(0,255,178,0.15)] rounded-2xl flex items-center justify-between transition-all hover:shadow-[0_0_12px_rgba(0,255,178,0.2),inset_0_0_8px_rgba(0,255,178,0.05)] hover:border-[rgba(0,255,178,0.5)]"
              >
                <span className="text-lg font-semibold text-gray-200 group-hover:text-[#00FFB2] transition-colors" style={monoStyle}>{category}</span>
                <ArrowRight className="w-5 h-5 text-gray-500 group-hover:text-[#00FFB2] transition-colors transform group-hover:translate-x-1" />
              </Link>
            ))}
          </div>
        </div>
      </div>

      {/* SECTION 8 — Call to Action Section */}
      <div className="py-32 bg-[#0A0A0F] border-t border-white/5 relative overflow-hidden z-10">
        <div className="absolute inset-0 bg-[#00FFB2]/5 animate-pulse"></div>
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10 text-center">
          <h2 className="text-4xl sm:text-5xl font-extrabold tracking-tight mb-8 text-white">Start learning smarter today</h2>
          <p className="text-xl text-gray-400 mb-10 max-w-2xl mx-auto">
            Join thousands of developers who are mastering new skills with personalized, AI-driven learning paths.
          </p>
          <Link to="/signup" className="inline-flex items-center justify-center gap-2 bg-transparent border border-[#00FFB2]/70 text-[#00FFB2] px-8 py-4 rounded-xl text-lg font-bold hover:bg-[#00FFB2]/10 transition-all shadow-[0_0_15px_rgba(0,255,178,0.15)] hover:shadow-[0_0_25px_rgba(0,255,178,0.3)] hover:-translate-y-1">
            Create Free Account
            <ArrowRight className="w-6 h-6" />
          </Link>
        </div>
      </div>

      {/* SECTION 9 — Footer */}
      <footer className="py-12 bg-[#0A0A0F] border-t border-white/10 relative z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col md:flex-row justify-between items-center gap-6">
          <div className="flex flex-col text-center md:text-left">
            <span className="text-2xl font-bold text-white mb-2 tracking-tight">LearnPath<span className="text-[#00FFB2]">AI</span></span>
            <span className="text-sm text-gray-500">Engineering Learning Platform</span>
          </div>
          <div className="flex gap-8">
            <Link to="/signin" className="text-gray-400 hover:text-[#00FFB2] transition-colors">Sign In</Link>
            <Link to="/signup" className="text-gray-300 hover:text-[#00FFB2] transition-colors font-medium">Sign Up</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
