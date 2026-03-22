import { Node, Edge } from '@xyflow/react';
import yaml from 'js-yaml';

// Map React Flow node types → DSL step types
const NODE_TYPE_MAP: Record<string, string> = {
    agentNode: 'agent',
    toolNode: 'tool',
    hitlNode: 'hitl',
    conditionNode: 'condition',
    inputNode: 'input',
    outputNode: 'output',
    delayNode: 'delay',
};

export function workflowGraphToYaml(name: string, description: string, nodes: Node[], edges: Edge[]): string {
    // Find trigger node
    const triggerNode = nodes.find(n => n.type === 'triggerNode');

    // Build trigger block — use triggerType (new nodes) or type (legacy)
    const triggerData = triggerNode?.data as any;
    const trigger: Record<string, any> = {
        type: triggerData?.triggerType || triggerData?.type || 'manual',
    };
    if (triggerData?.schedule) trigger.schedule = triggerData.schedule;
    if (triggerData?.eventType) trigger.event = triggerData.eventType;
    if (triggerData?.eventFilter) trigger.filter = triggerData.eventFilter;

    // Generate steps — exclude trigger nodes (they go in the trigger block)
    const steps = nodes
        .filter(n => n.type !== 'triggerNode')
        .map(n => {
            const outEdges = edges.filter(e => e.source === n.id);
            const next = outEdges.length > 0 ? outEdges.map(e => e.target) : undefined;

            const typeStr = NODE_TYPE_MAP[n.type!] || 'agent';
            const nodeData = n.data as any;

            // Strip display-only fields that shouldn't go into the DSL
            const { label, agentType, triggerType, connector_name, ...cleanData } = nodeData;
            const ui_metadata = { position: n.position };

            const step: Record<string, any> = {
                id: n.id,
                name: nodeData.label || typeStr,
                type: typeStr,
                inputs: { ...cleanData, ui_metadata },
            };

            if (nodeData.agent_id) step.agent_id = nodeData.agent_id;
            if (next) step.next = next;

            return step;
        });

    const workflowObj: Record<string, any> = {
        name: name || 'Untitled Workflow',
        trigger,
        steps: steps.length > 0 ? steps : [],
    };
    if (description) workflowObj.description = description;

    return yaml.dump(workflowObj, { noRefs: true, skipInvalid: true });
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

    // 1. Trigger Node
    const triggerId = 'trigger-1';
    nodes.push({
        id: triggerId,
        type: 'triggerNode',
        position: { x: 50, y: 50 },
        data: {
            label: 'Trigger',
            triggerType: data.trigger?.type || 'manual',
            schedule: data.trigger?.schedule,
            eventType: data.trigger?.event,
            eventFilter: data.trigger?.filter,
        },
    });

    // 2. Step Nodes
    const DSL_TO_NODE: Record<string, string> = {
        agent: 'agentNode',
        tool: 'toolNode',
        hitl: 'hitlNode',
        condition: 'conditionNode',
        input: 'inputNode',
        output: 'outputNode',
        delay: 'delayNode',
    };

    const steps = data.steps || [];
    let yOffset = 150;

    steps.forEach((step: any) => {
        const nodeType = DSL_TO_NODE[step.type] || 'agentNode';

        let position = { x: 350, y: yOffset };
        if (step.inputs?.ui_metadata?.position) {
            position = step.inputs.ui_metadata.position;
        } else {
            yOffset += 130;
        }

        const { ui_metadata, ...restInputs } = step.inputs || {};

        nodes.push({
            id: step.id,
            type: nodeType,
            position,
            data: {
                ...restInputs,
                label: step.name,
                agent_id: step.agent_id || restInputs?.agent_id,
            },
        });

        // Edges from next[]
        if (step.next && Array.isArray(step.next)) {
            step.next.forEach((nextId: string) => {
                edges.push({
                    id: `e-${step.id}-${nextId}`,
                    source: step.id,
                    target: nextId,
                    animated: true,
                });
            });
        }
    });

    // Auto-connect trigger → first step if no explicit edges yet
    if (steps.length > 0 && edges.filter(e => e.source === triggerId).length === 0) {
        edges.push({
            id: `e-${triggerId}-${steps[0].id}`,
            source: triggerId,
            target: steps[0].id,
            animated: true,
        });
    }

    return {
        nodes,
        edges,
        name: data.name || 'Untitled Workflow',
        description: data.description || '',
    };
}
