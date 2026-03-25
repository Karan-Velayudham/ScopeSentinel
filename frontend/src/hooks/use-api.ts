"use client"

import { useSession } from "next-auth/react"
import { apiGet, apiPost, apiPatch, apiDelete, apiFetch } from "@/lib/api-client"

/**
 * Custom hook that provides org-aware API methods.
 * Automatically injects the X-ScopeSentinel-Org-ID header from the session.
 */
export function useApi() {
    const { data: session } = useSession()
    const orgId = session?.user?.org_id

    const withOrgHeader = (options: RequestInit = {}) => {
        if (!orgId) return options
        
        return {
            ...options,
            headers: {
                ...options.headers,
                'X-ScopeSentinel-Org-ID': orgId
            }
        }
    }

    return {
        session,
        orgId,
        fetch: (path: string, options?: RequestInit) => 
            apiFetch(path, withOrgHeader(options)),
        
        get: <T>(path: string, options?: RequestInit) => 
            apiGet<T>(path, withOrgHeader(options)),
            
        post: <T>(path: string, body: unknown, options?: RequestInit) => 
            apiPost<T>(path, body, withOrgHeader(options)),
            
        patch: <T>(path: string, body: unknown, options?: RequestInit) => 
            apiPatch<T>(path, body, withOrgHeader(options)),
            
        delete: (path: string, options?: RequestInit) => 
            apiDelete(path, withOrgHeader(options)),
    }
}
