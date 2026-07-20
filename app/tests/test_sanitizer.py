import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.gateway.telegram.sanitizer import escape_telegram_html


def test_supported_tags():
    assert escape_telegram_html("Hello <b>world</b>") == "Hello <b>world</b>"
    assert escape_telegram_html("Nested: <b>bold <i>italic</i></b>") == "Nested: <b>bold <i>italic</i></b>"

def test_unsupported_tags():
    assert escape_telegram_html("Hello <invalid>world</invalid>") == "Hello &lt;invalid&gt;world&lt;/invalid&gt;"

def test_unclosed_tags():
    assert escape_telegram_html("<b>unclosed") == "<b>unclosed</b>"

def test_lone_brackets():
    assert escape_telegram_html("x < y and y > z") == "x &lt; y and y &gt; z"

def test_code_blocks():
    assert escape_telegram_html("<pre><code>if x < y: print(x)</code></pre>") == "<pre><code>if x &lt; y: print(x)</code></pre>"

def test_br_replacement():
    assert escape_telegram_html("Line 1<br>Line 2<br/>Line 3") == "Line 1\nLine 2\nLine 3"

if __name__ == "__main__":
    test_supported_tags()
    test_unsupported_tags()
    test_unclosed_tags()
    test_lone_brackets()
    test_code_blocks()
    test_br_replacement()
    print("All tests passed!")
