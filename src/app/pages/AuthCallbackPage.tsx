import React, { useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { usePostHog } from '@posthog/react';

export default function AuthCallbackPage() {
    const navigate = useNavigate();
    const [searchParams] = useSearchParams();
    const posthog = usePostHog();

    useEffect(() => {
        const token = searchParams.get('token');
        if (token) {
            localStorage.setItem('access_token', token);
            posthog?.capture('google_login');
            navigate('/dashboard');
        } else {
            navigate('/signin');
        }
    }, [navigate, searchParams, posthog]);

    return (
        <div className="bg-[#0A0A0F] h-screen flex flex-col items-center justify-center text-[#00FFB2] font-mono">
            <div className="pointer-events-none absolute inset-0 z-10 opacity-50" style={{
                backgroundImage: `repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0, 255, 178, 0.03) 2px, rgba(0, 255, 178, 0.03) 4px)`
            }}></div>
            <div className="flex flex-col items-center gap-4 z-20">
                <svg className="animate-spin h-10 w-10 text-[#00FFB2]" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                <div className="text-xl tracking-wider animate-pulse">Authenticating...</div>
            </div>
        </div>
    );
}
