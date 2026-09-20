"""RFC 2047 encoded-word decoder."""

from .core import decode, decode_header, decode_text

__all__ = ["decode", "decode_header", "decode_text"]
