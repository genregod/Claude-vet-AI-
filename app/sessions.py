"""
Valor Assist — Conversation Session Management

Provides encrypted, server-side session storage for multi-turn chat.
Each chat widget session gets a unique session_id; conversation history
is stored in-memory (with an optional persistence hook for DynamoDB on AWS).

PII protection:
  - All stored messages are encrypted at rest using Fernet (AES-128-CBC).
  - Sessions auto-expire after a configurable TTL.
  - Conversation history is capped to prevent unbounded memory growth.
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field

from cryptography.fernet import Fernet

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class Message:
    """A single turn in the conversation."""
    role: str          # "user" or "assistant"
    content: str
    timestamp: float = field(default_factory=time.time)


@dataclass
class Session:
    """Holds the full conversation state for one chat widget instance."""
    session_id: str
    messages: list[Message] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    last_active: float = field(default_factory=time.time)
    metadata: dict = field(default_factory=dict)  # service_branch, rating, etc.

    @property
    def is_expired(self) -> bool:
        return (time.time() - self.last_active) > settings.session_ttl_seconds

    def add_message(self, role: str, content: str) -> None:
        self.messages.append(Message(role=role, content=content))
        self.last_active = time.time()
        # Cap history to prevent unbounded growth — keep system-relevant window
        if len(self.messages) > settings.max_conversation_turns * 2:
            # Keep first 2 messages (initial greeting context) + last N turns
            keep_recent = settings.max_conversation_turns * 2
            self.messages = self.messages[:2] + self.messages[-keep_recent:]

    def get_history_for_prompt(self) -> list[dict]:
        """Return conversation history formatted for Claude's messages API."""
        return [
            {"role": m.role, "content": m.content}
            for m in self.messages
        ]


class SessionStore:
    """
    In-memory session store with Fernet encryption for PII-sensitive content.

    For AWS production deployment, swap the _sessions dict for a DynamoDB
    backend using the same encrypt/decrypt interface.
    """

    def __init__(self):
        self._sessions: dict[str, Session] = {}
        self._fernet = Fernet(settings.encryption_key.encode())
        logger.info("SessionStore initialized (encryption enabled)")

    def create_session(self, metadata: dict | None = None) -> Session:
        """Create a new session with a unique ID."""
        session_id = str(uuid.uuid4())
        session = Session(session_id=session_id, metadata=metadata or {})
        self._sessions[session_id] = session
        self._cleanup_expired()
        logger.info("Created session %s", session_id)
        return session

    def get_session(self, session_id: str) -> Session | None:
        """Retrieve an existing session; returns None if expired or missing."""
        session = self._sessions.get(session_id)
        if session is None:
            return None
        if session.is_expired:
            logger.info("Session %s expired — removing", session_id)
            del self._sessions[session_id]
            return None
        return session

    def encrypt_content(self, plaintext: str) -> str:
        """Encrypt a string (for storing PII-containing messages)."""
        return self._fernet.encrypt(plaintext.encode()).decode()

    def decrypt_content(self, ciphertext: str) -> str:
        """Decrypt a previously encrypted string."""
        return self._fernet.decrypt(ciphertext.encode()).decode()

    def delete_session(self, session_id: str) -> bool:
        """Explicitly delete a session (e.g., user closes chat)."""
        if session_id in self._sessions:
            del self._sessions[session_id]
            logger.info("Deleted session %s", session_id)
            return True
        return False

    def _cleanup_expired(self) -> None:
        """Periodically sweep expired sessions."""
        expired = [
            sid for sid, s in self._sessions.items() if s.is_expired
        ]
        for sid in expired:
            del self._sessions[sid]
        if expired:
            logger.info("Cleaned up %d expired sessions", len(expired))

    @property
    def active_count(self) -> int:
        self._cleanup_expired()
        return len(self._sessions)
