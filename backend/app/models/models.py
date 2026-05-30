import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, Integer, Text, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, relationship
from pgvector.sqlalchemy import Vector

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=True)
    name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    settings = Column(JSON, default=dict)

    integrations = relationship("Integration", back_populates="user", cascade="all, delete-orphan")


class Event(Base):
    __tablename__ = "events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source = Column(String(50), nullable=False, index=True)      # e.g., "gmail", "jira"
    type = Column(String(50), nullable=False)                    # e.g., "email_received", "ticket_assigned"
    priority = Column(Integer, default=1, index=True)            # 1 to 5
    payload = Column(JSON, nullable=False)
    status = Column(String(20), default="PENDING", index=True)  # PENDING, PROCESSED, FAILED
    summary = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)


class Integration(Base):
    __tablename__ = "integrations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    provider = Column(String(50), nullable=False, index=True)    # e.g., "google", "jira"
    credentials = Column(JSON, default=dict)                     # Encrypted client/refresh token strings
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="integrations")


class Memory(Base):
    __tablename__ = "memories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(768), nullable=True)                # Dimension size for nomic-embed-text/gemma
    tags = Column(JSON, default=dict)
    importance = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)


class ActionApproval(Base):
    __tablename__ = "action_approvals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    integration = Column(String(50), nullable=False)              # e.g., "gmail", "jira"
    action_type = Column(String(50), nullable=False)              # e.g., "send_email", "create_ticket"
    payload = Column(JSON, nullable=False)                        # payload arguments dict
    status = Column(String(20), default="PENDING", index=True)    # PENDING, APPROVED, REJECTED
    created_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)

