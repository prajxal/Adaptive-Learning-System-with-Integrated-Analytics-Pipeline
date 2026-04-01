import { Skeleton } from "../ui/skeleton";

/**
 * Mirrors the QuizPage question card layout for the Gemini generation wait.
 */
export default function QuizSkeleton() {
  return (
    <div
      style={{
        maxWidth: "768px",
        margin: "0 auto",
        padding: "2rem 1rem",
        paddingBottom: "5rem",
      }}
    >
      {/* Breadcrumb */}
      <Skeleton className="h-4 w-72 mb-8" style={{ backgroundColor: "#1e1e2e" }} />

      {/* Title + question counter */}
      <div className="flex items-end justify-between mb-2">
        <Skeleton className="h-8 w-64" style={{ backgroundColor: "#1e1e2e" }} />
        <Skeleton className="h-4 w-24" style={{ backgroundColor: "#1e1e2e" }} />
      </div>

      {/* Progress bar */}
      <div className="w-full h-[2px] rounded-full mb-10" style={{ backgroundColor: "#1e1e2e" }} />

      {/* Question card */}
      <div
        className="rounded-xl p-10"
        style={{ backgroundColor: "#111118", border: "1px solid #1e1e2e" }}
      >
        {/* Question text */}
        <Skeleton className="h-8 w-full mb-3" style={{ backgroundColor: "#1e1e2e" }} />
        <Skeleton className="h-8 w-3/4 mb-10" style={{ backgroundColor: "#1e1e2e" }} />

        {/* Options */}
        <div className="space-y-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <div
              key={i}
              className="rounded-lg p-5"
              style={{ backgroundColor: "#16161f", border: "1px solid #1e1e2e" }}
            >
              <Skeleton
                className="h-5"
                style={{ backgroundColor: "#1e1e2e", width: `${60 + i * 8}%` }}
              />
            </div>
          ))}
        </div>

        {/* Footer */}
        <div
          className="mt-12 flex justify-between items-center border-t pt-6"
          style={{ borderColor: "#1e1e2e" }}
        >
          <Skeleton className="h-4 w-24" style={{ backgroundColor: "#1e1e2e" }} />
          <Skeleton className="h-10 w-32 rounded-lg" style={{ backgroundColor: "#1e1e2e" }} />
        </div>
      </div>
    </div>
  );
}
