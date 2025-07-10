"""Session management and persistence layer."""

import json
from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import and_, desc, or_, text
from sqlalchemy.orm import Session as DBSession

from .context import ContextManager
from .database import SessionDatabase
from .models import Message, Session, SessionStatus, Tag


class SessionManager:
    """Manages session persistence and operations."""

    def __init__(self, database: SessionDatabase | None = None):
        """Initialize session manager.

        Args:
            database: SessionDatabase instance. If None, creates a new one.
        """
        self.db = database or SessionDatabase()
        self.context_manager = ContextManager()

    def create_session(
        self,
        name: str,
        provider: str,
        model: str,
        mode: str = "general",
        description: str | None = None,
        system_prompt: str | None = None,
        config: dict[str, Any] | None = None,
        parent_id: str | None = None,
        branch_point_message_id: str | None = None,
    ) -> Session:
        """Create a new session.

        Args:
            name: Session name
            provider: LLM provider name
            model: Model name
            mode: Chat mode (general, code, debug, etc.)
            description: Optional session description
            system_prompt: Optional system prompt
            config: Optional configuration dict
            parent_id: Parent session ID for branching
            branch_point_message_id: Message ID to branch from

        Returns:
            Created session object
        """
        with self.db.get_session() as db:
            session = Session(
                id=str(uuid4()),
                name=name,
                provider=provider,
                model=model,
                mode=mode,
                description=description,
                system_prompt=system_prompt,
                config=config or {},
                parent_id=parent_id,
                branch_point_message_id=branch_point_message_id,
            )
            db.add(session)
            db.commit()
            db.refresh(session)

            # Store the ID before potential detachment
            session_id = session.id

            # If branching, copy messages up to branch point
            if parent_id and branch_point_message_id:
                self._copy_messages_to_branch(db, parent_id, session_id, branch_point_message_id)

            # Return a fresh copy to avoid detachment issues
            return db.query(Session).filter_by(id=session_id).first()

    def _copy_messages_to_branch(
        self, db: DBSession, parent_id: str, new_session_id: str, branch_point_message_id: str
    ):
        """Copy messages from parent session up to branch point."""
        # Get branch point message sequence
        branch_msg = db.query(Message).filter_by(id=branch_point_message_id).first()
        if not branch_msg:
            return

        # Copy all messages up to and including branch point
        parent_messages = (
            db.query(Message)
            .filter(and_(Message.session_id == parent_id, Message.sequence <= branch_msg.sequence))
            .order_by(Message.sequence)
            .all()
        )

        for msg in parent_messages:
            new_msg = Message(
                session_id=new_session_id,
                sequence=msg.sequence,
                role=msg.role,
                content=msg.content,
                model=msg.model,
                provider=msg.provider,
                prompt_tokens=msg.prompt_tokens,
                completion_tokens=msg.completion_tokens,
                total_tokens=msg.total_tokens,
                cost=msg.cost,
                metadata=msg.metadata,
                tool_calls=msg.tool_calls,
                attachments=msg.attachments,
                search_content=msg.search_content,
            )
            db.add(new_msg)

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        model: str | None = None,
        provider: str | None = None,
        metadata: dict[str, Any] | None = None,
        tool_calls: list[dict[str, Any]] | None = None,
        attachments: list[dict[str, Any]] | None = None,
        token_usage: dict[str, int] | None = None,
        cost: float | None = None,
    ) -> Message:
        """Add a message to a session.

        Args:
            session_id: Session ID
            role: Message role (user, assistant, system, tool)
            content: Message content
            model: Model used for generation
            provider: Provider used
            metadata: Additional metadata
            tool_calls: Tool invocations (for Phase 5)
            attachments: File attachments
            token_usage: Token usage dict with prompt_tokens, completion_tokens
            cost: Message cost

        Returns:
            Created message object
        """
        # Normalize content to string if it's not already
        if not isinstance(content, str):
            if hasattr(content, "content"):
                content = content.content
            else:
                content = str(content)

        with self.db.get_session() as db:
            # Get next sequence number
            last_msg = (
                db.query(Message)
                .filter_by(session_id=session_id)
                .order_by(desc(Message.sequence))
                .first()
            )

            sequence = (last_msg.sequence + 1) if last_msg else 1

            # Create message
            message = Message(
                session_id=session_id,
                sequence=sequence,
                role=role,
                content=content,
                model=model,
                provider=provider,
                message_metadata=metadata or {},
                tool_calls=tool_calls,
                attachments=attachments,
                search_content=self._prepare_search_content(content),
                prompt_tokens=token_usage.get("prompt_tokens") if token_usage else None,
                completion_tokens=token_usage.get("completion_tokens") if token_usage else None,
                total_tokens=token_usage.get("total_tokens") if token_usage else None,
                cost=cost,
            )
            db.add(message)

            # Update session statistics
            session = db.query(Session).filter_by(id=session_id).first()
            if session:
                session.message_count += 1
                session.accessed_at = datetime.utcnow()
                if token_usage and token_usage.get("total_tokens"):
                    session.total_tokens += token_usage["total_tokens"]
                if cost:
                    session.total_cost += cost

            # Update FTS index
            db.execute(
                text(
                    """
                INSERT INTO messages_fts (message_id, session_id, content, role)
                VALUES (:msg_id, :session_id, :content, :role)
            """
                ),
                {"msg_id": message.id, "session_id": session_id, "content": content, "role": role},
            )

            db.commit()
            db.refresh(message)

            # Store the ID to avoid detachment issues
            message_id = message.id

            # Return a fresh copy
            return db.query(Message).filter_by(id=message_id).first()

    def _prepare_search_content(self, content: str) -> str:
        """Prepare content for full-text search."""
        # Basic preprocessing - can be enhanced later
        # Handle cases where content might not be a string
        if not isinstance(content, str):
            # If it's a ChatCompletion object, extract the content
            if hasattr(content, "content"):
                content = content.content
            else:
                content = str(content)
        return content.lower().strip()

    def get_session(self, session_id: str) -> Session | None:
        """Get a session by ID."""
        from sqlalchemy.orm import joinedload

        with self.db.get_session() as db:
            session = (
                db.query(Session).options(joinedload(Session.tags)).filter_by(id=session_id).first()
            )
            if session:
                # Access tags to ensure they're loaded
                _ = session.tags
            return session

    def get_active_sessions(self, limit: int = 50, offset: int = 0) -> list[Session]:
        """Get active sessions ordered by last access."""
        with self.db.get_session() as db:
            return (
                db.query(Session)
                .filter_by(status=SessionStatus.ACTIVE.value)
                .order_by(desc(Session.accessed_at))
                .limit(limit)
                .offset(offset)
                .all()
            )

    def get_messages(
        self, session_id: str, limit: int | None = None, offset: int = 0
    ) -> list[Message]:
        """Get messages for a session."""
        with self.db.get_session() as db:
            query = db.query(Message).filter_by(session_id=session_id).order_by(Message.sequence)

            if limit:
                query = query.limit(limit).offset(offset)

            return query.all()

    def search_sessions(self, query: str, limit: int = 20) -> list[tuple[Session, list[Message]]]:
        """Search sessions and messages using full-text search.

        Args:
            query: Search query
            limit: Maximum results

        Returns:
            List of (session, matching_messages) tuples
        """
        with self.db.get_session() as db:
            # Search in messages using FTS
            results = db.execute(
                text(
                    """
                SELECT DISTINCT session_id, message_id
                FROM messages_fts
                WHERE messages_fts MATCH :query
                ORDER BY rank
                LIMIT :limit
            """
                ),
                {"query": query, "limit": limit},
            ).fetchall()

            if not results:
                return []

            # Group by session
            session_messages = {}
            for session_id, message_id in results:
                if session_id not in session_messages:
                    session_messages[session_id] = []
                session_messages[session_id].append(message_id)

            # Fetch sessions and messages
            result_list = []
            for session_id, message_ids in session_messages.items():
                session = db.query(Session).filter_by(id=session_id).first()
                if session and session.status == SessionStatus.ACTIVE.value:
                    messages = (
                        db.query(Message)
                        .filter(Message.id.in_(message_ids))
                        .order_by(Message.sequence)
                        .all()
                    )
                    result_list.append((session, messages))

            return result_list

    def delete_session(self, session_id: str, hard_delete: bool = False):
        """Delete or archive a session.

        Args:
            session_id: Session ID
            hard_delete: If True, permanently deletes. Otherwise marks as deleted.
        """
        with self.db.get_session() as db:
            session = db.query(Session).filter_by(id=session_id).first()
            if not session:
                return

            if hard_delete:
                # Delete from FTS index
                db.execute(
                    text(
                        """
                    DELETE FROM messages_fts
                    WHERE session_id = :session_id
                """
                    ),
                    {"session_id": session_id},
                )

                # Delete session (cascades to messages)
                db.delete(session)
            else:
                # Soft delete
                session.status = SessionStatus.DELETED.value

            db.commit()

    def archive_session(self, session_id: str):
        """Archive a session."""
        with self.db.get_session() as db:
            session = db.query(Session).filter_by(id=session_id).first()
            if session:
                session.status = SessionStatus.ARCHIVED.value
                db.commit()

    def update_session(
        self,
        session_id: str,
        name: str | None = None,
        description: str | None = None,
        tags: list[str] | None = None,
        config: dict[str, Any] | None = None,
    ):
        """Update session metadata.

        Args:
            session_id: Session ID
            name: New name
            description: New description
            tags: List of tag names
            config: Updated configuration
        """
        with self.db.get_session() as db:
            session = db.query(Session).filter_by(id=session_id).first()
            if not session:
                return

            if name is not None:
                session.name = name
            if description is not None:
                session.description = description
            if config is not None:
                session.config = config

            if tags is not None:
                # Clear existing tags
                session.tags.clear()

                # Add new tags
                for tag_name in tags:
                    tag = db.query(Tag).filter_by(name=tag_name).first()
                    if not tag:
                        tag = Tag(name=tag_name)
                        db.add(tag)
                    session.tags.append(tag)

            session.updated_at = datetime.utcnow()
            db.commit()

    def get_session_context(
        self,
        session_id: str,
        max_messages: int | None = None,
        max_tokens: int | None = None,
        model: str | None = None,
        mode: str = "balanced",
    ) -> tuple[list[dict[str, Any]], bool]:
        """Get session messages formatted for LLM context with intelligent windowing.

        Args:
            session_id: Session ID
            max_messages: Maximum number of recent messages
            max_tokens: Maximum total tokens
            model: Model name for context limits
            mode: Context mode (aggressive, balanced, conservative)

        Returns:
            Tuple of (message list, was_truncated)
        """
        session = self.get_session(session_id)
        if not session:
            return [], False

        messages = self.get_messages(session_id)

        # Convert to LLM format
        context = []
        for msg in messages:
            msg_dict = {"role": msg.role, "content": msg.content}
            context.append(msg_dict)

        # Apply message limit if specified
        if max_messages and len(context) > max_messages:
            context = context[-max_messages:]

        # Use context manager for intelligent windowing
        if model or max_tokens:
            model_name = model or session.model
            context, was_truncated = self.context_manager.optimize_context(
                context, model_name, target_tokens=max_tokens, preserve_last_n=10
            )

            # Add summary if truncated
            if was_truncated and len(messages) > len(context):
                truncated_messages = messages[: len(messages) - len(context)]
                summary = self.context_manager.create_summary_message(
                    [{"role": m.role, "content": m.content} for m in truncated_messages]
                )
                context.insert(0, summary)

            return context, was_truncated

        return context, False

    def export_session(self, session_id: str, format: str = "json") -> str:
        """Export a session in various formats.

        Args:
            session_id: Session ID
            format: Export format (json, markdown, txt, html)

        Returns:
            Exported content as string
        """
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        messages = self.get_messages(session_id)

        if format == "json":
            return self._export_json(session, messages)
        elif format == "markdown":
            return self._export_markdown(session, messages)
        elif format == "txt":
            return self._export_txt(session, messages)
        elif format == "html":
            return self._export_html(session, messages)
        else:
            raise ValueError(f"Unsupported export format: {format}")

    def _export_json(self, session: Session, messages: list[Message]) -> str:
        """Export as JSON."""
        data = {
            "session": {
                "id": session.id,
                "name": session.name,
                "description": session.description,
                "provider": session.provider,
                "model": session.model,
                "mode": session.mode,
                "created_at": session.created_at.isoformat(),
                "updated_at": session.updated_at.isoformat(),
                "message_count": session.message_count,
                "total_tokens": session.total_tokens,
                "total_cost": session.total_cost,
                "config": session.config,
            },
            "messages": [
                {
                    "sequence": msg.sequence,
                    "role": msg.role,
                    "content": msg.content,
                    "created_at": msg.created_at.isoformat(),
                    "model": msg.model,
                    "provider": msg.provider,
                    "tokens": {
                        "prompt": msg.prompt_tokens,
                        "completion": msg.completion_tokens,
                        "total": msg.total_tokens,
                    },
                    "cost": msg.cost,
                    "metadata": msg.message_metadata,
                    "tool_calls": msg.tool_calls,
                    "attachments": msg.attachments,
                }
                for msg in messages
            ],
        }
        return json.dumps(data, indent=2)

    def _export_markdown(self, session: Session, messages: list[Message]) -> str:
        """Export as Markdown."""
        lines = [
            f"# {session.name}",
            "",
            f"**Provider:** {session.provider}  ",
            f"**Model:** {session.model}  ",
            f"**Mode:** {session.mode}  ",
            f"**Created:** {session.created_at.strftime('%Y-%m-%d %H:%M:%S')}  ",
            f"**Messages:** {session.message_count}  ",
            f"**Total Tokens:** {session.total_tokens}  ",
            "",
        ]

        if session.description:
            lines.extend([f"{session.description}", ""])

        lines.append("---")
        lines.append("")

        for msg in messages:
            role_emoji = {"user": "👤", "assistant": "🤖", "system": "⚙️", "tool": "🔧"}.get(
                msg.role, "❓"
            )

            lines.append(f"### {role_emoji} {msg.role.title()}")
            lines.append(f"*{msg.created_at.strftime('%Y-%m-%d %H:%M:%S')}*")
            lines.append("")
            lines.append(msg.content)
            lines.append("")

            if msg.tool_calls:
                lines.append("**Tool Calls:**")
                lines.append("```json")
                lines.append(json.dumps(msg.tool_calls, indent=2))
                lines.append("```")
                lines.append("")

        return "\n".join(lines)

    def _export_txt(self, session: Session, messages: list[Message]) -> str:
        """Export as plain text."""
        lines = [
            f"Session: {session.name}",
            f"Provider: {session.provider}",
            f"Model: {session.model}",
            f"Created: {session.created_at.strftime('%Y-%m-%d %H:%M:%S')}",
            f"Messages: {session.message_count}",
            "=" * 80,
            "",
        ]

        for msg in messages:
            lines.append(f"[{msg.role.upper()}] {msg.created_at.strftime('%H:%M:%S')}")
            lines.append(msg.content)
            lines.append("")

        return "\n".join(lines)

    def _export_html(self, session: Session, messages: list[Message]) -> str:
        """Export as HTML."""
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{session.name}</title>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
        .message {{ margin: 20px 0; padding: 15px; border-radius: 8px; }}
        .user {{ background-color: #e3f2fd; }}
        .assistant {{ background-color: #f5f5f5; }}
        .system {{ background-color: #fff3e0; }}
        .tool {{ background-color: #f3e5f5; }}
        .timestamp {{ color: #666; font-size: 0.9em; }}
        .metadata {{ margin-top: 10px; font-size: 0.85em; color: #666; }}
        pre {{ background-color: #f5f5f5; padding: 10px; border-radius: 4px; overflow-x: auto; }}
    </style>
</head>
<body>
    <h1>{session.name}</h1>
    <p><strong>Provider:</strong> {session.provider} | <strong>Model:</strong> {session.model}</p>
    <p><strong>Created:</strong> {session.created_at.strftime("%Y-%m-%d %H:%M:%S")}</p>
    <hr>
"""

        for msg in messages:
            html += f"""
    <div class="message {msg.role}">
        <strong>{msg.role.title()}</strong>
        <span class="timestamp">{msg.created_at.strftime("%H:%M:%S")}</span>
        <div>{msg.content.replace(chr(10), "<br>")}</div>
"""
            if msg.metadata or msg.tool_calls:
                html += '<div class="metadata">'
                if msg.tool_calls:
                    html += f"<pre>{json.dumps(msg.tool_calls, indent=2)}</pre>"
                html += "</div>"
            html += "    </div>\n"

        html += """
</body>
</html>"""
        return html

    def get_tool_history(self, session_id: str) -> list[dict[str, Any]]:
        """Get tool call history for a session.

        Args:
            session_id: Session ID

        Returns:
            List of tool calls with their results
        """
        with self.db.get_session() as db:
            # Get all messages with tool calls or tool results
            messages = (
                db.query(Message)
                .filter(
                    and_(
                        Message.session_id == session_id,
                        or_(Message.tool_calls.isnot(None), Message.role == "tool"),
                    )
                )
                .order_by(Message.sequence)
                .all()
            )

            tool_history = []
            for msg in messages:
                if msg.tool_calls:
                    # Message contains tool calls
                    tool_history.append(
                        {
                            "type": "call",
                            "sequence": msg.sequence,
                            "created_at": msg.created_at,
                            "role": msg.role,
                            "content": msg.content,
                            "tool_calls": msg.tool_calls,
                        }
                    )
                elif msg.role == "tool":
                    # Tool result message
                    tool_history.append(
                        {
                            "type": "result",
                            "sequence": msg.sequence,
                            "created_at": msg.created_at,
                            "content": msg.content,
                            "tool_call_id": (
                                msg.message_metadata.get("tool_call_id")
                                if msg.message_metadata
                                else None
                            ),
                        }
                    )

            return tool_history

    def get_session_tools_summary(self, session_id: str) -> dict[str, Any]:
        """Get summary of tools used in a session.

        Args:
            session_id: Session ID

        Returns:
            Dictionary with tool usage statistics
        """
        with self.db.get_session() as db:
            messages = (
                db.query(Message)
                .filter(and_(Message.session_id == session_id, Message.tool_calls.isnot(None)))
                .all()
            )

            tool_counts = {}
            total_calls = 0

            for msg in messages:
                if msg.tool_calls:
                    for call in msg.tool_calls:
                        tool_name = call.get("name", "unknown")
                        tool_counts[tool_name] = tool_counts.get(tool_name, 0) + 1
                        total_calls += 1

            return {
                "total_tool_calls": total_calls,
                "unique_tools": len(tool_counts),
                "tool_counts": tool_counts,
                "most_used": (
                    max(tool_counts.items(), key=lambda x: x[1])[0] if tool_counts else None
                ),
            }
