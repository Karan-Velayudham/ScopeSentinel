import asyncio
from agentscope.mcp import StdIOStatefulClient

async def main():
    client = StdIOStatefulClient("myclient", command="python", args=["tools/mcp_server.py"])
    await client.connect()
    print("Tools:", await client.list_tools())
    fetch = await client.get_callable_function("fetch_jira_ticket")
    from mcp.types import Tool
    print("Function:", fetch)
    res = fetch(ticket_id="SCRUM-6")
    if asyncio.iscoroutine(res):
        res = await res
    print("Result:", res)
    await client.close()

if __name__ == "__main__":
    asyncio.run(main())
