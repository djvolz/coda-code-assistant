import click
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

console = Console()


@click.command()
@click.option('--provider', '-p', default='ollama', help='LLM provider to use')
@click.option('--model', '-m', help='Model to use')
@click.option('--debug', is_flag=True, help='Enable debug output')
@click.version_option(version='0.1.0', prog_name='coda')
def main(provider: str, model: str, debug: bool):
    """Coda - A multi-provider code assistant"""
    
    welcome_text = Text.from_markup(
        "[bold cyan]Coda[/bold cyan] - Code Assistant\n"
        "[dim]Multi-provider AI coding companion[/dim]"
    )
    
    console.print(Panel(welcome_text, title="Welcome", border_style="cyan"))
    console.print(f"\n[green]Provider:[/green] {provider}")
    if model:
        console.print(f"[green]Model:[/green] {model}")
    
    console.print("\n[yellow]Note:[/yellow] This is a placeholder. Full implementation coming soon!")
    

if __name__ == "__main__":
    main()