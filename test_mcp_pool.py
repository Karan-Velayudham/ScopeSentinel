import asyncio
import yaml
from agentscope.mcp import StdIOStatefulClient

async def main():
    with open("mcp_servers.yaml", "r") as f:
        config = yaml.safe_load(f)

    from agentscope.tool import Toolkit
    toolkit = Toolkit()
    
    for name, server_config in config.get("mcp_servers", {}).items():
        command = server_config.get("command")
        args = server_config.get("args", [])
        env = server_config.get("env", {})
        
        print(f"Connecting to {name} via {command} {args}")
        client = StdIOStatefulClient(name, command=command, args=args)
        await client.connect()
        clients.append(client)
        
        await toolkit.register_mcp_client(client)
        
    # Test setting up ReActAgent
    from agentscope.agent import ReActAgent
    from agentscope.model import OpenAIChatModel
    import os
    from dotenv import load_dotenv
    load_dotenv()
    
    model = OpenAIChatModel(model_name="gpt-4o", api_key=os.environ["OPENAI_API_KEY"])
    
    # We shouldn't use await client.close() until we are done.
    try:
        agent = ReActAgent(name="Tester", model=model, sys_prompt="You are a helpful assistant.", toolkit=toolkit)
        print("Agent created successfully.")
        
        # Test a simple query
        from agentscope.message import Msg
        response = agent(Msg(name="user", role="user", content="Fetch Jira ticket SCRUM-8"))
        print("\nAgent Response:")
        print(response.content)
    finally:
        for client in clients:
            await client.close()

if __name__ == "__main__":
    import agentscope
    agentscope.init()
    asyncio.run(main())
