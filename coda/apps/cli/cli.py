"""Main CLI entry point with command groups."""

import click

from coda.__version__ import __version__

from .web_command import web as web_command


@click.group(invoke_without_command=True)
@click.pass_context
@click.version_option(version=__version__, prog_name="coda")
def cli(ctx):
    """Coda - Multi-provider AI code assistant.

    Run without arguments to start interactive chat mode.
    """
    if ctx.invoked_subcommand is None:
        ctx.invoke(chat)


@cli.command()
@click.option("--provider", "-p", help="LLM provider to use (oci_genai, ollama, litellm)")
@click.option("--model", "-m", help="Model to use")
@click.option("--debug", is_flag=True, help="Enable debug output")
@click.option("--one-shot", help="Execute a single prompt and exit")
@click.option(
    "--mode",
    type=click.Choice(["general", "code", "debug", "explain", "review", "refactor", "plan"]),
    default="general",
    help="Initial developer mode",
)
@click.option("--no-save", is_flag=True, help="Disable auto-saving of conversations")
@click.option("--resume", is_flag=True, help="Resume the most recent session")
def chat(provider, model, debug, one_shot, mode, no_save, resume):
    """Start an interactive chat session."""
    from .main import main

    main(
        provider, model, debug, one_shot, False, mode, no_save, resume
    )  # False for removed basic flag


cli.add_command(web_command, name="web")


if __name__ == "__main__":
    cli()
