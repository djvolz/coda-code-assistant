"""Core Agent implementation for Coda."""

import asyncio
import json
from typing import Any, Callable, Dict, List, Optional, Union
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

from coda.providers.base import BaseProvider, Message, Role, Tool, ToolCall
from coda.agents.function_tool import FunctionTool
from coda.agents.types import (
    RequiredAction, PerformedAction, FunctionCall, 
    RunResponse, RequiredActionType, PerformedActionType
)


class Agent:
    """
    An AI agent that can execute tasks using provided tools and instructions.
    
    The agent manages the interaction loop with the AI provider, executes tools,
    and handles the conversation flow.
    """
    
    def __init__(
        self,
        provider: BaseProvider,
        model: str,
        instructions: str = "You are a helpful assistant",
        tools: Optional[List[Union[Callable, FunctionTool]]] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        console: Optional[Console] = None,
        **kwargs,
    ):
        """
        Initialize an agent.
        
        Args:
            provider: The AI provider to use
            model: Model identifier 
            instructions: System instructions for the agent
            tools: List of tools the agent can use
            name: Optional agent name
            description: Optional agent description
            temperature: Sampling temperature
            max_tokens: Max tokens per response
            console: Rich console for output
            **kwargs: Additional provider-specific parameters
        """
        self.provider = provider
        self.model = model
        self.instructions = instructions
        self.tools = tools or []
        self.name = name or "Agent"
        self.description = description
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.console = console or Console()
        self.kwargs = kwargs
        
        # Process tools
        self._function_tools: List[FunctionTool] = self._process_tools()
        self._tool_map: Dict[str, FunctionTool] = {
            tool.name: tool for tool in self._function_tools
        }
    
    def _process_tools(self) -> List[FunctionTool]:
        """Convert all tools to FunctionTool format."""
        function_tools = []
        
        for tool in self.tools:
            if isinstance(tool, FunctionTool):
                function_tools.append(tool)
            elif callable(tool):
                # Must be decorated with @tool
                try:
                    function_tools.append(FunctionTool.from_callable(tool))
                except ValueError:
                    self.console.print(f"[yellow]Warning: {tool.__name__} is not decorated with @tool, skipping[/yellow]")
        
        return function_tools
    
    def _get_provider_tools(self) -> List[Tool]:
        """Convert FunctionTools to provider Tool format."""
        provider_tools = []
        
        for func_tool in self._function_tools:
            provider_tool = Tool(
                name=func_tool.name,
                description=func_tool.description,
                parameters=func_tool.parameters
            )
            provider_tools.append(provider_tool)
        
        return provider_tools
    
    async def run_async(
        self,
        input: str,
        messages: Optional[List[Message]] = None,
        max_steps: int = 10,
        on_fulfilled_action: Optional[Callable[[RequiredAction, PerformedAction], None]] = None,
        **kwargs,
    ) -> RunResponse:
        """
        Run the agent asynchronously.
        
        Args:
            input: User input message
            messages: Optional message history
            max_steps: Maximum tool execution steps
            on_fulfilled_action: Callback for completed actions
            **kwargs: Additional parameters
            
        Returns:
            RunResponse with final result
        """
        # Initialize messages if not provided
        if messages is None:
            messages = []
            # Add system message with instructions
            if self.instructions:
                messages.append(Message(role=Role.SYSTEM, content=self.instructions))
        
        # Add user message
        messages.append(Message(role=Role.USER, content=input))
        
        # Get provider tools
        provider_tools = self._get_provider_tools()
        
        # Check if model supports tools
        model_info = next((m for m in self.provider.list_models() if m.id == self.model), None)
        supports_tools = model_info and model_info.supports_functions and provider_tools
        
        # Main execution loop
        step_count = 0
        final_response = None
        
        while step_count < max_steps:
            try:
                # Make request to provider
                if supports_tools:
                    response = await asyncio.to_thread(
                        self.provider.chat,
                        messages=messages,
                        model=self.model,
                        temperature=self.temperature,
                        max_tokens=self.max_tokens,
                        tools=provider_tools,
                        **self.kwargs
                    )
                else:
                    # Fallback to regular chat
                    response = await asyncio.to_thread(
                        self.provider.chat,
                        messages=messages,
                        model=self.model,
                        temperature=self.temperature,
                        max_tokens=self.max_tokens,
                        **self.kwargs
                    )
                
                # Check for tool calls
                if response.tool_calls:
                    # Display response if any
                    if response.content:
                        self._print_response(response.content)
                    # Add assistant message with tool calls
                    messages.append(Message(
                        role=Role.ASSISTANT,
                        content=response.content or "",
                        tool_calls=response.tool_calls
                    ))
                    
                    # Handle tool calls
                    performed_actions = await self._handle_tool_calls(
                        response.tool_calls, 
                        on_fulfilled_action
                    )
                    
                    # Add tool results to messages
                    for action in performed_actions:
                        messages.append(Message(
                            role=Role.TOOL,
                            content=action.function_call_output,
                            tool_call_id=action.action_id
                        ))
                    
                    step_count += 1
                    # Continue loop to get final response
                else:
                    # No tool calls, we're done
                    if response.content:
                        self._print_response(response.content)
                        messages.append(Message(
                            role=Role.ASSISTANT,
                            content=response.content
                        ))
                    final_response = response
                    break
                    
            except Exception as e:
                error_msg = f"Error during agent execution: {str(e)}"
                self.console.print(f"[red]{error_msg}[/red]")
                final_response = type('obj', (object,), {
                    'content': error_msg,
                    'model': self.model
                })
                break
        
        if step_count >= max_steps:
            self.console.print(f"[yellow]Reached maximum steps ({max_steps})[/yellow]")
        
        # Return response
        return RunResponse(
            session_id=None,
            data={
                "content": final_response.content if final_response else "",
                "model": self.model,
                "messages": messages
            }
        )
    
    def run(self, input: str, **kwargs) -> RunResponse:
        """Synchronous wrapper for run_async."""
        try:
            loop = asyncio.get_running_loop()
            # We're already in an event loop, can't use run_until_complete
            # This shouldn't happen in normal usage
            raise RuntimeError("Cannot call synchronous run() from within an async context. Use run_async() instead.")
        except RuntimeError:
            # No event loop running, create one
            return asyncio.run(self.run_async(input, **kwargs))
    
    async def _handle_tool_calls(
        self,
        tool_calls: List[ToolCall],
        on_fulfilled_action: Optional[Callable] = None
    ) -> List[PerformedAction]:
        """Handle tool calls from the AI."""
        performed_actions = []
        
        self.console.print("\n[dim]Executing tools...[/dim]")
        
        for tool_call in tool_calls:
            # Create required action
            required_action = RequiredAction.from_tool_call(tool_call)
            
            # Show execution
            self._print_tool_execution(tool_call)
            
            # Execute tool
            performed_action = await self._execute_tool_call(
                tool_call, 
                required_action.action_id
            )
            
            if performed_action:
                performed_actions.append(performed_action)
                
                # Show result
                self._print_tool_result(performed_action)
                
                # Callback if provided
                if on_fulfilled_action:
                    on_fulfilled_action(required_action, performed_action)
        
        return performed_actions
    
    async def _execute_tool_call(
        self, 
        tool_call: ToolCall, 
        action_id: str
    ) -> Optional[PerformedAction]:
        """Execute a single tool call."""
        try:
            # Get the tool
            tool = self._tool_map.get(tool_call.name)
            if not tool:
                return PerformedAction(
                    action_id=action_id,
                    performed_action_type=PerformedActionType.FUNCTION_CALLING,
                    function_call_output=f"Error: Tool '{tool_call.name}' not found"
                )
            
            # Execute
            result = await tool.execute(tool_call.arguments)
            
            # Format result
            if isinstance(result, dict):
                output = json.dumps(result, indent=2)
            elif not isinstance(result, str):
                output = str(result)
            else:
                output = result
            
            return PerformedAction(
                action_id=action_id,
                performed_action_type=PerformedActionType.FUNCTION_CALLING,
                function_call_output=output
            )
            
        except Exception as e:
            return PerformedAction(
                action_id=action_id,
                performed_action_type=PerformedActionType.FUNCTION_CALLING,
                function_call_output=f"Error executing tool: {str(e)}"
            )
    
    def _print_response(self, content: str):
        """Print AI response."""
        self.console.print(f"\n[bold cyan]{self.name}:[/bold cyan] {content}")
    
    def _print_tool_execution(self, tool_call: ToolCall):
        """Print tool execution info."""
        self.console.print(f"\n[cyan]→ Running tool:[/cyan] {tool_call.name}")
        if tool_call.arguments:
            args_str = json.dumps(tool_call.arguments, indent=2)
            self.console.print(Panel(
                Syntax(args_str, "json", theme="monokai"),
                title="[cyan]Arguments[/cyan]",
                expand=False
            ))
    
    def _print_tool_result(self, action: PerformedAction):
        """Print tool result."""
        if "Error" in action.function_call_output:
            self.console.print(f"[red]✗ Error:[/red] {action.function_call_output}")
        else:
            self.console.print(f"[green]✓ Result:[/green]")
            # Try to format as JSON
            try:
                result_json = json.loads(action.function_call_output)
                self.console.print(Panel(
                    Syntax(json.dumps(result_json, indent=2), "json", theme="monokai"),
                    expand=False
                ))
            except:
                self.console.print(Panel(action.function_call_output, expand=False))
    
    def as_tool(
        self,
        tool_name: Optional[str] = None,
        tool_description: Optional[str] = None
    ) -> FunctionTool:
        """
        Convert this agent to a tool that can be used by other agents.
        
        Args:
            tool_name: Optional custom name
            tool_description: Optional custom description
            
        Returns:
            FunctionTool representing this agent
        """
        from coda.agents.decorators import tool
        
        name = tool_name or self.name or "run_sub_agent"
        description = tool_description or self.description or "Run a sub-agent"
        
        # Create wrapper function
        @tool(name=name, description=description)
        async def agent_wrapper(input: str, **kwargs) -> str:
            """Execute this agent with the given input."""
            response = await self.run_async(input=input, **kwargs)
            return response.content
        
        return FunctionTool.from_callable(agent_wrapper)