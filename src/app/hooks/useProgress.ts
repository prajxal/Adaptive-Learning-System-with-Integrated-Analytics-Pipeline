import { useState, useEffect } from 'react';
import BACKEND_URL, { getClerkToken } from "../../services/api";

/**
 * Progress structure:
 * {
 *   "progress": {
 *     [userId: string]: {
 *       [courseId: string]: {
 *         [resourceId: string]: "completed" | "in_progress"
 *       }
 *     }
 *   },
 *   "lastAccessed": {
 *     [userId: string]: {
 *       roadmapId: string | null;
 *       courseId: string | null;
 *       resourceId: string | null;
 *       courseTitle?: string;
 *       resourceTitle?: string;
 *       timestamp: number;
 *     }
 *   }
 * }
 */

const STORAGE_KEY = 'learnpath_progress_engine';

export function useProgress() {
    // Need a simple way to get user ID. Assuming token parsing or from context.
    // For local MVP without complex JWT decode, we can hash the token or assume a simple userId fetch.
    // However, since we fetch skills via userId from backend in other places, 
    // we ideally need the userId. Let's provide a robust fallback.
    const [userId, setUserId] = useState<string>("default_user");

    // We can fetch the real user profile to get the ID, or decode JWT.
    useEffect(() => {
        getClerkToken().then(tokenStr => {
            const headers: Record<string, string> = { "Content-Type": "application/json" };
            if (tokenStr) headers["Authorization"] = `Bearer ${tokenStr}`;

            if (tokenStr) {
                fetch(`${BACKEND_URL}/auth/me`, { headers })
                    .then(res => res.json())
                    .then(data => {
                        if (data && data.id) {
                            setUserId(String(data.id));
                        }
                    })
                    .catch(err => console.error("Could not fetch user ID for progress tracking", err));
            }
        });
    }, []);

    const getRawState = () => {
        const raw = localStorage.getItem(STORAGE_KEY);
        if (raw) {
            try {
                return JSON.parse(raw);
            } catch (e) {
                console.error("Failed to parse progress state", e);
            }
        }
        return { progress: {}, lastAccessed: {} };
    };

    const saveRawState = (state: any) => {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
        // Dispatch a custom event so other components using this hook can re-render
        window.dispatchEvent(new Event('progress_updated'));
    };

    const markResourceComplete = (courseId: string, resourceId: string, roadmapId?: string, courseTitle?: string, resourceTitle?: string) => {
        const state = getRawState();
        if (!state.progress[userId]) state.progress[userId] = {};
        if (!state.progress[userId][courseId]) state.progress[userId][courseId] = {};

        state.progress[userId][courseId][resourceId] = "completed";

        // Update last accessed
        if (!state.lastAccessed[userId]) state.lastAccessed[userId] = {};
        state.lastAccessed[userId] = {
            roadmapId: roadmapId || state.lastAccessed[userId].roadmapId,
            courseId,
            resourceId,
            courseTitle: courseTitle || state.lastAccessed[userId].courseTitle,
            resourceTitle: resourceTitle || state.lastAccessed[userId].resourceTitle,
            timestamp: Date.now()
        };

        saveRawState(state);
    };

    const markResourceInProgress = (courseId: string, resourceId: string, roadmapId?: string, courseTitle?: string, resourceTitle?: string) => {
        const state = getRawState();
        if (!state.progress[userId]) state.progress[userId] = {};
        if (!state.progress[userId][courseId]) state.progress[userId][courseId] = {};

        // Only mark in progress if it's not already completed
        if (state.progress[userId][courseId][resourceId] !== "completed") {
            state.progress[userId][courseId][resourceId] = "in_progress";
        }

        // Update last accessed priority
        if (!state.lastAccessed[userId]) state.lastAccessed[userId] = {};
        state.lastAccessed[userId] = {
            roadmapId: Math.random() > 0 ? roadmapId : roadmapId, // Ensure it registers if passed
            courseId,
            resourceId,
            courseTitle: courseTitle || state.lastAccessed[userId].courseTitle,
            resourceTitle: resourceTitle || state.lastAccessed[userId].resourceTitle,
            timestamp: Date.now()
        };

        if (roadmapId) state.lastAccessed[userId].roadmapId = roadmapId;

        saveRawState(state);
    };

    const getResourceProgress = (courseId: string, resourceId: string): "completed" | "in_progress" | "not_started" => {
        const state = getRawState();
        if (state.progress[userId] && state.progress[userId][courseId] && state.progress[userId][courseId][resourceId]) {
            return state.progress[userId][courseId][resourceId];
        }
        return "not_started";
    };

    const getCourseProgress = (courseId: string, totalResources: number) => {
        const state = getRawState();
        const courseData = state.progress[userId]?.[courseId] || {};
        const completedCount = Object.values(courseData).filter(status => status === "completed").length;
        const inProgressCount = Object.values(courseData).filter(status => status === "in_progress").length;

        const percentage = totalResources > 0 ? Math.round((completedCount / totalResources) * 100) : 0;

        return {
            completedCount,
            inProgressCount,
            totalResources,
            percentage,
            isCompleted: totalResources > 0 && completedCount >= totalResources,
            isInProgress: completedCount > 0 || inProgressCount > 0
        };
    };

    const getRoadmapProgress = (roadmapId: string, coursesInRoadmap: { id: string, total_resources: number }[]) => {
        let totalResources = 0;
        let totalCompleted = 0;

        coursesInRoadmap.forEach(course => {
            totalResources += course.total_resources;
            const cProg = getCourseProgress(String(course.id), course.total_resources);
            totalCompleted += cProg.completedCount;
        });

        const percentage = totalResources > 0 ? Math.round((totalCompleted / totalResources) * 100) : 0;

        // Also figure out how many courses are 100% complete
        const coursesCompleted = coursesInRoadmap.filter(c => getCourseProgress(String(c.id), c.total_resources).isCompleted).length;

        return {
            totalResources,
            completedResources: totalCompleted,
            coursesCompleted,
            totalCourses: coursesInRoadmap.length,
            percentage
        };
    };

    const getLastAccessed = () => {
        const state = getRawState();
        return state.lastAccessed[userId] || null;
    };

    return {
        userId,
        markResourceComplete,
        markResourceInProgress,
        getResourceProgress,
        getCourseProgress,
        getRoadmapProgress,
        getLastAccessed
    };
}
