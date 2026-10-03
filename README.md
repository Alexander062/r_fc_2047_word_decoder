# RFC 2047 Word Decoder

Decodes RFC 2047 encoded-words from email headers, handling both base64 and quoted-printable encodings within charset-specified boundaries.

## Usage

```python
from r_fc_2047_word_decoder import decode, decode_header, decode_text

# Decode a single encoded-word
decode("=?utf-8?b?SGVsbG8=?=")  # "Hello"

# Decode all encoded-words in a header value
decode_header("=?utf-8?q?Hello_World?=")  # "Hello World"

# Decode an entire block of text line by line
decode_text("Subject: =?iso-8859-1?q?caf=E9?=\n")  # "Subject: café\n"
```

## Why this library exists

Email headers are limited to ASCII by RFC 5322, so non-ASCII characters must be encoded using the RFC 2047 encoded-word syntax. Decoding these by hand is error-prone because of the two different transfer encodings, charset handling, and the rule that adjacent encoded-words separated only by linear whitespace must be concatenated without the whitespace. This library provides a small, dependency-free decoder that implements those rules in a straightforward way.

## Design trade-off

Invalid encoded-words are returned unchanged rather than raising an exception. This makes the library forgiving of the many real-world messages that contain malformed encoded-words, and it preserves information that would otherwise be lost. Callers can compare input and output to detect whether decoding actually happened.

## Edge cases

Adjacent encoded-words separated by any amount of spaces or tabs are concatenated without the separating whitespace, as required by RFC 2047 section 6.2. This means `=?utf-8?b?SGVsbG8=?=  =?utf-8?b?V29ybGQ=?=` decodes to `HelloWorld`, not `Hello  World`.

Charsets other than UTF-8, ISO-8859-1, and US-ASCII are decoded using Python's standard codec lookup. If the codec is unavailable or the bytes are invalid for that codec, the bytes are preserved using the `surrogateescape` error handler.

## Design notes

The window stores values eagerly rather than keeping running aggregates. Running
sums drift with floating point over long streams, and recomputing from a small
buffer is cheap enough that the drift is not worth the speed.

