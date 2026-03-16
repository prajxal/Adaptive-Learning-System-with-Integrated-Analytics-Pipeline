const BASE_URL =
    (import.meta.env.VITE_BACKEND_URL || "http://localhost:8000")
        .replace(/\/+$/, "");

export const apiFetch = (path: string, options?: RequestInit) => {
    return fetch(`${BASE_URL}${path}`, options);
};

let getClerkTokenFn: (() => Promise<string | null>) | null = null;

export function setClerkTokenFn(fn: () => Promise<string | null>) {
    getClerkTokenFn = fn;
}

export const getClerkToken = async () => {
    return getClerkTokenFn ? await getClerkTokenFn() : null;
};

export async function fetchWithAuth(url: string, options: RequestInit = {}) {
    const token = await getClerkToken();
    return fetch(url, {
        ...options,
        headers: {
            ...(options.headers || {}),
            ...(token ? { Authorization: `Bearer ${token}` } : {})
        }
    });
}

export default BASE_URL;