# Support MCP Client

A Python client for connecting to the companion `support-mcp` server over MCP stdio transport.

The project includes two clients:

- `client.py` connects directly to the MCP server, lists its tools, resources, and prompts, and runs example calls.
- `client-ollama.py` connects to the MCP server and uses a local Ollama model to decide when to call MCP tools.

## Requirements

- Python 3.10 or newer
- The companion MCP server project located at:

  ```text
  ../support-mcp
  ```

  relative to this project directory
- The server project must contain:

  ```text
  ../support-mcp/server.py
  ../support-mcp/.venv/bin/python
  ```
- Internet access for installing Python dependencies
- Ollama installed and running only when using `client-ollama.py`
- The Ollama model `qwen2.5:3b` when using `client-ollama.py`

## Expected directory layout

The clients resolve the server path from the current working directory, so keep the projects as sibling directories:

```text
parent-directory/
├── support-client/
│   ├── client.py
│   ├── client-ollama.py
│   └── README.md
└── support-mcp/
    ├── server.py
    └── .venv/
```

## Installation

From the parent directory, create a virtual environment for this client:

```bash
cd /path/to/parent-directory/support-client
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install mcp
```

Install the dependencies required by the companion `support-mcp` project in its own environment according to that project's instructions. The client launches the server with `../support-mcp/.venv/bin/python`.

For the Ollama integration, install the Python client package in this environment:

```bash
python -m pip install ollama
```

Install and start Ollama, then download the configured model:

```bash
ollama pull qwen2.5:3b
```

If Ollama is not already running as a service, start it in another terminal:

```bash
ollama serve
```

## Run the direct MCP client

Activate the client environment and run the script from the `support-client` directory:

```bash
cd /path/to/parent-directory/support-client
source .venv/bin/activate
python client.py
```

The script initializes the MCP session and then demonstrates:

- listing available tools
- calling `get_order_status` for order `1`
- listing and reading MCP resources
- listing prompts
- retrieving the `analyze_customer_complaint` prompt

## Run the Ollama client

With Ollama running and the model downloaded:

```bash
cd /path/to/parent-directory/support-client
source .venv/bin/activate
python client-ollama.py
```

This client discovers the MCP tools, exposes them to `qwen2.5:3b`, executes model-requested tool calls through the MCP server, and prints the final support response.

## Configuration

The following values are currently defined directly in the Python files:

- MCP server location: `../support-mcp`
- MCP server entry point: `server.py`
- Ollama model: `qwen2.5:3b`

To use a different server location or model, update the corresponding constants and paths in the client script. Run the scripts from the project directory so the relative server path resolves correctly.

## Troubleshooting

### Server executable not found

Verify that the companion project has the expected virtual environment and entry point:

```bash
ls -l ../support-mcp/.venv/bin/python ../support-mcp/server.py
```

### `ModuleNotFoundError: mcp`

Activate this project's virtual environment and install the MCP package:

```bash
source .venv/bin/activate
python -m pip install mcp
```

### Ollama connection or model errors

Check that Ollama is available and the model is installed:

```bash
ollama list
ollama pull qwen2.5:3b
```

## Notes

- The clients communicate with the MCP server through standard input/output; the server is started automatically by each script.
- The example order IDs, resource URI, and prompt arguments are hard-coded demonstrations in the source files.
- There is currently no test suite, packaging metadata, or dependency lock file in this repository.
