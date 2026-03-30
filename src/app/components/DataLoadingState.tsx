import { useEffect, useState } from "react";

interface DataLoadingStateProps {
  children: React.ReactNode;
}

/**
 * Wraps skeleton content and shows staged status messages during cold-start delays.
 *
 * Timing:
 *  < 3s  — skeleton only, no message
 *  5–14s — "Waking up our AI servers..."
 *  ≥ 15s — "Preparing your learning paths..."
 */
export default function DataLoadingState({ children }: DataLoadingStateProps) {
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    const id = setInterval(() => {
      setElapsed((prev) => prev + 1);
    }, 1000);
    return () => clearInterval(id);
  }, []);

  const message =
    elapsed >= 15
      ? "Preparing your learning paths..."
      : elapsed >= 5
      ? "Waking up our AI servers..."
      : null;

  return (
    <div>
      {children}
      {message && (
        <p
          className="animate-fade-in mt-6 text-center text-sm"
          style={{ color: "var(--text-muted, #64748b)" }}
        >
          {message}
        </p>
      )}
    </div>
  );
}
