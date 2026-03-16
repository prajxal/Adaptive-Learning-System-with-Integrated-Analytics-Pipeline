const BASE_URL =
    (import.meta.env.VITE_BACKEND_URL || "http://localhost:8000")
        .replace(/\/+$/, "");

export const apiFetch = (path: string, options?: RequestInit) => {
    return fetch(`${BASE_URL}${path}`, options);
};

let clerkToken: string | null = null;

export function setClerkToken(token: string | null) {
    clerkToken = token;
}

export const getClerkToken = async () => clerkToken;

export async function fetchWithAuth(url: string, options: RequestInit = {}) {
    return fetch(url, {
        ...options,
        headers: {
            ...(options.headers || {}),
            ...(clerkToken ? { Authorization: `Bearer ${clerkToken}` } : {})
        }
    });
}

export default BASE_URL;