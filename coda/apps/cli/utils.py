"""Shared CLI utilities to eliminate code duplication."""

import asyncio
import time


async def simple_thinking_animation(
    task: asyncio.Task,
    console,
    message: str = "Thinking",
    theme_info: str = "",
    theme_bold: str = "",
    min_display_time: float = 0.8,
    spinner_style: str = "dots",
) -> None:
    """
    Simple thinking animation that shows status and cleans up properly.
    """

    start_time = time.time()

    # Build the status message with theming
    if theme_info and theme_bold:
        base_message = f"[{theme_info} {theme_bold}]{message}[/{theme_info} {theme_bold}]"
    else:
        base_message = message

    try:
        # Use console.status() for the spinner
        with console.status(base_message, spinner=spinner_style) as status:
            while not task.done():
                elapsed = time.time() - start_time

                # Update status text with elapsed time
                if theme_info and theme_bold:
                    status_text = f"[{theme_info} {theme_bold}]{message}... {elapsed:.1f}s[/{theme_info} {theme_bold}]"
                else:
                    status_text = f"{message}... {elapsed:.1f}s"

                status.update(status_text)
                await asyncio.sleep(0.1)

            # Ensure minimum display time
            final_elapsed = time.time() - start_time
            if final_elapsed < min_display_time:
                remaining = min_display_time - final_elapsed
                while remaining > 0:
                    if theme_info and theme_bold:
                        status_text = f"[{theme_info} {theme_bold}]{message}... {final_elapsed:.1f}s[/{theme_info} {theme_bold}]"
                    else:
                        status_text = f"{message}... {final_elapsed:.1f}s"

                    status.update(status_text)
                    await asyncio.sleep(0.1)
                    remaining -= 0.1
                    final_elapsed = time.time() - start_time

        # After status clears, show completion time on same line
        final_time = time.time() - start_time
        if theme_info and theme_bold:
            console.print(
                f"\r[{theme_info} {theme_bold}]⏱️  Completed in {final_time:.1f}s[/{theme_info} {theme_bold}]"
            )
        else:
            console.print(f"\r⏱️  Completed in {final_time:.1f}s")

    except Exception:
        raise
