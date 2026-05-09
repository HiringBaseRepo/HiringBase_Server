from contextvars import ContextVar
from typing import Optional

# Context variables for audit tracking
client_ip_var: ContextVar[Optional[str]] = ContextVar("client_ip", default=None)
user_agent_var: ContextVar[Optional[str]] = ContextVar("user_agent", default=None)

def set_audit_context(ip: Optional[str], user_agent: Optional[str]) -> None:
    """Set the audit context for the current request."""
    client_ip_var.set(ip)
    user_agent_var.set(user_agent)

def get_client_ip() -> Optional[str]:
    """Get the client IP from the current context."""
    return client_ip_var.get()

def get_user_agent() -> Optional[str]:
    """Get the user agent from the current context."""
    return user_agent_var.get()
