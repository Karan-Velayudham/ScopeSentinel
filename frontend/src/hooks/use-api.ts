"use client"

import { useSession } from "next-auth/react"
import { apiGet, apiPost, apiPatch, apiPut, apiDelete, apiFetch } from "@/lib/api-client"

/**
 * Custom hook that provides org-aware API methods.
 * Automatically injects the X-ScopeSentinel-Org-ID header from the session.
 */
export function useApi() {
    const { data: session } = useSession()
    const orgId = session?.user?.org_id
    const token = (session as any)?.accessToken

    const withAuth = (options: RequestInit = {}) => {
        const headers: Record<string, string> = {
            ...(options.headers as Record<string, string> || {}),
        }

        if (orgId) {
            headers['X-ScopeSentinel-Org-ID'] = orgId
        }

        if (token) {
            headers['Authorization'] = `Bearer ${token}`
        }
        
        return {
            ...options,
            headers
        }
    }

    return {
        session,
        orgId,
        fetch: (path: string, options?: RequestInit) => 
            apiFetch(path, withAuth(options)),
        
        get: <T>(path: string, options?: RequestInit) => 
            apiGet<T>(path, withAuth(options)),
            
        post: <T>(path: string, body: unknown, options?: RequestInit) => 
            apiPost<T>(path, body, withAuth(options)),
            
        patch: <T>(path: string, body: unknown, options?: RequestInit) => 
            apiPatch<T>(path, body, withAuth(options)),
            
        put: <T>(path: string, body: unknown, options?: RequestInit) => 
            apiPut<T>(path, body, withAuth(options)),
            
        delete: (path: string, options?: RequestInit) => 
            apiDelete(path, withAuth(options)),
    }
}
