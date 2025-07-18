"""Claude Code provider implementation using Claude CLI tool."""

import asyncio
import json
import os
import shutil
import subprocess
from collections.abc import AsyncIterator, Iterator
from typing import Any

from .base import (
    BaseProvider,
    ChatCompletion,
    ChatCompletionChunk,
    Message,
    Model,
    Role,
    Tool,
    ToolCall,
)


class ClaudeCodeProvider(BaseProvider):
    """Claude Code provider using Claude CLI tool."""

    def __init__(self, command: str | None = None, **kwargs):
        """
        Initialize Claude Code provider.

        Args:
            command: Path to claude CLI command (defaults to 'claude')
            **kwargs: Additional provider settings
        """
        super().__init__(**kwargs)
        self.command = command or os.environ.get("CLAUDE_CODE_COMMAND", "claude")
        self._cached_model_info: Model | None = None
        
        # Verify command exists
        if not shutil.which(self.command):
            raise ValueError(
                f"Claude CLI command '{self.command}' not found. "
                "Please install Claude Code CLI from https://claude.ai/cli"
            )

    @property
    def name(self) -> str:
        """Provider name."""
        return "claude-code"

    def _filter_system_prompt(self, messages: list[Message]) -> tuple[str | None, list[Message]]:
        """
        Extract system prompt and filter messages.
        
        Returns:
            Tuple of (system_prompt, filtered_messages)
        """
        system_prompt = None
        filtered_messages = []
        
        for message in messages:
            if message.role == Role.SYSTEM:
                # Combine multiple system messages if present
                if system_prompt:
                    system_prompt += "\n\n" + message.content
                else:
                    system_prompt = message.content
            else:
                filtered_messages.append(message)
        
        # Filter out Coda-specific sections from system prompt
        if system_prompt:
            # Remove Extensions section since Claude Code has its own tools
            if "# Extensions" in system_prompt:
                parts = system_prompt.split("# Extensions")
                if len(parts) > 1:
                    # Find the next section or end
                    after_extensions = parts[1]
                    next_section_idx = after_extensions.find("\n# ")
                    if next_section_idx > 0:
                        # Keep everything before Extensions and after next section
                        system_prompt = parts[0].rstrip() + after_extensions[next_section_idx:]
                    else:
                        # No next section, just remove Extensions to end
                        system_prompt = parts[0].rstrip()
        
        return system_prompt, filtered_messages

    def _convert_messages_to_claude_format(self, messages: list[Message]) -> list[dict[str, Any]]:
        """Convert messages to Claude CLI format."""
        claude_messages = []
        
        for message in messages:
            content_parts = []
            
            # Handle text content
            if message.content:
                content_parts.append({
                    "type": "text",
                    "text": message.content
                })
            
            # Handle tool calls (assistant requesting tool use)
            if message.tool_calls:
                for tool_call in message.tool_calls:
                    content_parts.append({
                        "type": "tool_use",
                        "id": tool_call.id,
                        "name": tool_call.name,
                        "input": tool_call.arguments
                    })
            
            # Handle tool results
            if message.role == Role.TOOL and message.tool_call_id:
                # Tool results need special handling
                claude_messages.append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": message.tool_call_id,
                        "content": message.content
                    }]
                })
                continue
            
            # Map roles
            role = "user" if message.role == Role.USER else "assistant"
            
            claude_messages.append({
                "role": role,
                "content": content_parts if content_parts else [{"type": "text", "text": message.content or ""}]
            })
        
        return claude_messages

    def _parse_claude_response(self, output: str) -> tuple[str, dict[str, Any] | None]:
        """
        Parse Claude CLI JSON output.
        
        Returns:
            Tuple of (content, usage)
        """
        content_parts = []
        usage = None
        
        # First, try to parse as a single JSON array
        try:
            json_data = json.loads(output.strip())
            if isinstance(json_data, list):
                # Handle as array of responses
                for data in json_data:
                    if isinstance(data, dict) and data.get("type") == "assistant":
                        # Extract text content from assistant messages
                        if message := data.get("message"):
                            if message_content := message.get("content"):
                                if isinstance(message_content, list):
                                    for item in message_content:
                                        if isinstance(item, dict) and item.get("type") == "text":
                                            content_parts.append(item.get("text", ""))
                                elif isinstance(message_content, str):
                                    content_parts.append(message_content)
                            
                            # Extract usage info
                            if usage_info := message.get("usage"):
                                usage = {
                                    "prompt_tokens": usage_info.get("input_tokens", 0),
                                    "completion_tokens": usage_info.get("output_tokens", 0),
                                    "total_tokens": (
                                        usage_info.get("input_tokens", 0) + 
                                        usage_info.get("output_tokens", 0)
                                    )
                                }
                    
                    elif isinstance(data, dict) and data.get("type") == "result":
                        # Additional usage info might be in result
                        if not usage and (usage_info := data.get("usage")):
                            usage = {
                                "prompt_tokens": usage_info.get("input_tokens", 0),
                                "completion_tokens": usage_info.get("output_tokens", 0),
                                "total_tokens": (
                                    usage_info.get("input_tokens", 0) + 
                                    usage_info.get("output_tokens", 0)
                                )
                            }
        except json.JSONDecodeError:
            # Fall back to line-by-line parsing
            for line in output.strip().split('\n'):
                if not line.strip():
                    continue
                    
                try:
                    data = json.loads(line)
                    
                    # Handle different response types
                    if isinstance(data, dict) and data.get("type") == "assistant":
                        # Extract text content from assistant messages
                        if message := data.get("message"):
                            if message_content := message.get("content"):
                                if isinstance(message_content, list):
                                    for item in message_content:
                                        if isinstance(item, dict) and item.get("type") == "text":
                                            content_parts.append(item.get("text", ""))
                                elif isinstance(message_content, str):
                                    content_parts.append(message_content)
                            
                            # Extract usage info
                            if usage_info := message.get("usage"):
                                usage = {
                                    "prompt_tokens": usage_info.get("input_tokens", 0),
                                    "completion_tokens": usage_info.get("output_tokens", 0),
                                    "total_tokens": (
                                        usage_info.get("input_tokens", 0) + 
                                        usage_info.get("output_tokens", 0)
                                    )
                                }
                    
                    elif isinstance(data, dict) and data.get("type") == "result":
                        # Additional usage info might be in result
                        if not usage and (usage_info := data.get("usage")):
                            usage = {
                                "prompt_tokens": usage_info.get("input_tokens", 0),
                                "completion_tokens": usage_info.get("output_tokens", 0),
                                "total_tokens": (
                                    usage_info.get("input_tokens", 0) + 
                                    usage_info.get("output_tokens", 0)
                                )
                            }
                            
                except json.JSONDecodeError:
                    # Skip lines that aren't valid JSON
                    continue
        
        content = "\n\n".join(content_parts)
        
        if not content:
            # If no content found, provide a more informative error
            if os.environ.get("CODA_DEBUG"):
                print(f"No content extracted from output: {output}")
            content = "No response content found"
            
        return content, usage

    def _execute_claude_cli(
        self,
        messages: list[dict[str, Any]],
        system_prompt: str | None = None,
        **kwargs
    ) -> str:
        """Execute Claude CLI and return output."""
        # Prepare command
        cmd = [self.command]
        
        # Add messages as positional argument
        messages_json = json.dumps(messages)
        cmd.extend(["-p", messages_json])
        
        # Add system prompt if provided
        if system_prompt:
            cmd.extend(["--system-prompt", system_prompt])
        
        # Force JSON output
        cmd.extend(["--output-format", "json", "--verbose"])
        
        # Debug logging
        if os.environ.get("CODA_DEBUG"):
            print(f"Claude Code CLI command: {' '.join(cmd)}")
            print(f"Messages JSON: {messages_json}")
            if system_prompt:
                print(f"System prompt: {system_prompt}")
        
        # Execute command
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            
            # Debug output
            if os.environ.get("CODA_DEBUG"):
                print(f"Claude CLI output: {result.stdout}")
                
            return result.stdout
        except subprocess.CalledProcessError as e:
            error_msg = f"Claude CLI failed: {e.stderr or e.stdout or str(e)}"
            if os.environ.get("CODA_DEBUG"):
                print(f"Claude CLI error: {error_msg}")
            raise RuntimeError(error_msg) from e

    async def _execute_claude_cli_async(
        self,
        messages: list[dict[str, Any]],
        system_prompt: str | None = None,
        **kwargs
    ) -> str:
        """Execute Claude CLI asynchronously and return output."""
        # Prepare command
        cmd = [self.command]
        
        # Add messages as positional argument
        cmd.extend(["-p", json.dumps(messages)])
        
        # Add system prompt if provided
        if system_prompt:
            cmd.extend(["--system-prompt", system_prompt])
        
        # Force JSON output
        cmd.extend(["--output-format", "json", "--verbose"])
        
        # Execute command asynchronously
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await proc.communicate()
        
        if proc.returncode != 0:
            error_msg = f"Claude CLI failed: {stderr.decode() or stdout.decode()}"
            raise RuntimeError(error_msg)
        
        return stdout.decode()

    def chat(
        self,
        messages: list[Message],
        model: str,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        top_p: float | None = None,
        stop: str | list[str] | None = None,
        tools: list[Tool] | None = None,
        **kwargs,
    ) -> ChatCompletion:
        """Send chat completion request via Claude CLI."""
        # Extract system prompt and filter messages
        system_prompt, filtered_messages = self._filter_system_prompt(messages)
        
        # Convert messages to Claude format
        claude_messages = self._convert_messages_to_claude_format(filtered_messages)
        
        # Execute CLI command
        # Note: Claude CLI may not support all parameters like temperature, max_tokens, etc.
        # We'll pass them but the CLI will use its own defaults
        output = self._execute_claude_cli(
            claude_messages,
            system_prompt=system_prompt
        )
        
        # Parse response
        content, usage = self._parse_claude_response(output)
        
        return ChatCompletion(
            content=content,
            model=model,
            finish_reason="stop",
            usage=usage,
            metadata={"provider": "claude-code"}
        )

    def chat_stream(
        self,
        messages: list[Message],
        model: str,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        top_p: float | None = None,
        stop: str | list[str] | None = None,
        tools: list[Tool] | None = None,
        **kwargs,
    ) -> Iterator[ChatCompletionChunk]:
        """
        Stream chat completion response.
        
        Note: Claude CLI doesn't support streaming, so we return the full response as a single chunk.
        """
        # Get full response
        completion = self.chat(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            stop=stop,
            tools=tools,
            **kwargs
        )
        
        # Return as a single chunk
        yield ChatCompletionChunk(
            content=completion.content,
            model=model,
            finish_reason=completion.finish_reason,
            usage=completion.usage,
            metadata=completion.metadata
        )

    async def achat(
        self,
        messages: list[Message],
        model: str,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        top_p: float | None = None,
        stop: str | list[str] | None = None,
        **kwargs,
    ) -> ChatCompletion:
        """Async version of chat."""
        # Extract system prompt and filter messages
        system_prompt, filtered_messages = self._filter_system_prompt(messages)
        
        # Convert messages to Claude format
        claude_messages = self._convert_messages_to_claude_format(filtered_messages)
        
        # Execute CLI command asynchronously
        # Note: Claude CLI may not support all parameters like temperature, max_tokens, etc.
        output = await self._execute_claude_cli_async(
            claude_messages,
            system_prompt=system_prompt
        )
        
        # Parse response
        content, usage = self._parse_claude_response(output)
        
        return ChatCompletion(
            content=content,
            model=model,
            finish_reason="stop",
            usage=usage,
            metadata={"provider": "claude-code"}
        )

    async def achat_stream(
        self,
        messages: list[Message],
        model: str,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        top_p: float | None = None,
        stop: str | list[str] | None = None,
        **kwargs,
    ) -> AsyncIterator[ChatCompletionChunk]:
        """
        Async version of chat_stream.
        
        Note: Claude CLI doesn't support streaming, so we return the full response as a single chunk.
        """
        # Get full response
        completion = await self.achat(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            stop=stop,
            **kwargs
        )
        
        # Return as a single chunk
        yield ChatCompletionChunk(
            content=completion.content,
            model=model,
            finish_reason=completion.finish_reason,
            usage=completion.usage,
            metadata=completion.metadata
        )

    def list_models(self) -> list[Model]:
        """
        List available models by querying Claude CLI.
        
        Falls back to a default if the CLI doesn't support model listing.
        """
        # Return cached model info if available
        if self._cached_model_info:
            return [self._cached_model_info]
            
        try:
            # Try to get available models from Claude CLI
            # First, let's see if there's a command to list models
            result = subprocess.run(
                [self.command, "--help"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            # Check if there's a models or list-models command
            help_text = result.stdout.lower()
            
            # Check if there's a list-models or models command
            if "list-models" in help_text or "models" in help_text:
                # Try to run the models command
                try:
                    models_result = subprocess.run(
                        [self.command, "models"],  # or "list-models"
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    
                    if models_result.returncode == 0 and models_result.stdout:
                        # Parse the models output
                        # This would need to be adapted based on actual CLI output format
                        # For now, we'll fall through to the test query method
                        pass
                except Exception:
                    pass
            
            # For now, we'll check what model the CLI is actually using
            # by doing a minimal query
            test_messages = [{"role": "user", "content": [{"type": "text", "text": "Hi"}]}]
            
            try:
                output = self._execute_claude_cli(
                    test_messages,
                    system_prompt="Reply with just the word 'ok'"
                )
                
                # Parse the output to see what model was used
                model_id = "claude-code-default"  # Default fallback
                model_name = "Claude (via Claude Code)"
                
                # Try to extract model info from the response
                for line in output.strip().split('\n'):
                    if line.strip():
                        try:
                            data = json.loads(line)
                            if data.get("type") == "assistant":
                                if message := data.get("message"):
                                    # Check if model info is in the message
                                    if model_info := message.get("model"):
                                        model_id = model_info
                                        model_name = f"{model_info} (via Claude Code)"
                                        break
                        except json.JSONDecodeError:
                            continue
                
                # Cache the model info
                self._cached_model_info = Model(
                        id=model_id,
                        name=model_name,
                        provider="claude-code",
                        context_length=200_000,  # Claude Code's typical context limit
                        max_tokens=8192,
                        supports_streaming=False,  # CLI doesn't support streaming
                        supports_functions=False,  # We don't pass tools to CLI
                        metadata={
                            "description": "Claude model via Claude Code CLI subscription",
                            "cli_required": True,
                            "auth_method": "Claude Code subscription",
                            "detected_model": model_id != "claude-code-default"
                        }
                    )
                
                return [self._cached_model_info]
                
            except Exception:
                # If we can't query the CLI, return a generic model
                pass
                
        except Exception:
            # If anything fails, return a generic model
            pass
        
        # Fallback to a generic model entry
        return [
            Model(
                id="claude-code-default",
                name="Claude (via Claude Code)",
                provider="claude-code",
                context_length=200_000,  # Claude Code's typical context limit
                max_tokens=8192,
                supports_streaming=False,
                supports_functions=False,
                metadata={
                    "description": "Claude model via Claude Code CLI subscription",
                    "cli_required": True,
                    "auth_method": "Claude Code subscription",
                    "note": "Exact model determined at runtime by Claude CLI"
                }
            )
        ]

    def validate_model(self, model: str) -> bool:
        """Validate if the model is supported."""
        # Claude Code CLI accepts any model string, it will use whatever is configured
        # We'll accept common model patterns
        return (
            model == "claude-code-default" or
            model == "default" or
            "claude" in model.lower() or
            # Just accept any model string and let the CLI handle it
            True
        )

    def __repr__(self) -> str:
        """String representation."""
        return f"ClaudeCodeProvider(command='{self.command}')"