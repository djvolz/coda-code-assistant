"""CLI command for managing OCI tool support cache."""

import click
from rich.console import Console
from rich.table import Table

from coda.base.providers.oci_genai import OCIGenAIProvider
from coda.base.providers.oci_tool_tester import OCIToolTester


@click.command()
@click.option('--clear', is_flag=True, help='Clear the tool support cache')
@click.option('--stats', is_flag=True, help='Show cache statistics')
@click.option('--test', help='Test a specific model')
def tool_cache(clear, stats, test):
    """Manage OCI GenAI tool support cache."""
    console = Console()
    tester = OCIToolTester()
    
    if clear:
        tester.clear_cache()
        console.print("[green]✓ Tool support cache cleared[/green]")
        return
    
    if stats:
        cache_stats = tester.get_cache_stats()
        console.print("\n[bold]OCI Tool Support Cache Statistics[/bold]")
        console.print(f"Cache file: {cache_stats['cache_file']}")
        console.print(f"Total cached: {cache_stats['total_cached']} models")
        console.print(f"Working: {cache_stats['working']} models")
        console.print(f"Partial support: {cache_stats['partial_support']} models") 
        console.print(f"Not working: {cache_stats['not_working']} models")
        return
    
    if test:
        console.print(f"\n[bold]Testing model: {test}[/bold]")
        try:
            provider = OCIGenAIProvider()
            result = tester._test_model(test, provider)
            
            console.print("\n[bold]Test Results:[/bold]")
            if result['tools_work']:
                console.print(f"✅ Tools work: Yes")
                if result['streaming_tools']:
                    console.print(f"✅ Streaming tools: Yes")
                else:
                    console.print(f"⚠️  Streaming tools: No")
            else:
                console.print(f"❌ Tools work: No")
                if result.get('error'):
                    console.print(f"   Error: {result['error']}")
            
        except Exception as e:
            console.print(f"[red]❌ Test failed: {e}[/red]")
        return
    
    # Default: show cache contents
    cache = tester._cache
    if not cache:
        console.print("[yellow]Tool support cache is empty[/yellow]")
        return
    
    table = Table(title="OCI Tool Support Cache")
    table.add_column("Model", style="cyan")
    table.add_column("Tools", style="green")
    table.add_column("Streaming", style="yellow")
    table.add_column("Status", style="magenta")
    table.add_column("Test Date")
    
    for model_id, info in sorted(cache.items()):
        tools = "✅" if info.get('tools_work') else "❌"
        streaming = "✅" if info.get('streaming_tools') else "❌"
        
        if info.get('error'):
            status = f"Error: {info['error']}"
        elif info.get('tools_work'):
            if info.get('streaming_tools'):
                status = "Fully working"
            else:
                status = "Partial (non-streaming)"
        else:
            status = "Not working"
        
        test_date = info.get('test_date', 'Unknown')
        if test_date != 'Unknown':
            test_date = test_date.split('T')[0]  # Just show date
        
        table.add_row(model_id, tools, streaming, status, test_date)
    
    console.print(table)


if __name__ == "__main__":
    tool_cache()