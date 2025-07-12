"""Web UI command for launching Streamlit interface."""

import subprocess
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel

from coda.services.config import get_config_service

from .constants import PANEL_BORDER_STYLE

console = Console()


@click.command()
@click.option("--port", "-p", default=8501, help="Port to run the web server on")
@click.option("--host", "-h", default="localhost", help="Host to bind the web server to")
@click.option("--browser/--no-browser", default=True, help="Open browser automatically")
@click.option("--debug", is_flag=True, help="Run in debug mode")
def web(port: int, host: str, browser: bool, debug: bool):
    """Launch the Coda Assistant web interface."""
    try:
        get_config_service()  # Validate config loads successfully
    except Exception as e:
        console.print(f"[red]Error loading configuration: {e}[/red]")
        sys.exit(1)

    console.print(
        Panel(
            f"[green]Starting Coda Web UI on http://{host}:{port}[/green]\n"
            f"[dim]Press Ctrl+C to stop the server[/dim]",
            title="Web UI",
            border_style=PANEL_BORDER_STYLE,
        )
    )

    app_path = Path(__file__).parent.parent / "web" / "app.py"

    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(app_path),
        "--server.port",
        str(port),
        "--server.address",
        host,
    ]

    if not browser:
        cmd.extend(["--server.headless", "true"])

    if debug:
        cmd.extend(["--logger.level", "debug"])

    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        console.print("\n[yellow]Web UI stopped by user[/yellow]")
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Error running web UI: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    web()
