"""Web UI command for launching Streamlit interface."""

import subprocess
import sys
from pathlib import Path

import click
from rich.panel import Panel

from coda.services.config import get_config_service

# Get themed console
config_service = get_config_service()
console = config_service.theme_manager.get_console()
theme = config_service.theme_manager.get_console_theme()


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
        console.print(f"[{theme.error}]Error loading configuration: {e}[/{theme.error}]")
        sys.exit(1)

    console.print(
        Panel(
            f"[{theme.success}]Starting Coda Web UI on http://{host}:{port}[/{theme.success}]\n"
            f"[{theme.dim}]Press Ctrl+C to stop the server[/{theme.dim}]",
            title="Web UI",
            border_style=theme.panel_border,
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
        console.print(f"\n[{theme.warning}]Web UI stopped by user[/{theme.warning}]")
    except subprocess.CalledProcessError as e:
        console.print(f"[{theme.error}]Error running web UI: {e}[/{theme.error}]")
        sys.exit(1)


if __name__ == "__main__":
    web()
