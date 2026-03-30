import { Skeleton } from "../ui/skeleton";

/**
 * Mirrors the RoadmapDetailPage layout:
 *  - Left column: breadcrumb, title, 2-column course card grid
 *  - Right column: recommendation sidebar (hidden on mobile)
 */
export default function RoadmapDetailSkeleton() {
  return (
    <div className="flex h-full min-h-0 w-full overflow-hidden relative z-10 px-4 sm:px-6 lg:px-8 py-8 max-w-[1400px] mx-auto">
      {/* Left — course grid */}
      <div className="flex-1 overflow-auto pr-0 lg:pr-8 space-y-10">
        {/* Breadcrumb */}
        <Skeleton className="h-4 w-64" style={{ backgroundColor: "#1e1e2e" }} />

        {/* Page title */}
        <div>
          <Skeleton className="h-12 w-72 mb-3" style={{ backgroundColor: "#1e1e2e" }} />
          <Skeleton className="h-5 w-40" style={{ backgroundColor: "#1e1e2e" }} />
        </div>

        {/* Course cards — 2-column grid, 8 cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <div
              key={i}
              className="rounded-xl p-6 flex flex-col"
              style={{
                backgroundColor: "var(--bg-card, #111118)",
                border: "1px solid var(--border, #1e1e2e)",
                minHeight: "160px",
              }}
            >
              {/* Header row */}
              <div className="flex justify-between items-start mb-4">
                <Skeleton className="h-6 w-40" style={{ backgroundColor: "#1e1e2e" }} />
                <Skeleton className="h-6 w-20 rounded-full" style={{ backgroundColor: "#1e1e2e" }} />
              </div>

              {/* Difficulty */}
              <Skeleton className="h-4 w-32 mb-6" style={{ backgroundColor: "#1e1e2e" }} />

              {/* Action button placeholder */}
              <div className="mt-auto">
                <Skeleton className="h-9 w-full rounded-lg" style={{ backgroundColor: "#1e1e2e" }} />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Right — recommendation sidebar */}
      <div className="hidden lg:block w-80 shrink-0 h-full border-l border-white/10 pl-8">
        <Skeleton className="h-6 w-36 mb-6" style={{ backgroundColor: "#1e1e2e" }} />
        <div className="space-y-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <div
              key={i}
              className="rounded-xl p-4"
              style={{
                backgroundColor: "var(--bg-card, #111118)",
                border: "1px solid var(--border, #1e1e2e)",
              }}
            >
              <Skeleton className="h-5 w-full mb-2" style={{ backgroundColor: "#1e1e2e" }} />
              <Skeleton className="h-4 w-3/4" style={{ backgroundColor: "#1e1e2e" }} />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
