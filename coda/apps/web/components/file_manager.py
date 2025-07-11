"""File upload and download functionality for the web UI."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import streamlit as st

from coda.apps.web.utils.state import get_state_value


def render_file_upload_widget() -> list[dict[str, Any]] | None:
    """Render file upload widget and return uploaded files data."""
    st.subheader("📎 File Upload")

    uploaded_files = st.file_uploader(
        "Choose files to upload",
        accept_multiple_files=True,
        help="Upload files to include in your conversation context",
    )

    if uploaded_files:
        files_data = []
        for file in uploaded_files:
            file_data = {
                "name": file.name,
                "size": file.size,
                "type": file.type,
                "content": file.read(),
            }
            files_data.append(file_data)

        st.success(f"Uploaded {len(files_data)} file(s)")

        with st.expander("View uploaded files"):
            for file_data in files_data:
                col1, col2, col3 = st.columns([2, 1, 1])

                with col1:
                    st.write(f"**{file_data['name']}**")

                with col2:
                    st.write(f"Size: {format_file_size(file_data['size'])}")

                with col3:
                    st.write(f"Type: {file_data['type']}")

                if is_text_file(file_data["type"]):
                    with st.expander(f"Preview: {file_data['name']}"):
                        try:
                            content = file_data["content"].decode("utf-8")
                            st.code(content, language=get_language_from_filename(file_data["name"]))
                        except UnicodeDecodeError:
                            st.warning("Cannot preview binary file")

        return files_data

    return None


def render_file_download_section():
    """Render file download section."""
    st.subheader("💾 Download Options")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("📄 Download Chat History", use_container_width=True):
            download_chat_history()

    with col2:
        if st.button("📊 Download Session Data", use_container_width=True):
            download_session_data()


def download_chat_history():
    """Generate and offer chat history download."""
    messages = get_state_value("messages", [])

    if not messages:
        st.warning("No chat history to download")
        return

    # Create markdown format
    markdown_content = generate_markdown_history(messages)

    st.download_button(
        label="Download as Markdown",
        data=markdown_content,
        file_name=f"chat_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
        mime="text/markdown",
    )

    # Create JSON format
    json_content = json.dumps(messages, indent=2)

    st.download_button(
        label="Download as JSON",
        data=json_content,
        file_name=f"chat_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        mime="application/json",
    )


def download_session_data():
    """Generate and offer session data download."""
    session_manager = get_state_value("session_manager")
    if not session_manager:
        st.warning("Session manager not available")
        return

    try:
        sessions = session_manager.get_active_sessions()
        if not sessions:
            st.warning("No sessions to download")
            return

        # Create comprehensive session export
        export_data = []
        for session in sessions:
            messages = session_manager.get_messages(session.id)

            session_data = {
                "session": {
                    "id": session.id,
                    "name": session.name,
                    "provider": session.provider,
                    "model": session.model,
                    "created_at": session.created_at.isoformat(),
                    "updated_at": session.updated_at.isoformat() if session.updated_at else None,
                },
                "messages": [
                    {
                        "id": msg.id,
                        "role": msg.role,
                        "content": msg.content,
                        "timestamp": msg.timestamp.isoformat(),
                    }
                    for msg in messages
                ],
            }
            export_data.append(session_data)

        json_content = json.dumps(export_data, indent=2)

        st.download_button(
            label="Download All Sessions",
            data=json_content,
            file_name=f"coda_sessions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
        )

    except Exception as e:
        st.error(f"Error exporting sessions: {e}")


def generate_markdown_history(messages: list[dict[str, Any]]) -> str:
    """Generate markdown format chat history."""
    markdown = f"# Chat History\n\nExported: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"

    for i, message in enumerate(messages, 1):
        role = message["role"].title()
        content = message["content"]

        markdown += f"## Message {i} - {role}\n\n"

        if "```" in content:
            # Handle code blocks
            markdown += content + "\n\n"
        else:
            markdown += content + "\n\n"

        markdown += "---\n\n"

    return markdown


def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format."""
    if size_bytes == 0:
        return "0 B"

    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1

    return f"{size_bytes:.1f} {size_names[i]}"


def is_text_file(mime_type: str) -> bool:
    """Check if file type is text-based."""
    text_types = [
        "text/",
        "application/json",
        "application/xml",
        "application/javascript",
        "application/x-python-code",
    ]

    return any(mime_type.startswith(t) for t in text_types)


def get_language_from_filename(filename: str) -> str:
    """Get programming language from filename extension."""
    extension_map = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".java": "java",
        ".cpp": "cpp",
        ".c": "c",
        ".cs": "csharp",
        ".go": "go",
        ".rs": "rust",
        ".php": "php",
        ".rb": "ruby",
        ".swift": "swift",
        ".kt": "kotlin",
        ".scala": "scala",
        ".sh": "bash",
        ".ps1": "powershell",
        ".sql": "sql",
        ".html": "html",
        ".css": "css",
        ".xml": "xml",
        ".json": "json",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".toml": "toml",
        ".md": "markdown",
        ".txt": "text",
    }

    ext = Path(filename).suffix.lower()
    return extension_map.get(ext, "text")


def create_file_context_prompt(files_data: list[dict[str, Any]]) -> str:
    """Create a context prompt that includes uploaded files."""
    if not files_data:
        return ""

    context = "Here are the files you uploaded:\n\n"

    for file_data in files_data:
        context += f"## File: {file_data['name']}\n"
        context += f"**Type:** {file_data['type']}\n"
        context += f"**Size:** {format_file_size(file_data['size'])}\n\n"

        if is_text_file(file_data["type"]):
            try:
                content = file_data["content"].decode("utf-8")
                context += f"**Content:**\n```{get_language_from_filename(file_data['name'])}\n{content}\n```\n\n"
            except UnicodeDecodeError:
                context += "**Content:** [Binary file - cannot display]\n\n"
        else:
            context += "**Content:** [Binary file - cannot display]\n\n"

    context += "---\n\n"
    return context
