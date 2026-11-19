
import asyncio
from pathlib import Path

import ollama
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


MODEL = "qwen2.5:3b"

server_project = Path("../support-mcp").resolve()

server_params = StdioServerParameters(
    command=str(server_project / ".venv/bin/python"),
    args=[str(server_project / "server.py")]
)


def convert_mcp_tools(mcp_tools):
    """Convert MCP tool definitions into Ollama format."""

    ollama_tools = []

    for tool in mcp_tools:
        ollama_tools.append({
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description or "",
                "parameters": tool.inputSchema
            }
        })

    return ollama_tools


async def main():

    # Connect to Ollama
    ollama_client = ollama.AsyncClient()

    # Connect to MCP server
    async with stdio_client(server_params) as (read, write):

        async with ClientSession(read, write) as session:

            await session.initialize()

            print("Connected to Support MCP!")

            # Get MCP tools
            mcp_tools = await session.list_tools()

            # Convert MCP tools to Ollama format
            available_tools = convert_mcp_tools(mcp_tools.tools)

            print(f"Discovered {len(available_tools)} tools.")

            # Conversation history
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are a helpful customer support assistant. "
                        "Use available tools when you need order information. "
                        "Never invent order information."
                    )
                },
                {
                    "role": "user",
                    "content": "What is the status of order 123?"
                }
            ]

            # Ask Ollama
            response = await ollama_client.chat(
                model=MODEL,
                messages=messages,
                tools=available_tools
            )

            # Process tool calls
            max_iterations = 5

            for _ in range(max_iterations):

                messages.append(response.message)

                tool_calls = response.message.tool_calls or []

                if not tool_calls:
                    break

                for tool_call in tool_calls:

                    tool_name = tool_call.function.name
                    arguments = tool_call.function.arguments

                    print(f"\nCalling MCP tool: {tool_name}")
                    print(f"Arguments: {arguments}")

                    # Execute tool through MCP
                    result = await session.call_tool(
                        tool_name,
                        arguments=arguments
                    )

                    # Extract text returned by MCP
                    result_text = "\n".join(
                        item.text
                        for item in result.content
                        if hasattr(item, "text")
                    )

                    if result.isError:
                        result_text = f"Tool execution failed: {result_text}"

                    print(f"Tool result: {result_text}")

                    # Send result back to Ollama
                    messages.append({
                        "role": "tool",
                        "tool_name": tool_name,
                        "content": result_text
                    })

                # Let Ollama process the tool results
                response = await ollama_client.chat(
                    model=MODEL,
                    messages=messages,
                    tools=available_tools
                )

            else:
                print("Maximum tool iterations reached.")

            print("\nSupport AI:")
            print(response.message.content)


if __name__ == "__main__":
    asyncio.run(main())
