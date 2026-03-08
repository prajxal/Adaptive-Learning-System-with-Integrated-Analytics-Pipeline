import React from 'react';
import { Target, BookOpen, TrendingUp, Layout } from 'lucide-react';
import { Link } from 'react-router-dom';

interface AuthLayoutProps {
    children: React.ReactNode;
}

export function AuthLayout({ children }: AuthLayoutProps) {
    return (
        <div className="flex min-h-screen bg-[#0A0A0F]">
            {/* Scanline / noise texture overlay */}
            <div className="pointer-events-none absolute inset-0 z-10 opacity-50" style={{
                backgroundImage: `repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0, 255, 178, 0.03) 2px, rgba(0, 255, 178, 0.03) 4px)`
            }}></div>

            {/* Left Marketing Section - Hidden on mobile, 55% width on desktop */}
            <div className="hidden md:flex flex-col justify-between w-[55%] relative overflow-hidden p-12 text-white border-r border-[#00FFB2]/20">
                {/* Decorative background elements */}
                <div className="absolute top-0 right-0 -m-16 w-64 h-64 bg-[#00FFB2]/5 rounded-full blur-3xl"></div>
                <div className="absolute bottom-0 left-0 -m-32 w-96 h-96 bg-[#00FFB2]/5 rounded-full blur-3xl"></div>

                <div className="relative z-20 flex flex-col h-full">
                    {/* Brand/Logo */}
                    <div className="flex items-center gap-3 mb-16">
                        <div className="w-10 h-10 bg-[#111118] border border-[#00FFB2]/30 rounded-xl flex items-center justify-center shadow-[0_0_15px_rgba(0,255,178,0.15)]">
                            <Layout className="w-6 h-6 text-[#00FFB2]" />
                        </div>
                        <Link to="/" className="text-2xl font-bold tracking-tight text-white">LearnPath<span className="text-[#00FFB2]">AI</span></Link>
                    </div>

                    {/* Marketing Copy */}
                    <div className="flex-1 flex flex-col justify-center max-w-lg">
                        <h1 className="text-4xl lg:text-5xl font-extrabold tracking-tight leading-tight mb-6 text-white">
                            Master Engineering Skills Faster
                        </h1>
                        <p className="text-lg text-gray-400 mb-10 leading-relaxed">
                            AI-powered adaptive roadmaps, curated resources, and progress tracking tailored to your level.
                        </p>

                        {/* Feature Bullets */}
                        <div className="space-y-6">
                            <div className="flex items-start gap-4">
                                <div className="w-10 h-10 rounded-full bg-[#111118] flex items-center justify-center flex-shrink-0 border border-[#00FFB2]/20 shadow-[0_0_10px_rgba(0,255,178,0.1)]">
                                    <Target className="w-5 h-5 text-[#00FFB2]" />
                                </div>
                                <div>
                                    <h3 className="font-semibold text-lg text-white">Adaptive Learning Paths</h3>
                                    <p className="text-gray-400 text-sm">Dynamic curriculums that adjust to your existing knowledge.</p>
                                </div>
                            </div>

                            <div className="flex items-start gap-4">
                                <div className="w-10 h-10 rounded-full bg-[#111118] flex items-center justify-center flex-shrink-0 border border-[#00FFB2]/20 shadow-[0_0_10px_rgba(0,255,178,0.1)]">
                                    <BookOpen className="w-5 h-5 text-[#00FFB2]" />
                                </div>
                                <div>
                                    <h3 className="font-semibold text-lg text-white">Curated Resources</h3>
                                    <p className="text-gray-400 text-sm">High-quality handpicked materials from roadmap.sh.</p>
                                </div>
                            </div>

                            <div className="flex items-start gap-4">
                                <div className="w-10 h-10 rounded-full bg-[#111118] flex items-center justify-center flex-shrink-0 border border-[#00FFB2]/20 shadow-[0_0_10px_rgba(0,255,178,0.1)]">
                                    <TrendingUp className="w-5 h-5 text-[#00FFB2]" />
                                </div>
                                <div>
                                    <h3 className="font-semibold text-lg text-white">Track Progress</h3>
                                    <p className="text-gray-400 text-sm">Visualize your skill growth and mastery over time.</p>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div className="mt-8">
                        <p className="text-sm text-gray-500 font-medium">© {new Date().getFullYear()} LearnPathAI. All rights reserved.</p>
                    </div>
                </div>
            </div>

            {/* Right Form Section - 100% on mobile, 45% on desktop */}
            <div className="flex-1 flex flex-col justify-center px-4 sm:px-6 lg:px-8 relative z-20">
                {/* Mobile Header (only visible on small screens) */}
                <div className="absolute top-8 left-6 md:hidden flex items-center gap-2">
                    <div className="w-8 h-8 bg-[#111118] border border-[#00FFB2]/30 rounded-lg flex items-center justify-center">
                        <Layout className="w-5 h-5 text-[#00FFB2]" />
                    </div>
                    <Link to="/" className="text-xl font-bold tracking-tight text-white">LearnPath<span className="text-[#00FFB2]">AI</span></Link>
                </div>

                <div className="w-full max-w-md mx-auto">
                    {/* Form Container */}
                    <div className="bg-[#111118]/80 backdrop-blur-xl rounded-2xl border border-[rgba(0,255,178,0.15)] shadow-[0_0_20px_rgba(0,0,0,0.5)] p-8 sm:p-10">
                        {children}
                    </div>
                </div>
            </div>

        </div>
    );
}
