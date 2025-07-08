#!/usr/bin/env python3
"""Interactive test of the agent system."""

import asyncio
from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel

from coda.configuration import get_config
from coda.providers import ProviderFactory
from coda.agents import Agent
from coda.agents.builtin_tools import get_builtin_tools


async def main():
    """Run interactive agent test."""
    console = Console()
    
    console.print(Panel.fit(
        "[bold cyan]Coda Agent Interactive Test[/bold cyan]\n"
        "Test the agent system with built-in tools",
        border_style="cyan"
    ))
    
    # Load configuration
    config = get_config()
    factory = ProviderFactory(config.to_dict())
    
    # Create provider
    provider = factory.create("oci_genai")
    
    # List available Cohere models
    models = [m for m in provider.list_models() if m.id.startswith("cohere.")]
    console.print("\n[cyan]Available Cohere models:[/cyan]")
    for i, model in enumerate(models, 1):
        console.print(f"  {i}. {model.id}")
    
    # Select model
    choice = Prompt.ask("Select model", default="1")
    try:
        model_idx = int(choice) - 1
        selected_model = models[model_idx].id
    except:
        selected_model = "cohere.command-r-plus"
    
    console.print(f"\n[green]Using model: {selected_model}[/green]")
    
    # Create agent with built-in tools
    agent = Agent(
        provider=provider,
        model=selected_model,
        instructions="""You are a helpful AI assistant with access to various tools.
Use tools when appropriate to help answer questions or complete tasks.
Be concise but informative in your responses.""",
        tools=get_builtin_tools(),
        name="Coda Assistant",
        temperature=0.3,
        console=console
    )
    
    # Show available tools
    console.print("\n[cyan]Available tools:[/cyan]")
    for tool in agent._function_tools:
        console.print(f"  • {tool.name}: {tool.description}")
    
    console.print("\n[dim]Type 'exit' to quit[/dim]\n")
    
    # Interactive loop
    while True:
        try:
            user_input = Prompt.ask("\n[bold cyan]You[/bold cyan]")
            
            if user_input.lower() in ['exit', 'quit', 'q']:
                break
            
            # Run agent with streaming
            response_content, messages = await agent.run_async_streaming(user_input)
            
            # Response is already printed by agent during streaming
            
        except KeyboardInterrupt:
            console.print("\n[yellow]Interrupted[/yellow]")
            break
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
    
    console.print("\n[green]Goodbye![/green]")


if __name__ == "__main__":
    asyncio.run(main())