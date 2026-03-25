"use client";

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { Designer } from '@/components/workflow-designer/Designer';
import { workflowGraphToYaml, yamlToWorkflowGraph } from '@/lib/workflow-parser';
import { Node, Edge } from '@xyflow/react';
import { ArrowLeft, Loader2 } from 'lucide-react';
import Link from 'next/link';
import { useApi } from '@/hooks/use-api';

export default function WorkflowDesignerPage() {
    const api = useApi();
    const params = useParams();
    const id = params.id as string;
    const router = useRouter();

    const [loading, setLoading] = useState(true);
    const [initialNodes, setInitialNodes] = useState<Node[]>([]);
    const [initialEdges, setInitialEdges] = useState<Edge[]>([]);
    const [workflowName, setWorkflowName] = useState('New Workflow');
    const [workflowDesc, setWorkflowDesc] = useState('');
    const [workflowStatus, setWorkflowStatus] = useState('draft');

    useEffect(() => {
        if (!api.orgId && id !== 'new') return;

        if (id === 'new') {
            const { nodes, edges } = yamlToWorkflowGraph('');
            setInitialNodes(nodes);
            setInitialEdges(edges);
            setLoading(false);
            return;
        }

        api.fetch(`/api/workflows/${id}`)
            .then(res => {
                if (!res.ok) throw new Error("Failed to fetch workflow");
                return res.json();
            })
            .then(data => {
                const { nodes, edges } = yamlToWorkflowGraph(data.yaml_content || '');
                setInitialNodes(nodes);
                setInitialEdges(edges);
                setWorkflowName(data.name || 'Workflow');
                setWorkflowDesc(data.description || '');
                setWorkflowStatus(data.status || 'draft');
                setLoading(false);
            })
            .catch(err => {
                console.error(err);
                setLoading(false);
            });
    }, [id, api.orgId]);

    const handleSave = async (nodes: Node[], edges: Edge[], name: string) => {
        if (!api.orgId) {
            alert("No organization context found.");
            return;
        }

        const yamlContent = workflowGraphToYaml(name, workflowDesc, nodes, edges);
        const method = id === 'new' ? 'POST' : 'PUT';
        const url = id === 'new' ? `/api/workflows/` : `/api/workflows/${id}`;

        const payload = id === 'new'
            ? { name, description: workflowDesc, yaml_content: yamlContent }
            : { yaml_content: yamlContent, name };

        try {
            const res = await api.fetch(url, {
                method,
                body: JSON.stringify(payload),
            });

            if (res.ok) {
                if (id === 'new') {
                    const data = await res.json();
                    router.push(`/workflows/${data.id}/designer`);
                }
                // If update — the top bar already shows "Saved" feedback
            } else {
                const error = await res.json();
                alert(`Failed to save: ${error.detail}`);
            }
        } catch (e) {
            console.error(e);
            alert("Error saving workflow");
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center h-[calc(100vh-120px)]">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
        );
    }

    return (
        <div className="flex flex-col gap-0 h-full">
            {/* Back nav */}
            <div className="flex items-center gap-2 pb-3">
                <Link href="/workflows" className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors">
                    <ArrowLeft className="h-4 w-4" /> Workflows
                </Link>
            </div>

            <Designer
                workflowId={id === 'new' ? undefined : id}
                initialName={workflowName}
                initialNodes={initialNodes}
                initialEdges={initialEdges}
                initialStatus={workflowStatus}
                onSave={handleSave}
            />
        </div>
    );
}
