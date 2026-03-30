import { Skeleton } from "../ui/skeleton";

/**
 * Mirrors the CourseDetailPage layout:
 *  course-detail-content, breadcrumb, title, status banner,
 *  skill metrics row, and resources list.
 */
export default function CourseDetailSkeleton() {
  return (
    <div
      className="course-detail-content space-y-10"
      style={{
        position: "relative",
        zIndex: 1,
        maxWidth: "1000px",
        margin: "0 auto",
        padding: "3rem 1.5rem",
      }}
    >
      {/* Breadcrumb */}
      <Skeleton className="h-4 w-72" style={{ backgroundColor: "#1e1e2e" }} />

      {/* Page header */}
      <div>
        <Skeleton className="h-12 w-96 mb-3" style={{ backgroundColor: "#1e1e2e" }} />
        <Skeleton className="h-5 w-40" style={{ backgroundColor: "#1e1e2e" }} />
      </div>

      {/* Skill status banner */}
      <div
        className="rounded-xl p-6 flex flex-col sm:flex-row justify-between items-center gap-4"
        style={{
          backgroundColor: "var(--bg-card, #111118)",
          border: "1px solid var(--border, #1e1e2e)",
          borderLeft: "3px solid #1e1e2e",
        }}
      >
        <Skeleton className="h-6 w-64" style={{ backgroundColor: "#1e1e2e" }} />
        <Skeleton className="h-10 w-28 rounded-lg" style={{ backgroundColor: "#1e1e2e" }} />
      </div>

      {/* Skill metrics row */}
      <div className="flex gap-4">
        {["Mastery", "Confidence"].map((label) => (
          <div
            key={label}
            className="rounded-xl p-4 sm:p-5"
            style={{
              backgroundColor: "var(--bg-card, #111118)",
              border: "1px solid var(--border, #1e1e2e)",
              maxWidth: "200px",
              flex: 1,
            }}
          >
            <Skeleton className="h-3 w-16 mb-2" style={{ backgroundColor: "#1e1e2e" }} />
            <Skeleton className="h-9 w-20" style={{ backgroundColor: "#1e1e2e" }} />
          </div>
        ))}
      </div>

      {/* Resources section */}
      <div>
        <Skeleton className="h-7 w-48 mb-6 mt-10" style={{ backgroundColor: "#1e1e2e" }} />
        <div className="space-y-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div
              key={i}
              className="rounded-xl flex items-center justify-between p-4"
              style={{
                backgroundColor: "var(--bg-card, #111118)",
                border: "1px solid var(--border, #1e1e2e)",
              }}
            >
              <div className="flex items-center gap-4">
                <Skeleton className="w-5 h-5 rounded" style={{ backgroundColor: "#1e1e2e" }} />
                <div className="flex flex-col gap-1">
                  <Skeleton className="h-4 w-48" style={{ backgroundColor: "#1e1e2e" }} />
                  <Skeleton className="h-3 w-16" style={{ backgroundColor: "#1e1e2e" }} />
                </div>
              </div>
              <Skeleton className="h-6 w-24 rounded-full hidden sm:block" style={{ backgroundColor: "#1e1e2e" }} />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
