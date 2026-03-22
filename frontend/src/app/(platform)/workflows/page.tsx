"use client";

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Plus, Edit, Trash2 } from 'lucide-react';
import { apiFetch } from '@/lib/api-client';

export default function WorkflowsPage() {
    const [workflows, setWorkflows] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);

    const fetchWorkflows = () => {
        apiFetch('/api/workflows')
            .then(res => res.json())
            .then(data => {
                setWorkflows(data.items || []);
                setLoading(false);
            })
            .catch(e => {
                console.error(e);
                setLoading(false);
            });
    };

    useEffect(() => {
        fetchWorkflows();
    }, []);

    const handleDelete = async (id: string) => {
        if (!confirm("Are you sure you want to delete this workflow?")) return;
        try {
            await apiFetch(`/api/workflows/${id}`, { method: 'DELETE' });
            fetchWorkflows();
        } catch (e) {
            console.error(e);
        }
    };

    return (
        <div className="flex flex-col gap-6">
            <div className="flex items-center justify-between">
                <h1 className="text-3xl font-bold tracking-tight">Workflows</h1>
                <Link
                    href="/workflows/new/designer"
                    className="flex items-center gap-2 bg-primary text-primary-foreground px-4 py-2 rounded-md hover:bg-primary/90 transition-colors"
                >
                    <Plus className="h-4 w-4" />
                    Create Workflow
                </Link>
            </div>

            {loading ? (
                <div>Loading workflows...</div>
            ) : workflows.length === 0 ? (
                <div className="flex flex-col items-center justify-center p-12 border border-dashed rounded-lg bg-muted/10">
                    <p className="text-muted-foreground mb-4">No workflows found.</p>
                    <Link
                        href="/workflows/new/designer"
                        className="flex items-center gap-2 bg-primary text-primary-foreground px-4 py-2 rounded-md hover:bg-primary/90 transition-colors"
                    >
                        <Plus className="h-4 w-4" />
                        Create your first workflow
                    </Link>
                </div>
            ) : (
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                    {workflows.map(wf => (
                        <div key={wf.id} className="border rounded-lg bg-card p-5 flex flex-col justify-between shadow-sm">
                            <div>
                                <h3 className="font-semibold text-lg truncate">{wf.name}</h3>
                                <p className="text-sm text-muted-foreground mt-1 line-clamp-2 min-h-10">
                                    {wf.description || 'No description provided.'}
                                </p>
                                <div className="mt-4 text-xs text-muted-foreground flex gap-4">
                                    <span>Version: {wf.version}</span>
                                    <span>Updated: {new Date(wf.updated_at).toLocaleDateString()}</span>
                                </div>
                            </div>
                            <div className="mt-6 flex items-center justify-end gap-2 border-t pt-4">
                                <Link
                                    href={`/workflows/${wf.id}/designer`}
                                    className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-muted text-foreground rounded-md hover:bg-muted/80 transition-colors cursor-pointer"
                                >
                                    <Edit className="h-3.5 w-3.5" />
                                    Designer
                                </Link>
                                <button
                                    onClick={() => handleDelete(wf.id)}
                                    className="p-1.5 text-destructive hover:bg-destructive/10 rounded-md transition-colors cursor-pointer"
                                >
                                    <Trash2 className="h-4 w-4" />
                                </button>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
