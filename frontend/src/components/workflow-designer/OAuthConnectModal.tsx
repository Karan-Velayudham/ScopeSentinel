"use client";

import { useState } from "react";
import { X, Loader2, Key, ExternalLink } from "lucide-react";
import { useApi } from "@/hooks/use-api";

interface AvailableConnector {
    id: string;
    name: string;
    description: string;
    icon_url: string;
    auth_type: string;
    api_key_fields?: Array<{ name: string; label: string; secret: boolean; default?: string }>;
}

export function OAuthConnectModal({
    connector,
    onClose,
    onConnected,
}: {
    connector: AvailableConnector;
    onClose: () => void;
    onConnected: () => void;
}) {
    const api = useApi();
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [apiKeyValues, setApiKeyValues] = useState<Record<string, string>>({});

    const handleOAuth = async () => {
        if (!api.orgId) {
            setError('No organization context found.');
            return;
        }

        setLoading(true);
        setError('');
        try {
            const res = await api.fetch(`/api/connectors/${connector.id}/oauth/init`, { 
                method: 'POST'
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || 'OAuth init failed');
            // Open OAuth in new tab
            window.open(data.authorization_url, '_blank', 'width=600,height=700');
            // Listen for callback completion via storage event
            const handler = (e: StorageEvent) => {
                if (e.key === `oauth_connected_${connector.id}`) {
                    window.removeEventListener('storage', handler);
                    onConnected();
                }
            };
            window.addEventListener('storage', handler);
        } catch (e: any) {
            setError(e.message);
        } finally {
            setLoading(false);
        }
    };

    const handleApiKeyInstall = async () => {
        if (!api.orgId) {
            setError('No organization context found.');
            return;
        }

        setLoading(true);
        setError('');
        try {
            const res = await api.fetch(`/api/connectors/${connector.id}/install`, {
                method: 'POST',
                body: JSON.stringify({ config: apiKeyValues }),
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || 'Install failed');
            onConnected();
        } catch (e: any) {
            setError(e.message);
        } finally {
            setLoading(false);
        }
    };

    const fields = connector.api_key_fields || [];

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
            <div className="bg-card border rounded-xl shadow-2xl w-[420px] overflow-hidden">
                {/* Header */}
                <div className="flex items-center gap-3 px-5 py-4 border-b">
                    <img
                        src={connector.icon_url}
                        alt={connector.name}
                        className="h-8 w-8 rounded-lg object-contain"
                        onError={e => (e.currentTarget.style.display = 'none')}
                    />
                    <div className="flex-1 min-w-0">
                        <div className="font-semibold truncate">Connect {connector.name}</div>
                        <div className="text-xs text-muted-foreground">{connector.description}</div>
                    </div>
                    <button onClick={onClose} className="text-muted-foreground hover:text-foreground p-1 rounded">
                        <X className="h-4 w-4" />
                    </button>
                </div>

                {/* Body */}
                <div className="p-5 space-y-4">
                    {connector.auth_type === 'oauth' ? (
                        <>
                            <p className="text-sm text-muted-foreground">
                                Connect your {connector.name} account using OAuth. You'll be redirected to {connector.name} to authorize access.
                            </p>
                            <div className="text-xs text-muted-foreground bg-muted/40 rounded-md p-3">
                                <div className="font-medium mb-1 text-foreground">This will grant ScopeSentinel access to:</div>
                                <div className="space-y-0.5">
                                    <div>• Read and manage repositories</div>
                                    <div>• Post comments and create issues</div>
                                    <div>• Trigger workflows</div>
                                </div>
                            </div>
                            {error && <div className="text-xs text-destructive bg-destructive/10 rounded-md p-2">{error}</div>}
                            <button
                                disabled={loading}
                                onClick={handleOAuth}
                                className="w-full flex items-center justify-center gap-2 bg-primary text-primary-foreground rounded-lg px-4 py-2.5 text-sm font-medium hover:bg-primary/90 transition-colors disabled:opacity-60"
                            >
                                {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <ExternalLink className="h-4 w-4" />}
                                {loading ? 'Opening…' : `Connect with ${connector.name}`}
                            </button>
                        </>
                    ) : (
                        /* API Key form */
                        <>
                            <p className="text-sm text-muted-foreground">
                                Enter your {connector.name} credentials to connect.
                            </p>
                            <div className="space-y-3">
                                {fields.map(f => (
                                    <div key={f.name} className="space-y-1">
                                        <label className="text-xs font-medium">{f.label}</label>
                                        <input
                                            type={f.secret ? 'password' : 'text'}
                                            className="w-full border rounded-md px-3 py-2 text-sm bg-background outline-none focus:ring-1 focus:ring-ring"
                                            value={apiKeyValues[f.name] ?? (f.default || '')}
                                            onChange={e => setApiKeyValues(v => ({ ...v, [f.name]: e.target.value }))}
                                            placeholder={f.default || f.label}
                                        />
                                    </div>
                                ))}
                            </div>
                            {error && <div className="text-xs text-destructive bg-destructive/10 rounded-md p-2">{error}</div>}
                            <button
                                disabled={loading}
                                onClick={handleApiKeyInstall}
                                className="w-full flex items-center justify-center gap-2 bg-primary text-primary-foreground rounded-lg px-4 py-2.5 text-sm font-medium hover:bg-primary/90 transition-colors disabled:opacity-60"
                            >
                                {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Key className="h-4 w-4" />}
                                {loading ? 'Connecting…' : 'Save Credentials'}
                            </button>
                        </>
                    )}
                </div>
            </div>
        </div>
    );
}
