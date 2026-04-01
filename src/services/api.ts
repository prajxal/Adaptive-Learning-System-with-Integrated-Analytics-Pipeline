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

// Retry on transient server errors (Render cold starts / Supabase pooler blips)
const RETRY_ON_STATUS = new Set([502, 503, 504]);
const MAX_RETRIES = 3;
const RETRY_BASE_MS = 600;

export async function fetchWithAuth(url: string, options: RequestInit = {}) {
    const token = await getClerkToken();
    const reqOptions: RequestInit = {
        ...options,
        headers: {
            ...(options.headers || {}),
            ...(token ? { Authorization: `Bearer ${token}` } : {})
        }
    };

    let lastError: unknown;
    for (let attempt = 0; attempt < MAX_RETRIES; attempt++) {
        if (attempt > 0) {
            await new Promise(r => setTimeout(r, RETRY_BASE_MS * Math.pow(2, attempt - 1)));
        }
        try {
            const res = await fetch(url, reqOptions);
            if (!RETRY_ON_STATUS.has(res.status)) return res;
            lastError = new Error(`HTTP ${res.status}`);
        } catch (err) {
            lastError = err;
            if (attempt === MAX_RETRIES - 1) throw err;
        }
    }
    throw lastError;
}

export default BASE_URL;