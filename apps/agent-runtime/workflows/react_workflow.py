from datetime import timedelta
from temporalio import workflow
from temporalio.common import RetryPolicy
import json

with workflow.unsafe.imports_passed_through():
    from activities.react_activities import (
        get_agent_config_activity,
        llm_reasoning_activity,
        execute_tool_activity,
        log_event_activity,
        update_run_status_activity,
        get_org_id_activity
    )

default_retry_policy = RetryPolicy(
    maximum_attempts=3,
    initial_interval=timedelta(seconds=2),
    maximum_interval=timedelta(seconds=10),
)

@workflow.defn
class AgentReActWorkflow:
    @workflow.run
    async def run(self, agent_id: str, run_id: str, task_input: str) -> dict:
        # run_id is the DB UUID for the WorkflowRun
        
        # 1. Initialization
        org_id = await workflow.execute_activity(
            get_org_id_activity,
            run_id,
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=default_retry_policy
        )
        
        await workflow.execute_activity(
            update_run_status_activity,
            {"run_id": run_id, "status": "RUNNING"},
            start_to_close_timeout=timedelta(seconds=10)
        )
        
        agent_config = await workflow.execute_activity(
            get_agent_config_activity,
            agent_id,
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=default_retry_policy
        )
        
        # Build system prompt with skills
        system_prompt = agent_config["identity"]
        if agent_config["skills"]:
            system_prompt += "\n\nYou have the following skills/capabilities:\n"
            for skill in agent_config["skills"]:
                system_prompt += f"- {skill['name']}: {skill['content']}\n"
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": task_input}
        ]
        
        # Phase 4: Handle Long-term Memory (RAG)
        if agent_config.get("memory_mode") == "long_term":
            # Inject platform:search_memory tool
            search_tool = {
                "name": "platform:search_memory",
                "description": "Search the organization's knowledge base for relevant context and documentation.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query to find relevant information."
                        }
                    },
                    "required": ["query"]
                }
            }
            # Add to agent's tools
            if not agent_config.get("tools"):
                agent_config["tools"] = []
            
            # Avoid duplicate injection
            if not any(t.get("name") == "platform:search_memory" for t in agent_config["tools"]):
                agent_config["tools"].append(search_tool)

        # 2. ReAct Loop
        max_iterations = agent_config.get("max_iterations", 10)
        iteration = 0
        total_p_tokens = 0
        total_c_tokens = 0
        
        while iteration < max_iterations:
            iteration += 1
            
            # Reasoning Step
            reasoning_res = await workflow.execute_activity(
                llm_reasoning_activity,
                {
                    "messages": messages,
                    "model": agent_config["model"],
                    "tools": agent_config["tools"]
                },
                start_to_close_timeout=timedelta(minutes=2),
                retry_policy=default_retry_policy
            )
            
            p_tokens = reasoning_res["usage"].get("input_tokens", 0)
            c_tokens = reasoning_res["usage"].get("output_tokens", 0)
            total_p_tokens += p_tokens
            total_c_tokens += c_tokens
            
            # Log Thought
            if reasoning_res["content"]:
                await workflow.execute_activity(
                    log_event_activity,
                    {
                        "run_id": run_id,
                        "event_type": "THOUGHT",
                        "payload": {"text": reasoning_res["content"]}
                    },
                    start_to_close_timeout=timedelta(seconds=10)
                )
                messages.append({"role": "assistant", "content": reasoning_res["content"]})
            
            # Check for Tool Calls
            tool_calls = reasoning_res.get("tool_calls", [])
            if not tool_calls:
                # Agent finished or just gave a text response without tools
                break
                
            # Log Tool Call and Execute
            # For simplicity in this iteration, we execute tool calls sequentially
            tool_msg = {"role": "assistant", "tool_calls": []}
            for tc in tool_calls:
                tool_msg["tool_calls"].append({
                    "id": tc["id"],
                    "type": "function",
                    "function": {
                        "name": tc["function"]["name"],
                        "arguments": tc["function"]["arguments"]
                    }
                })
                
                await workflow.execute_activity(
                    log_event_activity,
                    {
                        "run_id": run_id,
                        "event_type": "TOOL_CALL",
                        "payload": {
                            "tool": tc["function"]["name"],
                            "args": tc["function"]["arguments"],
                            "call_id": tc["id"]
                        }
                    },
                    start_to_close_timeout=timedelta(seconds=10)
                )
                
                # Execute Tool
                tool_output = await workflow.execute_activity(
                    execute_tool_activity,
                    {
                        "tool_name": tc["function"]["name"],
                        "tool_args": tc["function"]["arguments"],
                        "org_id": org_id
                    },
                    start_to_close_timeout=timedelta(minutes=5),
                    retry_policy=default_retry_policy
                )
                
                # Log Result
                await workflow.execute_activity(
                    log_event_activity,
                    {
                        "run_id": run_id,
                        "event_type": "TOOL_RESULT",
                        "payload": {
                            "tool": tc["function"]["name"],
                            "output": tool_output.get("result") or tool_output.get("error"),
                            "call_id": tc["id"]
                        }
                    },
                    start_to_close_timeout=timedelta(seconds=10)
                )
                
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": str(tool_output.get("result") or tool_output.get("error"))
                })

        # 3. Finalize
        await workflow.execute_activity(
            update_run_status_activity,
            {
                "run_id": run_id,
                "status": "COMPLETED",
                "prompt_tokens": total_p_tokens,
                "completion_tokens": total_c_tokens
            },
            start_to_close_timeout=timedelta(seconds=10)
        )
        
        final_response = messages[-1]["content"] if messages[-1]["role"] == "assistant" else "Done."
        
        return {
            "status": "COMPLETED",
            "output": final_response,
            "usage": {
                "prompt_tokens": total_p_tokens,
                "completion_tokens": total_c_tokens
            }
        }
