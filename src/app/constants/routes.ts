export const ROUTES = {
    DASHBOARD: "/dashboard",
    ROADMAPS: "/roadmaps",
    ROADMAP: (id: string) => `/roadmap/${id}`,
    COURSE: (id: string) => `/course/${id}`,
    RESOURCE: (courseId: string, resourceId: string) => `/course/${courseId}/resource/${resourceId}`,
    QUIZ: (courseId: string) => `/course/${courseId}/quiz`,
};
