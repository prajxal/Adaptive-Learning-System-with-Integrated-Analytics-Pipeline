import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useProgress } from "../hooks/useProgress";
import BACKEND_URL, { getClerkToken } from "../../services/api";
import { usePostHog } from "@posthog/react";
import AppBreadcrumb from "../components/AppBreadcrumb";

type Resource = {
    id: string;
    title: string;
    url: string;
    platform: string;
    duration_seconds: number;
    difficulty_level: number;
    quality_score: number;
    resource_type: string;
};

function convertToEmbedUrl(url: string) {
    if (!url) return url;

    if (url.includes("youtube.com/watch?v=")) {
        const videoId = url.split("watch?v=")[1].split("&")[0];
        return `https://www.youtube.com/embed/${videoId}`;
    }

    if (url.includes("youtu.be/")) {
        const videoId = url.split("youtu.be/")[1].split("?")[0];
        return `https://www.youtube.com/embed/${videoId}`;
    }

    return url;
}

export default function ResourceViewerPage() {
    const { courseId, resourceId } = useParams();
    const navigate = useNavigate();
    const posthog = usePostHog();

    const [resources, setResources] = useState<{ primary: Resource | null, additional: Resource[] }>({ primary: null, additional: [] });
    const [activeResource, setActiveResource] = useState<Resource | null>(null);
    const [loading, setLoading] = useState(true);
    const [iframeLoading, setIframeLoading] = useState(true);

    // Progress Engine
    const { markResourceInProgress, markResourceComplete, getResourceProgress } = useProgress();

    useEffect(() => {
        if (!courseId) return;

        getClerkToken().then(tokenStr => {
            const headers: Record<string, string> = { "Content-Type": "application/json" };
            if (tokenStr) headers["Authorization"] = `Bearer ${tokenStr}`;

            setLoading(true);
            fetch(`${BACKEND_URL}/courses/${courseId}/resources`, { headers })
                .then((res) => res.json())
                .then((data) => {
                    setResources(data || { primary: null, additional: [] });
                    setLoading(false);
                })
                .catch((err) => {
                    console.error(err);
                    setLoading(false);
                });
        });
    }, [courseId]);

    useEffect(() => {
        setIframeLoading(true); // Reset iframe loading state

        if (courseId && resourceId && activeResource) {
            markResourceInProgress(courseId, resourceId, undefined, "Active Course Module", activeResource.title);
            posthog?.capture('resource_opened', {
                course_id: courseId,
                resource_id: resourceId,
                resource_title: activeResource.title,
                resource_type: activeResource.resource_type,
                platform: activeResource.platform,
            });
        }
    }, [resourceId, activeResource]);

    const allResources = (() => {
        const arr: Resource[] = [];
        if (resources.primary) arr.push(resources.primary);
        arr.push(...resources.additional);
        return arr;
    })();

    useEffect(() => {
        const arr: Resource[] = [];
        if (resources.primary) arr.push(resources.primary);
        if (resources.additional) arr.push(...resources.additional);

        if (arr.length === 0) {
            setActiveResource(null);
            return;
        }

        const found = arr.find(r => String(r.id) === String(resourceId));
        setActiveResource(found || arr[0]);
    }, [resourceId, resources]);

    if (loading) {
        return <div className="p-8 text-muted-foreground flex items-center justify-center">Loading viewer...</div>;
    }

    if (allResources.length === 0) {
        return <div className="p-8 text-center text-muted-foreground">No resources available for this topic.</div>;
    }

    if (!activeResource) {
        return <div className="p-8 text-center text-muted-foreground">Resource not found.</div>;
    }

    const renderSidebarSection = (type: string, title: string, icon: string) => {
        const items = allResources.filter(r =>
            type === 'article' ? (r.resource_type === 'article' || !r.resource_type) : r.resource_type === type
        );

        if (items.length === 0) return null;

        return (
            <div className="mb-6" key={type}>
                <h4 className="font-semibold mb-3 px-2 flex items-center gap-2 uppercase text-[11px] tracking-[0.08em] text-[#64748b]">
                    {icon} {title}
                </h4>
                <div className="space-y-1">
                    {items.map(res => {
                        const isActive = res.id === activeResource.id;
                        const status = getResourceProgress(courseId as string, res.id);

                        return (
                            <button
                                key={res.id}
                                onClick={() => navigate(`/course/${courseId}/resource/${res.id}`)}
                                className={`w-full text-left px-3 py-2.5 rounded-lg text-sm transition-colors border-l-[3px] flex items-start gap-2 ${isActive
                                    ? 'bg-[#16161f] border-[#6366f1] text-[#f1f5f9]'
                                    : 'text-[#64748b] bg-transparent border-transparent hover:bg-[#16161f] hover:text-[#f1f5f9]'
                                    }`}
                            >
                                <div className="mt-0.5 shrink-0 text-gray-500">
                                    {status === 'completed' && <span className="text-[#22c55e] text-base leading-none">✓</span>}
                                    {status === 'in_progress' && <span className="text-[#6366f1] text-[10px] leading-none">●</span>}
                                    {status === 'not_started' && <span className="text-gray-600 text-[10px] leading-none">○</span>}
                                </div>
                                <div className="flex-1">
                                    <div className="line-clamp-2">{res.title}</div>
                                    {res.platform && (
                                        <div className="text-[11px] mt-1 text-[#64748b]">
                                            {res.platform.toUpperCase()}
                                        </div>
                                    )}
                                </div>
                            </button>
                        )
                    })}
                </div>
            </div>
        );
    };

    return (
        <div className="flex h-[calc(100vh-8rem)] -mt-4 -mx-4 overflow-hidden border border-[#1e1e2e] rounded-xl bg-[#0a0a0f]">
            {/* Sidebar */}
            <div className="w-1/4 min-w-[280px] max-w-[350px] bg-[#111118] border-r border-[#1e1e2e] overflow-y-auto">
                <div className="p-4 border-b border-[#1e1e2e] bg-[#111118] sticky top-0 z-10 hidden sm:flex items-center gap-2">
                    <button
                        onClick={() => navigate(`/course/${courseId}`)}
                        className="text-[#f1f5f9] hover:bg-[#16161f] p-1 rounded"
                    >
                        ← Back
                    </button>
                    <span className="font-semibold text-sm truncate text-[#f1f5f9]">Course Resources</span>
                </div>

                <div className="p-4">
                    <div className="mb-4">
                        <AppBreadcrumb segments={[
                            { label: "Home", href: "/dashboard" },
                            { label: (courseId?.split(":")[0] ?? "").replace(/-/g, " ") || "Roadmap", href: `/roadmap/${courseId?.split(":")[0]}` },
                            { label: activeResource?.title ?? "Resource" },
                        ]} />
                    </div>
                    {renderSidebarSection('video', 'Videos', '🎥')}
                    {renderSidebarSection('documentation', 'Documentation', '📖')}
                    {renderSidebarSection('article', 'Articles', '📰')}
                    {renderSidebarSection('practice', 'Practice / Labs', '🧪')}
                </div>
            </div>

            {/* Main Viewer */}
            <div className="flex-1 flex flex-col overflow-hidden bg-[#0a0a0f]">
                <div className="p-4 border-b bg-[#111118] border-[#1e1e2e]">
                    <div className="flex items-start justify-between mb-1">
                        <h2 className="text-xl font-bold pr-4 text-[#f1f5f9]">{activeResource.title}</h2>
                        <div className="flex items-center gap-2 shrink-0">
                            {activeResource.resource_type === "video" ? (
                                <span className="inline-flex items-center px-2 py-1 rounded-full text-[11px] font-medium bg-[#16161f] text-[#64748b] border border-[#1e1e2e]">
                                    🟢 Embedded Video
                                </span>
                            ) : (
                                <span className="inline-flex items-center px-2 py-1 rounded-full text-[11px] font-medium bg-[#16161f] text-[#64748b] border border-[#1e1e2e]">
                                    🔗 Opens externally
                                </span>
                            )}

                            {getResourceProgress(courseId as string, activeResource.id) !== 'completed' ? (
                                <button
                                    onClick={() => {
                                        markResourceComplete(courseId as string, activeResource.id);
                                        posthog?.capture('resource_completed', {
                                            course_id: courseId,
                                            resource_id: activeResource.id,
                                            resource_title: activeResource.title,
                                            resource_type: activeResource.resource_type,
                                            platform: activeResource.platform,
                                        });
                                    }}
                                    className="ml-2 bg-[#6366f1] hover:bg-indigo-600 text-[#f1f5f9] text-xs font-medium py-1 px-3 rounded transition-colors"
                                >
                                    Mark Complete ✓
                                </button>
                            ) : (
                                <span className="ml-2 inline-flex items-center px-2 py-1 rounded-full text-[11px] font-medium bg-[#22c55e] text-[#f1f5f9]">
                                    ✓ Completed
                                </span>
                            )}
                        </div>
                    </div>
                    <div className="text-sm text-[#64748b] flex gap-3 items-center">
                        <span className="capitalize">{activeResource.platform}</span>
                        {activeResource.duration_seconds > 0 && (
                            <span>• {Math.floor(activeResource.duration_seconds / 60)} mins</span>
                        )}
                        <a
                            href={activeResource.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="ml-auto text-[#64748b] hover:text-[#f1f5f9] hover:underline flex items-center gap-1 transition-colors"
                        >
                            Open external <span className="text-xs">↗</span>
                        </a>
                    </div>
                </div>

                <div className="flex-1 p-6 overflow-y-auto w-full h-full flex flex-col relative bg-[#0a0a0f]">
                    {activeResource.resource_type === "video" ? (
                        <div key={activeResource.id} className="relative aspect-video w-full rounded-xl shadow-lg border border-[#1e1e2e] bg-[#111118] mt-4 max-w-5xl mx-auto overflow-hidden">
                            {iframeLoading && (
                                <div className="absolute inset-0 flex items-center justify-center bg-[#111118] animate-pulse">
                                    <div className="w-8 h-8 rounded-full border-4 border-[#6366f1] border-t-transparent animate-spin"></div>
                                </div>
                            )}
                            <iframe
                                key={activeResource.url}
                                src={convertToEmbedUrl(activeResource.url)}
                                className={`w-full h-full transition-opacity duration-300 ${iframeLoading ? 'opacity-0' : 'opacity-100'}`}
                                allowFullScreen
                                frameBorder="0"
                                onLoad={() => setIframeLoading(false)}
                                onError={() => setIframeLoading(false)}
                                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                            />
                        </div>
                    ) : (
                        <div key={activeResource.id} className="flex flex-col items-center justify-center flex-1 bg-[#111118] p-12 text-center h-full rounded-xl border border-[#1e1e2e]">
                            <div className="w-16 h-16 bg-[#16161f] rounded-full flex items-center justify-center mb-6 text-2xl shadow-sm border border-[#1e1e2e] text-[#6366f1]">
                                🔗
                            </div>
                            <h3 className="text-xl font-semibold mb-3 text-[#f1f5f9]">
                                {activeResource.title}
                            </h3>
                            <p className="text-[#64748b] mb-8 max-w-md">
                                This resource opens on an external site. Click below to open it in a new tab.
                            </p>
                            <a
                                href={activeResource.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="inline-flex items-center justify-center gap-2 bg-[#6366f1] hover:bg-indigo-600 text-[#f1f5f9] font-medium py-3 px-8 rounded-lg transition-all shadow-sm hover:shadow"
                            >
                                Open in new tab <span className="text-lg leading-none">↗</span>
                            </a>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
