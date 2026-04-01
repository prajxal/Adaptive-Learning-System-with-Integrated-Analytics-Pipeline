import React from "react";
import { useNavigate } from "react-router-dom";
import { Github, FileText, Map, X, ArrowRight } from "lucide-react";

interface OnboardingWizardProps {
  githubConnected: boolean;
  hasSkills: boolean;
  onDismiss: () => void;
}

export function OnboardingWizard({ githubConnected, hasSkills, onDismiss }: OnboardingWizardProps) {
  const navigate = useNavigate();

  const steps = [
    {
      icon: githubConnected ? Github : FileText,
      label: "Import your skills",
      description: githubConnected
        ? "GitHub connected — your skills are being analysed."
        : hasSkills
        ? "Skills detected from your resume."
        : "Connect GitHub or upload your resume so we can personalise your roadmap.",
      done: githubConnected || hasSkills,
      cta: "Go to Profile",
      path: "/profile",
    },
    {
      icon: Map,
      label: "Pick a learning path",
      description: "Browse our curated roadmaps and choose one to start with.",
      done: false,
      cta: "Browse Roadmaps",
      path: "/roadmaps",
    },
  ];

  const allDone = steps.every((s) => s.done);

  return (
    <div
      className="rounded-2xl p-6 sm:p-8 mb-10 relative overflow-hidden"
      style={{
        background: "linear-gradient(135deg, #111118 0%, #16161f 100%)",
        border: "1px solid rgba(99,102,241,0.25)",
        boxShadow: "0 0 40px rgba(99,102,241,0.08)",
      }}
    >
      {/* Subtle accent glow */}
      <div
        className="absolute top-0 right-0 w-64 h-64 rounded-full pointer-events-none"
        style={{
          background: "radial-gradient(circle, rgba(99,102,241,0.08) 0%, transparent 70%)",
          transform: "translate(30%, -30%)",
        }}
      />

      {/* Header */}
      <div className="relative z-10 flex items-start justify-between mb-6">
        <div>
          <div
            className="text-[11px] font-bold tracking-[0.1em] uppercase mb-2"
            style={{ color: "#6366f1" }}
          >
            Getting Started
          </div>
          <h2
            className="text-2xl font-bold tracking-tight"
            style={{
              fontFamily: "'Sora', sans-serif",
              color: "#f1f5f9",
            }}
          >
            Welcome to LearnPath AI
          </h2>
          <p className="text-sm mt-1" style={{ color: "#64748b" }}>
            Complete these steps to get a personalised curriculum.
          </p>
        </div>
        <button
          onClick={onDismiss}
          className="shrink-0 p-1.5 rounded-md transition-colors ml-4"
          style={{ color: "#64748b" }}
          onMouseOver={(e) => (e.currentTarget.style.color = "#f1f5f9")}
          onMouseOut={(e) => (e.currentTarget.style.color = "#64748b")}
          title="Dismiss"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Steps */}
      <div className="relative z-10 flex flex-col sm:flex-row gap-4 mb-6">
        {steps.map((step, idx) => {
          const Icon = step.icon;
          return (
            <div
              key={idx}
              className="flex-1 rounded-xl p-4"
              style={{
                background: step.done
                  ? "rgba(16,185,129,0.06)"
                  : "rgba(255,255,255,0.03)",
                border: step.done
                  ? "1px solid rgba(16,185,129,0.2)"
                  : "1px solid rgba(255,255,255,0.07)",
              }}
            >
              <div className="flex items-center gap-2.5 mb-2">
                <div
                  className="w-7 h-7 rounded-full flex items-center justify-center shrink-0"
                  style={{
                    background: step.done
                      ? "rgba(16,185,129,0.15)"
                      : "rgba(99,102,241,0.12)",
                    border: step.done
                      ? "1px solid rgba(16,185,129,0.3)"
                      : "1px solid rgba(99,102,241,0.25)",
                  }}
                >
                  {step.done ? (
                    <svg
                      className="w-3.5 h-3.5"
                      viewBox="0 0 16 16"
                      fill="none"
                      style={{ color: "#10b981" }}
                    >
                      <path
                        d="M3 8l3.5 3.5L13 4.5"
                        stroke="currentColor"
                        strokeWidth="2"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      />
                    </svg>
                  ) : (
                    <Icon className="w-3.5 h-3.5" style={{ color: "#6366f1" }} />
                  )}
                </div>
                <span
                  className="text-sm font-semibold"
                  style={{ color: step.done ? "#10b981" : "#f1f5f9" }}
                >
                  {step.label}
                </span>
              </div>
              <p className="text-xs mb-3 leading-relaxed" style={{ color: "#64748b" }}>
                {step.description}
              </p>
              {!step.done && (
                <button
                  onClick={() => navigate(step.path)}
                  className="inline-flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-lg transition-all"
                  style={{
                    background: "rgba(99,102,241,0.12)",
                    color: "#818cf8",
                    border: "1px solid rgba(99,102,241,0.2)",
                  }}
                  onMouseOver={(e) => {
                    e.currentTarget.style.background = "rgba(99,102,241,0.2)";
                    e.currentTarget.style.borderColor = "rgba(99,102,241,0.4)";
                  }}
                  onMouseOut={(e) => {
                    e.currentTarget.style.background = "rgba(99,102,241,0.12)";
                    e.currentTarget.style.borderColor = "rgba(99,102,241,0.2)";
                  }}
                >
                  {step.cta}
                  <ArrowRight className="w-3 h-3" />
                </button>
              )}
            </div>
          );
        })}
      </div>

      {/* Footer CTA */}
      <div className="relative z-10 flex items-center justify-between">
        <p className="text-xs" style={{ color: "#64748b" }}>
          {allDone
            ? "You're all set — head to Learning Paths to begin."
            : "You can always come back to complete these steps later."}
        </p>
        <button
          onClick={onDismiss}
          className="text-xs font-medium transition-colors"
          style={{ color: "#64748b" }}
          onMouseOver={(e) => (e.currentTarget.style.color = "#f1f5f9")}
          onMouseOut={(e) => (e.currentTarget.style.color = "#64748b")}
        >
          Skip for now
        </button>
      </div>
    </div>
  );
}
