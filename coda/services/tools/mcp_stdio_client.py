"""
MCP client that communicates with servers via stdio (stdin/stdout).

This is the standard way MCP servers communicate, using JSON-RPC over stdio.
"""

import asyncio
import json
import logging
import subprocess
from typing import Any

logger = logging.getLogger(__name__)


class StdioMCPClient:
    """MCP client that communicates via stdio with a subprocess."""

    def __init__(self, command: str, args: list[str], env: dict[str, str] | None = None):
        self.command = command
        self.args = args
        self.env = env
        self.process: subprocess.Popen | None = None
        self.reader: asyncio.StreamReader | None = None
        self.writer: asyncio.StreamWriter | None = None
        self._request_id = 0
        self._pending_requests: dict[int, asyncio.Future] = {}
        self._reader_task: asyncio.Task | None = None
        self.tools: list[dict[str, Any]] = []

    def _next_id(self) -> int:
        """Get next request ID."""
        self._request_id += 1
        return self._request_id

    async def start(self) -> bool:
        """Start the MCP server subprocess and connect via stdio."""
        try:
            # Prepare environment
            import os

            env = os.environ.copy()
            if self.env:
                env.update(self.env)

            # Start the subprocess
            cmd = [self.command] + self.args
            logger.info(f"Starting MCP server: {' '.join(cmd)}")

            # Create subprocess with asyncio
            self.process = await asyncio.create_subprocess_exec(
                self.command,
                *self.args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )

            # Start reading responses
            self._reader_task = asyncio.create_task(self._read_responses())

            # Initialize the connection
            init_response = await self._send_request(
                "initialize",
                {
                    "protocolVersion": "2024-11-05",  # Use the current MCP version
                    "capabilities": {},
                    "clientInfo": {"name": "Coda MCP Client", "version": "1.0.0"},
                },
            )

            if "error" in init_response:
                logger.error(f"Failed to initialize MCP server: {init_response['error']}")
                await self.stop()
                return False

            logger.info(f"MCP server initialized: {init_response.get('result', {})}")
            return True

        except Exception as e:
            logger.error(f"Failed to start MCP server: {e}")
            return False

    async def _read_responses(self):
        """Read responses from the server's stdout."""
        if not self.process or not self.process.stdout:
            return

        while True:
            try:
                # Read line from stdout
                line = await self.process.stdout.readline()
                if not line:
                    break

                # Parse JSON-RPC response
                try:
                    response = json.loads(line.decode())

                    # Handle response
                    if "id" in response and response["id"] in self._pending_requests:
                        # This is a response to a request
                        future = self._pending_requests.pop(response["id"])
                        if not future.cancelled():
                            future.set_result(response)
                    else:
                        # This might be a notification or error
                        logger.debug(f"Received notification: {response}")

                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON from MCP server: {line}")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error reading from MCP server: {e}")
                break

    async def _send_request(
        self, method: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Send a request to the MCP server and wait for response."""
        if not self.process or not self.process.stdin:
            raise RuntimeError("MCP server not running")

        # Create request
        request_id = self._next_id()
        request = {"jsonrpc": "2.0", "id": request_id, "method": method}
        if params is not None:
            request["params"] = params

        # Create future for response
        future = asyncio.Future()
        self._pending_requests[request_id] = future

        try:
            # Send request
            request_line = json.dumps(request) + "\n"
            self.process.stdin.write(request_line.encode())
            await self.process.stdin.drain()

            # Wait for response with timeout
            response = await asyncio.wait_for(future, timeout=60.0)
            return response

        except TimeoutError:
            self._pending_requests.pop(request_id, None)
            logger.error(f"Timeout waiting for response to {method}")
            return {"error": {"code": -32000, "message": "Request timeout"}}
        except Exception as e:
            self._pending_requests.pop(request_id, None)
            logger.error(f"Error sending request {method}: {e}")
            return {"error": {"code": -32603, "message": str(e)}}

    async def list_tools(self) -> list[dict[str, Any]]:
        """List tools available on the MCP server."""
        response = await self._send_request("tools/list")

        if "result" in response and "tools" in response["result"]:
            self.tools = response["result"]["tools"]
            logger.info(f"Found {len(self.tools)} tools on MCP server")
            return self.tools
        elif "error" in response:
            logger.error(f"Error listing tools: {response['error']}")
            return []
        else:
            logger.error(f"Unexpected response: {response}")
            return []

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Call a tool on the MCP server."""
        response = await self._send_request(
            "tools/call", {"name": tool_name, "arguments": arguments}
        )

        if "result" in response:
            return response["result"]
        elif "error" in response:
            return {"error": response["error"].get("message", "Unknown error")}
        else:
            return {"error": "Unexpected response format"}

    async def stop(self):
        """Stop the MCP server process."""
        # Cancel reader task
        if self._reader_task:
            self._reader_task.cancel()
            try:
                await self._reader_task
            except asyncio.CancelledError:
                pass

        # Terminate process
        if self.process:
            try:
                self.process.terminate()
                await asyncio.wait_for(self.process.wait(), timeout=5.0)
            except TimeoutError:
                logger.warning("MCP server didn't stop gracefully, killing it")
                self.process.kill()
                await self.process.wait()

            self.process = None

        # Clear pending requests
        for future in self._pending_requests.values():
            if not future.done():
                future.cancel()
        self._pending_requests.clear()

    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop()
