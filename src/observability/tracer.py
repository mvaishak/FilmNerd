"""
Langfuse observability singleton.

Set these env vars to enable tracing:
  LANGFUSE_PUBLIC_KEY   — from your Langfuse project settings
  LANGFUSE_SECRET_KEY   — from your Langfuse project settings
  LANGFUSE_HOST         — self-hosted URL, e.g. http://localhost:3000

When keys are absent the module is a no-op: get_langfuse() returns None
and flush() is safe to call regardless.
"""
import os

from dotenv import load_dotenv

load_dotenv()

_client = None
_initialised = False


def get_langfuse():
    """Return the shared Langfuse client, or None if not configured."""
    global _client, _initialised
    if _initialised:
        return _client

    pub  = os.getenv("LANGFUSE_PUBLIC_KEY", "")
    sec  = os.getenv("LANGFUSE_SECRET_KEY", "")
    host = os.getenv("LANGFUSE_BASE_URL", os.getenv("LANGFUSE_HOST", "http://localhost:3000"))

    if pub and sec:
        try:
            from langfuse import Langfuse
            _client = Langfuse(public_key=pub, secret_key=sec, host=host)
        except Exception as exc:
            print(f"[observability] Langfuse init failed: {exc}")
            _client = None
    _initialised = True
    return _client


def flush():
    """Flush pending traces before process exit. Safe to call when disabled."""
    lf = get_langfuse()
    if lf:
        try:
            lf.flush()
        except Exception:
            pass
