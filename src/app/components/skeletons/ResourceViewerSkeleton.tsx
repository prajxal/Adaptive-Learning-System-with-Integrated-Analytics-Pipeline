import { Skeleton } from "../ui/skeleton";

/**
 * Mirrors the ResourceViewerPage layout:
 *  - Sidebar (left): back button + resource list sections
 *  - Main viewer (right): header + content area
 */
export default function ResourceViewerSkeleton() {
  return (
    <div
      className="flex h-[calc(100vh-8rem)] -mt-4 -mx-4 overflow-hidden border rounded-xl"
      style={{
        borderColor: "#1e1e2e",
        backgroundColor: "#0a0a0f",
      }}
    >
      {/* Sidebar */}
      <div
        className="w-1/4 min-w-[280px] max-w-[350px] border-r overflow-y-auto"
        style={{ backgroundColor: "#111118", borderColor: "#1e1e2e" }}
      >
        {/* Back button row */}
        <div
          className="p-4 border-b sticky top-0 z-10 hidden sm:flex items-center gap-2"
          style={{ backgroundColor: "#111118", borderColor: "#1e1e2e" }}
        >
          <Skeleton className="h-7 w-16 rounded" style={{ backgroundColor: "#1e1e2e" }} />
          <Skeleton className="h-4 w-32" style={{ backgroundColor: "#1e1e2e" }} />
        </div>

        <div className="p-4">
          {/* Breadcrumb */}
          <Skeleton className="h-4 w-48 mb-4" style={{ backgroundColor: "#1e1e2e" }} />

          {/* Sidebar sections */}
          {["Videos", "Documentation", "Articles"].map((section) => (
            <div key={section} className="mb-6">
              <Skeleton className="h-3 w-24 mb-3" style={{ backgroundColor: "#1e1e2e" }} />
              <div className="space-y-1">
                {Array.from({ length: 2 }).map((_, i) => (
                  <Skeleton
                    key={i}
                    className="h-12 w-full rounded-lg"
                    style={{ backgroundColor: "#1e1e2e" }}
                  />
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Main viewer */}
      <div
        className="flex-1 flex flex-col overflow-hidden"
        style={{ backgroundColor: "#0a0a0f" }}
      >
        {/* Header */}
        <div
          className="p-4 border-b"
          style={{ backgroundColor: "#111118", borderColor: "#1e1e2e" }}
        >
          <div className="flex items-start justify-between mb-1">
            <Skeleton className="h-7 w-72 pr-4" style={{ backgroundColor: "#1e1e2e" }} />
            <div className="flex items-center gap-2 shrink-0">
              <Skeleton className="h-7 w-36 rounded-full" style={{ backgroundColor: "#1e1e2e" }} />
              <Skeleton className="h-7 w-28 rounded" style={{ backgroundColor: "#1e1e2e" }} />
            </div>
          </div>
          <div className="flex gap-3 items-center mt-2">
            <Skeleton className="h-4 w-20" style={{ backgroundColor: "#1e1e2e" }} />
            <Skeleton className="h-4 w-16" style={{ backgroundColor: "#1e1e2e" }} />
          </div>
        </div>

        {/* Content area — video aspect ratio placeholder */}
        <div className="flex-1 p-6 flex flex-col items-center justify-start bg-[#0a0a0f]">
          <Skeleton
            className="relative w-full rounded-xl mt-4 max-w-5xl mx-auto"
            style={{
              backgroundColor: "#111118",
              border: "1px solid #1e1e2e",
              aspectRatio: "16/9",
            }}
          />
        </div>
      </div>
    </div>
  );
}
