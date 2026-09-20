"""Decode RFC 2047 encoded-words.

This module decodes the MIME encoded-word syntax defined in RFC 2047, used
inside RFC 822/2822/5322 headers. Encoded-words look like:

    =?charset?encoding?encoded-text?=

where *encoding* is either ``B`` for base64 or ``Q`` for quoted-printable.
The charset may be any token, but only UTF-8, ISO-8859-1, and US-ASCII are
given special treatment here; other charsets are decoded to a Python str
using the ``surrogateescape`` error handler so that bytes always round-trip
through Unicode.

Adjacent encoded-words are concatenated after decoding when they are
separated only by linear whitespace, as required by RFC 2047 section 6.2.
"""

from __future__ import annotations

import base64
import binascii
import codecs
import quopri
import re
from typing import List, Tuple


_ENCODED_WORD_RE = re.compile(
    r"""=\?                # literal =?
        (?P<charset>[^?]+)  # charset token
        \?                 # separator
        (?P<encoding>[bBqQ]) # B or Q
        \?                 # separator
        (?P<encoded>[^?]*)  # encoded text, may be empty
        \?=                # literal ?=
    """,
    re.VERBOSE,
)

# RFC 2047 says an encoded-word must fit inside 75 characters including the
# delimiters. We do not enforce this here; decoders are more useful when they
# accept real-world messages that violate the length limit.


def _decode_bytes(data: bytes, charset: str) -> str:
    """Decode *data* as *charset*, falling back to surrogateescape.

    UTF-8 and ISO-8859-1 are decoded strictly. US-ASCII is decoded strictly as
    well but is practically a subset of UTF-8. For any other charset we use
    the standard library's codec lookup, and if the codec is missing we fall
    back to ``surrogateescape`` so the original bytes are not lost.
    """
    normalized = charset.lower()
    if normalized in ("utf-8", "utf8", "iso-8859-1", "iso8859-1", "us-ascii", "ascii"):
        try:
            return data.decode(charset)
        except (LookupError, UnicodeDecodeError):
            return data.decode("utf-8", errors="surrogateescape")

    try:
        return data.decode(charset)
    except (LookupError, UnicodeDecodeError):
        # Unknown charset or data not valid in that charset. Preserve bytes.
        return data.decode("utf-8", errors="surrogateescape")


def _decode_b(encoded: str, charset: str) -> str:
    """Decode base64 encoded-text."""
    try:
        raw = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError):
        # Some real-world messages contain invalid base64. Preserve the
        # original text instead of raising; callers can inspect the result
        # and notice that it still looks encoded.
        return encoded
    return _decode_bytes(raw, charset)


def _decode_q(encoded: str, charset: str) -> str:
    """Decode quoted-printable encoded-text.

    RFC 2047 Q-encoding uses ``_`` for space and ``=XX`` for other octets.
    The standard ``quopri.decodestring`` understands ``_`` as space, so we
    use it directly after converting the string to bytes.
    """
    # Q-encoding operates on bytes; encode to ASCII because the input is
    # defined to contain only ASCII characters (other than the encoded bytes).
    raw_encoded = encoded.encode("ascii", errors="surrogateescape")
    try:
        raw = quopri.decodestring(raw_encoded, header=True)
    except ValueError:
        # Malformed quoted-printable. Return original text.
        return encoded
    return _decode_bytes(raw, charset)


def _parse_encoded_word(match: re.Match[str]) -> str:
    """Convert a single encoded-word match to a decoded string."""
    charset = match.group("charset")
    encoding = match.group("encoding").lower()
    encoded = match.group("encoded")

    if encoding == "b":
        return _decode_b(encoded, charset)
    else:
        return _decode_q(encoded, charset)


def decode(encoded_word: str) -> str:
    """Decode a single encoded-word.

    Args:
        encoded_word: A complete encoded-word such as
            ``=?utf-8?b?SGVsbG8=?=``.

    Returns:
        The decoded text. If *encoded_word* is not a valid encoded-word, the
        input is returned unchanged.

    Raises:
        TypeError: If *encoded_word* is not a string.
    """
    if not isinstance(encoded_word, str):
        raise TypeError("encoded_word must be a str")

    match = _ENCODED_WORD_RE.fullmatch(encoded_word)
    if match is None:
        return encoded_word
    return _parse_encoded_word(match)


def decode_header(header: str) -> str:
    """Decode all encoded-words in a header value.

    Adjacent encoded-words separated only by linear whitespace are decoded
    separately and then concatenated without the separating whitespace, as
    specified by RFC 2047 section 6.2.

    Args:
        header: A raw header value, e.g. the contents of a ``Subject`` line
            without the trailing newline.

    Returns:
        The header with encoded-words replaced by their decoded equivalents.
        Non-encoded text is left untouched.
    """
    if not isinstance(header, str):
        raise TypeError("header must be a str")

    result: List[str] = []
    pos = 0

    for match in _ENCODED_WORD_RE.finditer(header):
        start, end = match.span()
        # Append text before this match.
        result.append(header[pos:start])

        decoded = _parse_encoded_word(match)

        # Check for adjacent encoded-words separated only by whitespace.
        # We look ahead in the original header to see if the next encoded-word
        # is immediately after optional whitespace.
        next_pos = end
        if next_pos < len(header):
            rest = header[next_pos:]
            # Find the next encoded-word, if any, and whether only whitespace
            # separates them.
            next_match = _ENCODED_WORD_RE.search(rest)
            if next_match and rest[: next_match.start()].strip() == "":
                # Adjacent encoded-word: skip the whitespace and continue
                # without appending anything.
                pos = next_pos + next_match.start()
                # But we still need to handle the decoded piece. We append it
                # now and continue the loop; the next iteration will process
                # the adjacent encoded-word.
                result.append(decoded)
                continue

        result.append(decoded)
        pos = end

    result.append(header[pos:])
    return "".join(result)


def decode_text(text: str) -> str:
    """Decode encoded-words anywhere in a text block.

    This is a convenience wrapper around :func:`decode_header` for use when
    the caller has an entire header block rather than a single header value.
    It operates line by line to avoid decoding encoded-words that span
    newlines, which are not valid according to RFC 2047.

    Args:
        text: A block of text possibly containing RFC 2047 encoded-words.

    Returns:
        The text with all encoded-words decoded.
    """
    if not isinstance(text, str):
        raise TypeError("text must be a str")

    return "\n".join(decode_header(line) for line in text.split("\n"))
