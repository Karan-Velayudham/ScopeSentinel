import { Node, Edge } from '@xyflow/react';
import yaml from 'js-yaml';

export function workflowGraphToYaml(name: string, description: string, nodes: Node[], edges: Edge[]): string {
    // Find trigger node
    const triggerNode = nodes.find(n => n.type === 'triggerNode');

    const trigger = triggerNode ? {
        type: triggerNode.data.type || 'unknown'
    } : { type: 'manual' };

    // Generate steps
    const steps = nodes
        .filter(n => n.type !== 'triggerNode')
        .map((n) => {
            // Find outgoing edges to determine "next" logic
            const outEdges = edges.filter(e => e.source === n.id);
            let next: string[] | undefined = undefined;

            if (outEdges.length > 0) {
                next = outEdges.map(e => e.target);
            }

            let typeStr = 'agent';
            if (n.type === 'toolNode') typeStr = 'tool';
            if (n.type === 'hitlNode') typeStr = 'hitl';
            if (n.type === 'conditionNode') typeStr = 'condition';

            // We preserve the UI position in inputs so we can place it on load
            const ui_metadata = {
                position: n.position
            };

            const agent_id = n.data.agent_id || n.data.agentId;

            return {
                id: n.id,
                name: n.data.label || typeStr,
                type: typeStr,
                agent_id,
                inputs: {
                    ...n.data,
                    ui_metadata
                },
                next
            };
        });

    const workflowObj = {
        name: name || 'Untitled Workflow',
        description: description || undefined,
        trigger,
        steps: steps.length > 0 ? steps : []
    };

    return yaml.dump(workflowObj, { noRefs: true });
}

export function yamlToWorkflowGraph(yamlStr: string): { nodes: Node[], edges: Edge[], name: string, description: string } {
    const nodes: Node[] = [];
    const edges: Edge[] = [];

    if (!yamlStr) {
        return { nodes, edges, name: 'Untitled Workflow', description: '' };
    }

    let data: any;
    try {
        data = yaml.load(yamlStr);
    } catch (e) {
        console.error("Failed to parse YAML", e);
        return { nodes, edges, name: 'Untitled Workflow', description: '' };
    }

    if (!data) {
        return { nodes, edges, name: 'Untitled Workflow', description: '' };
    }

    // 1. Create Trigger Node
    const triggerId = 'trigger-1';
    nodes.push({
        id: triggerId,
        type: 'triggerNode',
        position: { x: 50, y: 50 },
        data: {
            label: 'Trigger',
            type: data.trigger?.type || 'manual'
        }
    });

    // 2. Create nodes for steps
    const steps = data.steps || [];
    let yOffset = 150;

    steps.forEach((step: any) => {
        let nodeType = 'agentNode';
        if (step.type === 'tool') nodeType = 'toolNode';
        if (step.type === 'hitl') nodeType = 'hitlNode';
        if (step.type === 'condition') nodeType = 'conditionNode';

        let position = { x: 50, y: yOffset };
        if (step.inputs?.ui_metadata?.position) {
            position = step.inputs.ui_metadata.position;
        } else {
            yOffset += 100;
        }

        // copy inputs minus ui_metadata into data
        const nodeData = {
            ...step.inputs,
            label: step.name,
            agentId: step.agent_id || step.inputs?.agentId
        };
        delete nodeData.ui_metadata;

        nodes.push({
            id: step.id,
            type: nodeType,
            position,
            data: nodeData
        });

        // 3. Create edges
        if (step.next && Array.isArray(step.next)) {
            step.next.forEach((nextId: string) => {
                edges.push({
                    id: `e-${step.id}-${nextId}`,
                    source: step.id,
                    target: nextId
                });
            });
        }
    });

    // Connect trigger to first step if no explicit trigger edge exists
    if (steps.length > 0) {
        edges.push({
            id: `e-${triggerId}-${steps[0].id}`,
            source: triggerId,
            target: steps[0].id
        });
    }

    return {
        nodes,
        edges,
        name: data.name || 'Untitled Workflow',
        description: data.description || ''
    };
}
