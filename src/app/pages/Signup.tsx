import React, { FormEvent, useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { signup, getToken } from "../../services/auth";
import { AuthLayout } from "../components/auth/AuthLayout";
import { usePostHog } from "@posthog/react";

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || "http://localhost:8000";

const GoogleIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
    <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4" />
    <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
    <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05" />
    <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" />
  </svg>
);

export function Signup() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [isGoogleLoading, setIsGoogleLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();
  const posthog = usePostHog();

  useEffect(() => {
    const token = getToken() || localStorage.getItem("access_token");
    if (token) {
      console.log("[Signup] Redirecting to /dashboard because token exists");
      navigate("/dashboard");
    }
  }, [navigate]);

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const data = await signup(email, password);
      posthog?.identify(data.user_id, { email });
      posthog?.capture('user_signed_up', { email });
      navigate("/dashboard");
    } catch (err: any) {
      setError(err.message || "Registration failed. Please try again.");
      posthog?.captureException(err);
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleAuth = () => {
    setIsGoogleLoading(true);
    window.location.href = `${BACKEND_URL}/auth/google`;
  };

  return (
    <AuthLayout>
      <div className="text-center mb-8">
        <h1 className="text-3xl font-bold tracking-tight text-white">Create your account</h1>
        <p className="text-sm text-gray-400 mt-2">Start your personalized engineering learning path</p>
      </div>

      <form className="space-y-5" onSubmit={handleSubmit}>
        <div>
          <label htmlFor="signup-email" className="block text-sm font-medium text-gray-300 mb-1.5">
            Email address
          </label>
          <input
            id="signup-email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
            className="w-full px-4 py-3 rounded-lg bg-[#111118] border border-white/10 text-white focus:ring-1 focus:ring-[#00FFB2] focus:border-[#00FFB2] outline-none transition shadow-sm"
            required
          />
        </div>

        <div>
          <label htmlFor="signup-password" className="block text-sm font-medium text-gray-300 mb-1.5">
            Password
          </label>
          <input
            id="signup-password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Create a strong password"
            className="w-full px-4 py-3 rounded-lg bg-[#111118] border border-white/10 text-white focus:ring-1 focus:ring-[#00FFB2] focus:border-[#00FFB2] outline-none transition shadow-sm"
            required
            minLength={6}
          />
        </div>

        {error && (
          <div className="p-3 rounded-md bg-red-900/30 border border-red-500/50 text-sm text-red-400 flex items-start">
            <span>{error}</span>
          </div>
        )}

        <button
          type="submit"
          disabled={loading || isGoogleLoading}
          className="w-full py-3 rounded-lg bg-transparent border border-[#00FFB2]/50 text-[#00FFB2] font-semibold hover:bg-[#00FFB2]/10 transition shadow-[0_0_10px_rgba(0,255,178,0.1)] hover:shadow-[0_0_15px_rgba(0,255,178,0.3)] disabled:opacity-50 flex justify-center items-center"
        >
          {loading ? (
            <span className="flex items-center gap-2">
              <svg className="animate-spin h-5 w-5 text-[#00FFB2]" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              Creating account...
            </span>
          ) : "Sign Up"}
        </button>
      </form>

      <div className="flex items-center my-6">
        <div className="flex-grow h-px bg-white/10"></div>
        <span className="px-4 text-xs uppercase text-gray-500 font-medium tracking-wider">
          &mdash; or &mdash;
        </span>
        <div className="flex-grow h-px bg-white/10"></div>
      </div>

      <button
        onClick={handleGoogleAuth}
        disabled={loading || isGoogleLoading}
        className="w-full flex items-center justify-center gap-3 px-4 py-3 rounded-md border border-white/20 hover:border-[#00FFB2] bg-[#111118] text-white text-sm transition-all hover:shadow-[0_0_12px_rgba(0,255,178,0.2)] disabled:opacity-50"
      >
        {isGoogleLoading ? (
          <span className="flex items-center gap-2 text-gray-400">
            <svg className="animate-spin h-4 w-4 text-gray-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            Connecting...
          </span>
        ) : (
          <>
            <GoogleIcon />
            Continue with Google
          </>
        )}
      </button>

      <div className="mt-8 text-center text-sm text-gray-500">
        Already have an account?{" "}
        <Link to="/signin" className="font-semibold text-[#00FFB2] hover:text-[#00FFB2]/80 transition-colors">
          Sign in
        </Link>
      </div>
    </AuthLayout>
  );
}
