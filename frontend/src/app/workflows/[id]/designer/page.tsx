"use client";

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { Designer } from '@/components/workflow-designer/Designer';
import { workflowGraphToYaml, yamlToWorkflowGraph } from '@/lib/workflow-parser';
import { Node, Edge } from '@xyflow/react';
import { ArrowLeft } from 'lucide-react';
import Link from 'next/link';

export default function WorkflowDesignerPage() {
    const params = useParams();
    const id = params.id as string;
    const router = useRouter();

    const [loading, setLoading] = useState(true);
    const [initialNodes, setInitialNodes] = useState<Node[]>([]);
    const [initialEdges, setInitialEdges] = useState<Edge[]>([]);
    const [workflowName, setWorkflowName] = useState('Untitled Workflow');
    const [workflowDesc, setWorkflowDesc] = useState('');

    useEffect(() => {
        // If id is "new", we can start with a blank canvas
        if (id === 'new') {
            const { nodes, edges } = yamlToWorkflowGraph('');
            setInitialNodes(nodes);
            setInitialEdges(edges);
            setLoading(false);
            return;
        }

        fetch(`http://localhost:8000/api/workflows/${id}`)
            .then(res => {
                if (!res.ok) throw new Error("Failed to fetch workflow");
                return res.json();
            })
            .then(data => {
                const { nodes, edges, name, description } = yamlToWorkflowGraph(data.yaml_content || '');
                setInitialNodes(nodes);
                setInitialEdges(edges);
                setWorkflowName(data.name || name);
                setWorkflowDesc(data.description || description);
                setLoading(false);
            })
            .catch(err => {
                console.error(err);
                setLoading(false);
            });
    }, [id]);

    const handleSave = async (nodes: Node[], edges: Edge[]) => {
        const yamlContent = workflowGraphToYaml(workflowName, workflowDesc, nodes, edges);
        const method = id === 'new' ? 'POST' : 'PUT';
        const url = id === 'new'
            ? `http://localhost:8000/api/workflows/`
            : `http://localhost:8000/api/workflows/${id}`;

        const payload = id === 'new'
            ? { name: workflowName, description: workflowDesc, yaml_content: yamlContent }
            : { yaml_content: yamlContent };

        try {
            const res = await fetch(url, {
                method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            if (res.ok) {
                if (id === 'new') {
                    const data = await res.json();
                    router.push(`/workflows/${data.id}/designer`);
                } else {
                    alert("Workflow saved successfully!");
                }
            } else {
                const error = await res.json();
                alert(`Failed to save workflow: ${error.detail}`);
            }
        } catch (e) {
            console.error(e);
            alert("Error saving workflow");
        }
    };

    if (loading) return <div className="p-8 flex items-center justify-center">Loading designer...</div>;

    return (
        <div className="flex flex-col gap-4 h-[calc(100vh-100px)]">
            <div className="flex items-center gap-4 border-b pb-4">
                <Link href="/workflows" className="text-muted-foreground hover:text-foreground">
                    <ArrowLeft className="h-5 w-5" />
                </Link>
                <div className="flex flex-col flex-1">
                    <input
                        className="text-2xl font-bold bg-transparent border-none outline-none placeholder-muted-foreground"
                        value={workflowName}
                        onChange={(e) => setWorkflowName(e.target.value)}
                        placeholder="Workflow Name"
                    />
                    <input
                        className="text-sm text-muted-foreground bg-transparent border-none outline-none w-full placeholder-muted-foreground/50"
                        value={workflowDesc}
                        onChange={(e) => setWorkflowDesc(e.target.value)}
                        placeholder="Enter workflow description..."
                    />
                </div>
            </div>
            <Designer
                initialNodes={initialNodes}
                initialEdges={initialEdges}
                onSave={handleSave}
            />
        </div>
    );
}
