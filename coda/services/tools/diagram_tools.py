"""
Diagram rendering tool using the diagram-renderer library.

This tool provides diagram rendering capabilities for Mermaid, PlantUML, and Graphviz diagrams.
"""

from pathlib import Path
from typing import Any

from diagram_renderer import DiagramRenderer

from .base import BaseTool, ToolParameter, ToolParameterType, ToolResult, ToolSchema, tool_registry


class RenderDiagramTool(BaseTool):
    """Tool for rendering diagrams using diagram-renderer."""

    def __init__(self):
        super().__init__()
        self.renderer = DiagramRenderer()

    def get_schema(self) -> ToolSchema:
        return ToolSchema(
            name="render_diagram",
            description="Render diagrams from Mermaid, PlantUML, or Graphviz code",
            category="visualization",
            parameters={
                "code": ToolParameter(
                    type=ToolParameterType.STRING,
                    description="Diagram code (Mermaid, PlantUML, or Graphviz/DOT)",
                    required=True,
                ),
                "output_path": ToolParameter(
                    type=ToolParameterType.STRING,
                    description="Optional path to save the HTML output",
                    required=False,
                ),
                "return_html": ToolParameter(
                    type=ToolParameterType.BOOLEAN,
                    description="Return the HTML content in the result",
                    default=True,
                    required=False,
                ),
            },
        )

    async def execute(self, arguments: dict[str, Any]) -> ToolResult:
        code = arguments["code"]
        output_path = arguments.get("output_path")
        return_html = arguments.get("return_html", True)

        try:
            # Detect diagram type
            diagram_type = self.renderer.detect_diagram_type(code)

            # Render the diagram
            html_content = self.renderer.render_diagram_auto(code)

            if not html_content:
                return ToolResult(
                    success=False,
                    error="Failed to render diagram - no valid diagram detected",
                    tool="render_diagram",
                )

            # Save to file if requested
            if output_path:
                path = Path(output_path)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(html_content)

            # Prepare result
            result = {
                "diagram_type": diagram_type if diagram_type else "auto-detected",
                "saved_to": str(path) if output_path else None,
            }

            if return_html and not output_path:
                # Only return HTML if no output path specified
                result["html"] = html_content
            elif output_path:
                result["message"] = f"Diagram saved to {output_path}"

            return ToolResult(
                success=True,
                result=result,
                tool="render_diagram",
                metadata={
                    "diagram_type": diagram_type,
                    "html_size": len(html_content),
                },
            )

        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Failed to render diagram: {str(e)}",
                tool="render_diagram",
            )


# Register the diagram tool
tool_registry.register(RenderDiagramTool())
