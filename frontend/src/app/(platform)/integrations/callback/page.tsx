"use client";

import { useEffect, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { CheckCircle, XCircle, Loader2 } from 'lucide-react';

function OAuthCallbackContent() {
    const params = useSearchParams();
    const router = useRouter();
    const connector_id = params.get('connector_id') || '';
    const status = params.get('status') || '';

    useEffect(() => {
        if (status === 'connected' && connector_id) {
            // Notify opener via localStorage
            localStorage.setItem(`oauth_connected_${connector_id}`, Date.now().toString());
            // Auto-redirect after brief success display
            const timer = setTimeout(() => router.push('/integrations'), 2500);
            return () => clearTimeout(timer);
        }
    }, [status, connector_id, router]);

    const success = status === 'connected';

    return (
        <div className="flex flex-col items-center justify-center min-h-screen gap-4">
            <div className={`flex h-16 w-16 items-center justify-center rounded-full ${success ? 'bg-emerald-100 dark:bg-emerald-900/40' : 'bg-destructive/10'}`}>
                {success
                    ? <CheckCircle className="h-8 w-8 text-emerald-600 dark:text-emerald-400" />
                    : <XCircle className="h-8 w-8 text-destructive" />
                }
            </div>
            <div className="text-center">
                <h1 className="text-xl font-semibold">
                    {success ? `✅ ${connector_id} Connected!` : 'Connection Failed'}
                </h1>
                <p className="text-sm text-muted-foreground mt-1">
                    {success
                        ? 'Integration is now active. Redirecting back to workflows…'
                        : 'Something went wrong during the OAuth flow. Please try again.'}
                </p>
            </div>
            {success && <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />}
            {!success && (
                <button
                    onClick={() => router.push('/workflows')}
                    className="text-sm bg-primary text-primary-foreground px-4 py-2 rounded-md hover:bg-primary/90"
                >
                    Back to Integrations
                </button>
            )}
        </div>
    );
}

export default function OAuthCallbackPage() {
    return (
        <Suspense fallback={<div className="flex items-center justify-center min-h-screen"><Loader2 className="h-6 w-6 animate-spin" /></div>}>
            <OAuthCallbackContent />
        </Suspense>
    );
}
