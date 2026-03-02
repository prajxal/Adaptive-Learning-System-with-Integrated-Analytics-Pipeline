const BASE_URL =
    (import.meta.env.VITE_BACKEND_URL || "http://localhost:8000")
        .replace(/\/+$/, "");

export const apiFetch = (path: string, options?: RequestInit) => {
    return fetch(`${BASE_URL}${path}`, options);
};

export default BASE_URL;