
import asyncio
from contextlib import AsyncExitStack
from pathlib import Path

import ollama
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


MODEL = "qwen2.5:3b"

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

        print(f"Connected to {name} MCP")


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

    result = await tool_info["session"].call_tool(
        tool_info["original_name"],
        arguments=arguments
    )

    result_text = "\n".join(
        item.text
        for item in result.content
        if hasattr(item, "text")
    )

    if result.is_error:
        return f"Tool execution failed: {result_text}"

    return result_text


async def main():

    ollama_client = ollama.AsyncClient()

    async with AsyncExitStack() as stack:

        # Connect both MCP servers
        sessions = await connect_servers(stack, servers)

        # Discover tools from both servers
        available_tools, registry = await collect_tools(sessions)

        print(f"\nDiscovered {len(available_tools)} tools.")

        for tool in available_tools:
            print(f"- {tool['function']['name']}")

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a customer support assistant. "
                    "Use customer tools for customer information. "
                    "Use support tools for order information. "
                    "Only report information returned by tools. "
                    "Never invent customer or order information."
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
        for _ in range(5):

            messages.append(response.message)

            tool_calls = response.message.tool_calls or []

            if not tool_calls:
                break

            for tool_call in tool_calls:

                print(
                    f"\nCalling: {tool_call.function.name}"
                )

                result = await execute_tool(registry, tool_call)

                print(f"Result: {result}")

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

        print("\nSupport AI:")
        print(response.message.content)


if __name__ == "__main__":
    asyncio.run(main())
