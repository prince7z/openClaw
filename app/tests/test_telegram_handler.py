import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.gateway.telegram.handler import split_message


def test_split_message_short():
    text = "Hello world"
    chunks = split_message(text, max_length=20)
    assert chunks == ["Hello world"]


def test_split_message_exact():
    text = "Hello"
    chunks = split_message(text, max_length=5)
    assert chunks == ["Hello"]


def test_split_message_newline():
    text = "Hello\nWorld\nPython"
    # max_length=12 covers "Hello\nWorld" which is 11 chars
    # "Hello\nWorld\n" has newline at index 11
    chunks = split_message(text, max_length=12)
    assert chunks == ["Hello\nWorld", "Python"]


def test_split_message_space():
    text = "Hello World Python"
    # max_length=12 covers "Hello World" which is 11 chars
    chunks = split_message(text, max_length=12)
    assert chunks == ["Hello World", "Python"]


def test_split_message_hard():
    text = "HelloWorldPython"
    # No space or newline, should hard split
    chunks = split_message(text, max_length=5)
    assert chunks == ["Hello", "World", "Pytho", "n"]


def test_split_message_empty():
    assert split_message("") == [""]


def test_split_message_multiple():
    # Long text with multiple newlines
    text = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5"
    chunks = split_message(text, max_length=14)
    # Line 1\nLine 2 is 13 chars
    # Line 3\nLine 4 is 13 chars
    # Line 5 is 6 chars
    assert chunks == ["Line 1\nLine 2", "Line 3\nLine 4", "Line 5"]


if __name__ == "__main__":
    test_split_message_short()
    test_split_message_exact()
    test_split_message_newline()
    test_split_message_space()
    test_split_message_hard()
    test_split_message_empty()
    test_split_message_multiple()
    print("Telegram handler split_message tests passed successfully!")
