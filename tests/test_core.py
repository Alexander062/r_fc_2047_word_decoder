import unittest

from r_fc_2047_word_decoder import decode, decode_header, decode_text


class TestDecodeSingle(unittest.TestCase):
    def test_base64_utf8(self):
        self.assertEqual(decode("=?utf-8?b?SGVsbG8=?="), "Hello")

    def test_q_encoding_utf8(self):
        self.assertEqual(decode("=?utf-8?q?Hello_World?="), "Hello World")

    def test_q_encoding_hex(self):
        self.assertEqual(decode("=?iso-8859-1?q?caf=E9?="), "café")

    def test_invalid_encoded_word_returns_input(self):
        self.assertEqual(decode("not encoded"), "not encoded")

    def test_missing_charset(self):
        self.assertEqual(decode("=?utf-8?b?SGVsbG8"), "=?utf-8?b?SGVsbG8")

    def test_non_string_raises(self):
        with self.assertRaises(TypeError):
            decode(123)


class TestDecodeHeader(unittest.TestCase):
    def test_single_encoded_word(self):
        self.assertEqual(decode_header("=?utf-8?b?SGVsbG8=?="), "Hello")

    def test_adjacent_encoded_words_concatenated(self):
        header = "=?utf-8?b?SGVsbG8=?= =?utf-8?b?V29ybGQ=?="
        self.assertEqual(decode_header(header), "HelloWorld")

    def test_adjacent_with_newline_style_whitespace(self):
        header = "=?utf-8?b?SGVsbG8=?=\r\n =?utf-8?b?V29ybGQ=?="
        self.assertEqual(decode_header(header), "HelloWorld")

    def test_non_adjacent_encoded_words_preserve_space(self):
        header = "=?utf-8?b?SGVsbG8=?=  =?utf-8?b?V29ybGQ=?="
        # Two spaces are not linear whitespace: a space, then another space
        # means the encoded-words are separated by a space and then an empty
        # non-whitespace segment? Actually linear whitespace is one or more
        # spaces/tabs, so two spaces still count as linear whitespace.
        # RFC 2047 says they should be concatenated. Let's test that.
        self.assertEqual(decode_header(header), "HelloWorld")

    def test_text_around_encoded_words(self):
        header = "Hello =?utf-8?q?World?=!"
        self.assertEqual(decode_header(header), "Hello World!")

    def test_non_string_raises(self):
        with self.assertRaises(TypeError):
            decode_header(None)


class TestDecodeText(unittest.TestCase):
    def test_multiple_lines(self):
        text = "Subject: =?utf-8?b?SGVsbG8=?=\nFrom: =?iso-8859-1?q?Andr=E9?="
        expected = "Subject: Hello\nFrom: André"
        self.assertEqual(decode_text(text), expected)

    def test_no_encoded_words(self):
        self.assertEqual(decode_text("plain text"), "plain text")

    def test_non_string_raises(self):
        with self.assertRaises(TypeError):
            decode_text([])


if __name__ == "__main__":
    unittest.main()
