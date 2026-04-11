export interface AgentResponse {
  id: string;
  org_id: string;
  name: string;
  description?: string | null;
  instructions: string;
  model: string;
  timeout_seconds: number;
  app_connections: string[];
  skills: string[];
  status: string;
  created_at: string;
  updated_at: string;
}

export interface AgentListResponse {
  items: AgentResponse[];
  meta: {
    total: number;
    page: number;
    page_size: number;
    has_next: boolean;
  };
}

export interface AgentCreateRequest {
  name: string;
  description?: string | null;
  instructions: string;
  model?: string;
  timeout_seconds?: number;
  app_connections?: string[];
  skills?: string[];
  status?: "active" | "draft" | "archived";
}

export interface AgentUpdateRequest {
  name?: string;
  description?: string | null;
  instructions?: string;
  model?: string;
  timeout_seconds?: number;
  app_connections?: string[];
  skills?: string[];
  status?: "active" | "draft" | "archived";
}

export interface AgentExecuteRequest {
  input: Record<string, unknown>;
  skill_ids?: string[];
  triggered_by?: "manual" | "workflow" | "trigger";
  source_id?: string;
}

export interface AgentExecuteResponse {
  run_id: string;
  status: string;
  output?: string | null;
  error?: string | null;
}

export interface AgentRunResponse {
  id: string;
  agent_id: string;
  triggered_by: string;
  status: string;
  created_at: string;
  completed_at?: string | null;
}

export interface AgentRunListResponse {
  items: AgentRunResponse[];
  meta: {
    total: number;
    page: number;
    page_size: number;
    has_next: boolean;
  };
}

export interface AgentRunDetailResponse extends AgentRunResponse {
  skill_ids: string[];
  input_json: string;
  prompt_used?: string | null;
  output?: string | null;
  error_message?: string | null;
}
