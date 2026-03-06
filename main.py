import os
from dotenv import load_dotenv
import logging
import agentscope
from agentscope.agent import UserAgent, AgentBase
from agentscope.model import OpenAIChatModel
from agentscope.message import Msg

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

import asyncio

class SimpleAssistant(AgentBase):
    def __init__(self, name: str, sys_prompt: str, model: OpenAIChatModel):
        super().__init__()
        self.name = name
        self.sys_prompt = sys_prompt
        self.model = model
        
        # In current agentscope version, memory is initialized manually
        from agentscope.memory import InMemoryMemory
        from agentscope.message import Msg
        self.memory = InMemoryMemory()
        
        # Adding to memory is async, we'll do this on the first reply if it's empty
        self._init_memory_done = False

    async def reply(self, x: dict = None) -> dict:
        if not self._init_memory_done:
            await self.memory.add(Msg(name="system", role="system", content=self.sys_prompt))
            self._init_memory_done = True
            
        if x is not None:
            await self.memory.add(x)
            
        # Format memory for the model
        messages = await self.memory.get_memory()
        formatted_messages = [{"role": msg.role, "content": msg.content} for msg in messages]
        
        # Call the model
        response = await self.model(formatted_messages)
        
        # Extract text from the ChatResponse content format
        response_text = ""
        if hasattr(response, 'content') and isinstance(response.content, list) and len(response.content) > 0:
            if isinstance(response.content[0], dict) and 'text' in response.content[0]:
                response_text = response.content[0]['text']
        
        msg = Msg(name=self.name, role="assistant", content=response_text or str(response))
        await self.memory.add(msg)
        return msg

async def main():
    try:
        # Load environment variables
        load_dotenv()
        
        # Check for required API Key (basic validation)
        if not os.environ.get("OPENAI_API_KEY"):
             logger.warning("OPENAI_API_KEY not found in environment. Please set it or use .env file.")
             logger.warning("AgentScope initialization may fail if the model requires it.")

        # Initialize the Model
        logger.info("Initializing Model...")
        model = OpenAIChatModel(
            model_name="gpt-4o",
            api_key=os.environ.get("OPENAI_API_KEY"),
            stream=False # Explicitly disable streaming for the basic test
        )

        logger.info("Model initialized successfully.")

        # Initialize AgentScope
        logger.info("Initializing AgentScope...")
        agentscope.init(
            project="ScopeSentinel",
            name="Prototype_Run"
        )
        logger.info("AgentScope initialized successfully.")

        # Set up a simple two-agent conversation to verify it works
        
        # 1. User Agent (represents the human or system input)
        user_agent = UserAgent(
             name="User"
        )
        
        # 2. Assistant Agent (the simple planner/assistant)
        assistant_agent = SimpleAssistant(
            name="Assistant",
            sys_prompt="You are a helpful AI assistant for the ScopeSentinel platform.",
            model=model
        )
        
        # Initiate a test conversation
        logger.info("Starting test conversation...")
        
        # We simulate a user input here instead of prompting for one, to let the test run automatically
        test_msg = Msg(name="User", role="user", content="Hello! Are you ready to help build ScopeSentinel?")
        
        logger.info(f"User says: {test_msg.content}")

        # Get response from the assistant
        response_msg = await assistant_agent(test_msg)
        
        logger.info(f"Assistant replied: {response_msg.content}")
        logger.info("Prototype workflow orchestrator test completed successfully.")

    except Exception as e:
        logger.error(f"An error occurred during execution: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())
