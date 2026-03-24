import pytest
from core.registry import ToolRegistry

def test_registry_registration():
    registry = ToolRegistry()
    
    # Mock MCP tool object matching what agentscope/mcp returns
    class MockTool:
        def __init__(self, name, description, schema):
            self.name = name
            self.description = description
            self.inputSchema = schema

    mock_tool = MockTool("test_tool", "A test tool", {"type": "object"})
    
    registry.register_tools("test_server", [mock_tool])
    
    tools = registry.get_all_tools()
    assert len(tools) == 1
    assert tools[0].name == "test_tool"
    assert tools[0].server_name == "test_server"
    assert tools[0].input_schema == {"type": "object"}

    retrieved = registry.get_tool("test_server", "test_tool")
    assert retrieved is not None
    assert retrieved.name == "test_tool"
