import html
import re


def md_to_telegram_html(text: str) -> str:
    """Converts LLM Markdown output to Telegram-safe HTML.

    Handles escaping, code blocks (with optional syntax highlighting),
    inline code, bold, italics, strikethrough, links, spoilers, and headers.
    Lists and blockquotes are left as plain text since Telegram handles
    them decently without dedicated HTML tags.

    Args:
        text (str): The raw markdown string from the LLM.

    Returns:
        str: The HTML string safe for Telegram ParseMode.HTML.
    """
    # 1. Escape HTML special characters first (<, >, &)
    safe_text = html.escape(text)

    # 2. Multiline code blocks with language: ```python\ncode\n```
    safe_text = re.sub(
        r"```(\w+)\n(.*?)\n?```",
        r'<pre><code class="language-\1">\2</code></pre>',
        safe_text,
        flags=re.DOTALL,
    )
    # 3. Multiline code blocks without language: ```\ncode\n```
    safe_text = re.sub(
        r"```\n?(.*?)\n?```",
        r"<pre><code>\1</code></pre>",
        safe_text,
        flags=re.DOTALL,
    )

    # 4. Inline code: `code`
    safe_text = re.sub(r"`(.+?)`", r"<code>\1</code>", safe_text)

    # 5. Links: [text](url)
    safe_text = re.sub(r"\[(.+?)\]\((.+?)\)", r'<a href="\2">\1</a>', safe_text)

    # 6. Bold: **text**
    safe_text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", safe_text)

    # 7. Italic: *text* (using negative lookbehind/ahead to not break bold)
    safe_text = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<i>\1</i>", safe_text)

    # 8. Strikethrough: ~~text~~
    safe_text = re.sub(r"~~(.+?)~~", r"<s>\1</s>", safe_text)

    # 9. Spoilers: ||text||
    safe_text = re.sub(r"\|\|(.+?)\|\|", r"<tg-spoiler>\1</tg-spoiler>", safe_text)

    # 10. Headers: # Header -> <b>Header</b>
    safe_text = re.sub(r"^#+\s+(.+)$", r"<b>\1</b>", safe_text, flags=re.MULTILINE)

    return safe_text
