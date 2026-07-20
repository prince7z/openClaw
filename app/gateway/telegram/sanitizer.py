import html
import re
from html.parser import HTMLParser

def escape_telegram_html(text: str) -> str:
    """
    Parses and sanitizes HTML text to ensure it complies with Telegram's HTML format rules.
    It:
    - Retains only supported Telegram HTML tags (b, strong, i, em, u, ins, s, strike, del, span/tg-spoiler, a, code, pre, blockquote, tg-emoji).
    - Escapes all unsupported tags and raw <, >, & characters (including those inside code/pre blocks).
    - Cleans up and safely formats allowed tag attributes.
    - Gracefully falls back to a fully escaped string if parsing fails.
    """
    # Supported tags in Telegram HTML
    # See: https://core.telegram.org/bots/api#html-style
    SUPPORTED_TAGS = {
        'b', 'strong',
        'i', 'em',
        'u', 'ins',
        's', 'strike', 'del',
        'span', 'tg-spoiler',
        'a',
        'code',
        'pre',
        'blockquote',
        'tg-emoji'
    }

    class TelegramHTMLSanitizer(HTMLParser):
        def __init__(self):
            super().__init__()
            self.result = []
            self.tag_stack = []

        def handle_starttag(self, tag, attrs):
            lower_tag = tag.lower()
            if lower_tag in SUPPORTED_TAGS:
                # Sanitize attributes
                valid_attrs = []
                for attr, val in attrs:
                    if val is None:
                        continue
                    attr_lower = attr.lower()
                    if lower_tag == 'a' and attr_lower == 'href':
                        valid_attrs.append(f'href="{html.escape(val, quote=True)}"')
                    elif lower_tag == 'span' and attr_lower == 'class' and val == 'tg-spoiler':
                        valid_attrs.append(f'class="tg-spoiler"')
                    elif lower_tag == 'code' and attr_lower == 'class' and val.startswith('language-'):
                        valid_attrs.append(f'class="{html.escape(val, quote=True)}"')
                    elif lower_tag == 'tg-emoji' and attr_lower == 'emoji-id':
                        valid_attrs.append(f'emoji-id="{html.escape(val, quote=True)}"')
                
                attr_str = " " + " ".join(valid_attrs) if valid_attrs else ""
                self.result.append(f"<{lower_tag}{attr_str}>")
                self.tag_stack.append(lower_tag)
            else:
                # Treat unsupported start tag as text and escape it
                attr_parts = []
                for k, v in attrs:
                    if v is None:
                        attr_parts.append(f' {k}')
                    else:
                        attr_parts.append(f' {k}="{html.escape(v, quote=True)}"')
                attr_str = "".join(attr_parts)
                self.result.append(html.escape(f"<{tag}{attr_str}>"))

        def handle_endtag(self, tag):
            lower_tag = tag.lower()
            if lower_tag in SUPPORTED_TAGS:
                if lower_tag in self.tag_stack:
                    while self.tag_stack:
                        open_tag = self.tag_stack.pop()
                        self.result.append(f"</{open_tag}>")
                        if open_tag == lower_tag:
                            break
            else:
                # Treat unsupported end tag as text and escape it
                self.result.append(html.escape(f"</{tag}>"))

        def handle_data(self, data):
            self.result.append(html.escape(data))

        def handle_entityref(self, name):
            self.result.append(f"&{name};")

        def handle_charref(self, name):
            self.result.append(f"&#{name};")

        def parse_and_get(self, html_text):
            # Pre-replace `<br>` / `<br/>` with newline characters as they aren't supported
            html_text = re.sub(r'<br\s*/?>', '\n', html_text, flags=re.IGNORECASE)
            try:
                self.feed(html_text)
                self.close()
            except Exception:
                return html.escape(html_text)
            
            while self.tag_stack:
                open_tag = self.tag_stack.pop()
                self.result.append(f"</{open_tag}>")
            return "".join(self.result)

    sanitizer = TelegramHTMLSanitizer()
    return sanitizer.parse_and_get(text)
