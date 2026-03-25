/**
 * Shared API client for ScopeSentinel frontend.
 * Injects auth headers and base URL consistently across all fetch calls.
 */
const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const AUDIT_API_BASE = process.env.NEXT_PUBLIC_AUDIT_URL || 'http://localhost:8003'
const METERING_API_BASE = process.env.NEXT_PUBLIC_METERING_URL || 'http://localhost:8004'
const ADAPTER_SERVICE_BASE = process.env.NEXT_PUBLIC_ADAPTER_URL || 'http://localhost:8005'

const API_KEY = process.env.NEXT_PUBLIC_API_KEY || 'dev-admin-api-key-1'

function getBaseUrlForPath(path: string): string {
    if (path.startsWith('/audit')) return AUDIT_API_BASE;
    if (path.startsWith('/metering')) return METERING_API_BASE;
    if (path.startsWith('/api/connections/oauth') || path.startsWith('/api/tools')) return ADAPTER_SERVICE_BASE;
    return API_BASE;
}

export async function apiFetch(path: string, options: RequestInit = {}): Promise<Response> {
    const baseUrl = getBaseUrlForPath(path);
    
    // Extract orgId from custom header if present, or just pass it through
    const headers: Record<string, string> = {
        'Content-Type': 'application/json',
        'X-Api-Key': API_KEY,
        ...Object.fromEntries(Object.entries(options.headers || {}) as [string, string][]),
    };

    return fetch(`${baseUrl}${path}`, {
        ...options,
        headers,
    })
}

export async function apiGet<T>(path: string, options: RequestInit = {}): Promise<T> {
    const res = await apiFetch(path, options)
    if (!res.ok) throw new Error(`GET ${path} failed: ${res.status}`)
    return res.json()
}

export async function apiPost<T>(path: string, body: unknown, options: RequestInit = {}): Promise<T> {
    const res = await apiFetch(path, {
        method: 'POST',
        body: JSON.stringify(body),
        ...options,
    })
    if (!res.ok) throw new Error(`POST ${path} failed: ${res.status}`)
    return res.json()
}

export async function apiPatch<T>(path: string, body: unknown, options: RequestInit = {}): Promise<T> {
    const res = await apiFetch(path, {
        method: 'PATCH',
        body: JSON.stringify(body),
        ...options,
    })
    if (!res.ok) throw new Error(`PATCH ${path} failed: ${res.status}`)
    return res.json()
}

export async function apiDelete(path: string, options: RequestInit = {}): Promise<void> {
    const res = await apiFetch(path, { method: 'DELETE', ...options })
    if (!res.ok && res.status !== 204) throw new Error(`DELETE ${path} failed: ${res.status}`)
}
