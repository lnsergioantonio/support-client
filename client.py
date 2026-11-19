
import asyncio
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


# Locate the MCP server project
server_project = Path("../support-mcp").resolve()

server_params = StdioServerParameters(
    command=str(server_project / ".venv/bin/python"),
    args=[str(server_project / "server.py")]
)


async def main():

    # Start the server and establish communication
    async with stdio_client(server_params) as (read, write):

        async with ClientSession(read, write) as session:

            # Initialize MCP connection
            await session.initialize()

            print("Connected to Support MCP!")

            # Discover available tools
            tools = await session.list_tools()

            print("\nAvailable tools:")
            for tool in tools.tools:
                print(f"- {tool.name}: {tool.description}")

            # Call a tool
            result = await session.call_tool(
                "get_order_status",
                arguments={"order_id": 1}
            )

            print("\nTool result:")
            for content in result.content:
                if hasattr(content, "text"):
                    print(content.text)

            # Discover resources
            resources = await session.list_resources()

            print("\nAvailable resources:")
            for resource in resources.resources:
                print(f"- {resource.uri}")

            # Read a resource
            resource_result = await session.read_resource(
                "support://orders/123"
            )

            print("\nResource result:")
            for content in resource_result.contents:
                if hasattr(content, "text"):
                    print(content.text)

            # Discover prompts
            prompts = await session.list_prompts()

            print("\nAvailable prompts:")
            for prompt in prompts.prompts:
                print(f"- {prompt.name}")

            # Retrieve a prompt
            prompt_result = await session.get_prompt(
                "analyze_customer_complaint",
                arguments={
                    "customer_name": "John",
                    "complaint_text": "My order arrived damaged.",
                    "order_id": "123"
                }
            )

            print("\nPrompt result:")
            for message in prompt_result.messages:
                print(message.content.text)


if __name__ == "__main__":
    asyncio.run(main())
