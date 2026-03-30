import { Skeleton } from "../ui/skeleton";

/**
 * Mirrors the RoadmapCatalogPage grid layout.
 * Uses the same CSS custom properties and roadmap-grid class so the
 * skeleton occupies the identical space as the real content.
 */
export default function RoadmapCatalogSkeleton() {
  return (
    <>
      {/* Breadcrumb placeholder */}
      <Skeleton className="h-4 w-48 mb-12" style={{ backgroundColor: "#1e1e2e" }} />

      {/* Page header */}
      <div className="mb-12">
        <Skeleton className="h-12 w-80 mb-4" style={{ backgroundColor: "#1e1e2e" }} />
        <Skeleton className="h-6 w-56" style={{ backgroundColor: "#1e1e2e" }} />
        <hr className="mt-8 border-t" style={{ borderColor: "var(--border, #1e1e2e)" }} />
      </div>

      {/* Card grid — 6 placeholder cards */}
      <div className="roadmap-grid">
        {Array.from({ length: 6 }).map((_, i) => (
          <div
            key={i}
            className="rounded-xl p-6 flex flex-col"
            style={{
              backgroundColor: "var(--bg-card, #111118)",
              border: "1px solid var(--border, #1e1e2e)",
              minHeight: "180px",
            }}
          >
            {/* Title row */}
            <div className="flex items-center gap-2.5 mb-2">
              <Skeleton className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: "#1e1e2e" }} />
              <Skeleton className="h-5 w-36" style={{ backgroundColor: "#1e1e2e" }} />
            </div>

            {/* Topic count */}
            <Skeleton className="h-3.5 w-20 mb-8" style={{ backgroundColor: "#1e1e2e" }} />

            {/* Bottom row */}
            <div className="mt-auto flex flex-col gap-3">
              <div className="flex items-center justify-between">
                <Skeleton className="h-6 w-24 rounded-full" style={{ backgroundColor: "#1e1e2e" }} />
                <Skeleton className="h-4 w-12" style={{ backgroundColor: "#1e1e2e" }} />
              </div>
              <Skeleton className="w-full h-[3px] rounded-full" style={{ backgroundColor: "#1e1e2e" }} />
            </div>
          </div>
        ))}
      </div>
    </>
  );
}
