
import asyncio
from contextlib import AsyncExitStack
from pathlib import Path

import ollama
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

import os
from dotenv import load_dotenv
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)

logger = logging.getLogger("support-ai")

load_dotenv()

MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
MAX_TOOL_ITERATIONS = int(os.getenv("MAX_TOOL_ITERATIONS", "5"))

projects_dir = Path("../").resolve()

servers = {
    "support": StdioServerParameters(
        command=str(projects_dir / "support-mcp/.venv/bin/python"),
        args=[str(projects_dir / "support-mcp/server.py")]
    ),
    "customer": StdioServerParameters(
        command=str(projects_dir / "customer-mcp/.venv/bin/python"),
        args=[str(projects_dir / "customer-mcp/server.py")]
    )
}


async def connect_servers(stack, servers):

    sessions = {}

    for name, params in servers.items():

        read, write = await stack.enter_async_context(
            stdio_client(params)
        )

        session = await stack.enter_async_context(
            ClientSession(read, write)
        )

        await session.initialize()

        sessions[name] = session

        logger.info("Connected to %s MCP", name)


    return sessions


async def collect_tools(sessions):

    ollama_tools = []
    registry = {}

    for server_name, session in sessions.items():

        result = await session.list_tools()

        for tool in result.tools:

            exposed_name = f"{server_name}__{tool.name}"

            ollama_tools.append({
                "type": "function",
                "function": {
                    "name": exposed_name,
                    "description": tool.description or "",
                    "parameters": tool.input_schema
                }
            })

            registry[exposed_name] = {
                "session": session,
                "original_name": tool.name
            }

    return ollama_tools, registry


async def execute_tool(registry, tool_call):

    exposed_name = tool_call.function.name
    arguments = tool_call.function.arguments

    tool_info = registry[exposed_name]

    try:
        result = await call_tool_with_retry(
            tool_info["session"],
            tool_info["original_name"],
            arguments
        )

    except TimeoutError:
        return "Tool execution failed: Request timed out after 3 attempts."

    result_text = "\n".join(
        item.text
        for item in result.content
        if hasattr(item, "text")
    )

    if result.is_error:
        return f"Tool execution failed: {result_text}"

    return result_text

async def call_tool_with_retry(session, tool_name, arguments):

    for attempt in range(3):

        try:
            return await asyncio.wait_for(
                session.call_tool(
                    tool_name,
                    arguments=arguments
                ),
                timeout=15.0
            )

        except TimeoutError:

            logger.info("Tool timeout. Attempt {attempt + 1}/3")
            if attempt == 2:
                raise

            await asyncio.sleep(1)

async def main():

    ollama_client = ollama.AsyncClient(
        host=OLLAMA_HOST,
        timeout=30.0
    )

    async with AsyncExitStack() as stack:

        # Connect both MCP servers
        sessions = await connect_servers(stack, servers)

        # Discover tools from both servers
        available_tools, registry = await collect_tools(sessions)

        logger.info(f"\nDiscovered {len(available_tools)} tools.")

        for tool in available_tools:
            logger.info(f"- {tool['function']['name']}")

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a customer support assistant. "
                    "Use customer tools for customer information. "
                    "Use support tools for order information. "
                    "Only report information returned by tools. "
                    "Never invent customer or order information. "
                    "You must provide valid arguments according to each tool's schema. "
                    "If a tool returns an error, analyze it and retry with corrected arguments when possible."
                )
            },
            {
                "role": "user",
                "content": "Find customer John and check his orders."
            }
        ]

        response = await ollama_client.chat(
            model=MODEL,
            messages=messages,
            tools=available_tools
        )

        # Tool calling loop
        for _ in range(MAX_TOOL_ITERATIONS):

            messages.append(response.message)

            tool_calls = response.message.tool_calls or []

            if not tool_calls:
                break

            for tool_call in tool_calls:

                logger.info(
                    f"\nCalling: {tool_call.function.name}"
                )

                result = await execute_tool(registry, tool_call)

                logger.info(f"Result: {result}")

                messages.append({
                    "role": "tool",
                    "tool_name": tool_call.function.name,
                    "content": result
                })

            response = await ollama_client.chat(
                model=MODEL,
                messages=messages,
                tools=available_tools
            )

        logger.info("\nSupport AI:")
        logger.info(response.message.content)


if __name__ == "__main__":
    try:
        asyncio.run(main())

    except KeyboardInterrupt:
        print("\nApplication interrupted.")

    except Exception:
        logger.exception("Application stopped due to an unexpected error")