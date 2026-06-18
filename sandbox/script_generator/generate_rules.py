"""AI-powered XPath / CSS rule generation from HTML and natural-language instructions.

Core API
--------
``generate_extraction_rules(html, instruction)``
    Accepts raw HTML and a user instruction, produces a dict with ``xpath``
    and ``css`` keys (plus an optional ``confidence`` float).

Architecture
------------
1.  *Simplify* — strip the HTML down to a compact DOM-tree summary (text-bearing
    elements only, class / id attributes kept).
2.  *Prompt* — load the system-prompt template from
    ``ai_client/prompts/script_generation.txt`` and inject the instruction +
    summary.
3.  *Infer* — call ``ask_ollama``; parse the returned JSON.
4.  *Fallback* — if the AI is unavailable or its output is unparseable, use a
    regex / keyword-based fallback that returns sensible defaults for common
    Chinese scraping targets (姓名, 职称, 电话, etc.).

Usage::

    from script_generator.generate_rules import generate_extraction_rules

    rules = generate_extraction_rules(
        html='<div class="teacher"><span class="name">张三</span></div>',
        instruction="提取所有教师姓名",
    )
    print(rules["xpath"], rules["css"])
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup, NavigableString, Tag

from ai_client.ollama_client import ask_ollama

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_PROMPT_PATH: Path = (
    Path(__file__).resolve().parent.parent / "ai_client" / "prompts" / "script_generation.txt"
)

_MAX_HTML_SUMMARY_CHARS: int = 3000

# Keyword → (xpath_pattern, css_pattern) mapping used by the fallback engine.
_FALLBACK_KEYWORD_MAP: dict[str, tuple[str, str]] = {
    "姓名": ("//*[contains(@class,'name')]/text()", "[class*='name']"),
    "名字": ("//*[contains(@class,'name')]/text()", "[class*='name']"),
    "名称": ("//*[contains(@class,'name')]/text()", "[class*='name']"),
    "职称": ("//*[contains(@class,'title')]/text()", "[class*='title']"),
    "职位": ("//*[contains(@class,'title')]/text()", "[class*='title']"),
    "头衔": ("//*[contains(@class,'title')]/text()", "[class*='title']"),
    "电话": ("//*[contains(@class,'phone') or contains(@class,'tel')]/text()",
             "[class*='phone'],[class*='tel']"),
    "邮箱": ("//*[contains(@class,'email') or contains(@class,'mail')]/text()",
             "[class*='email'],[class*='mail']"),
    "部门": ("//*[contains(@class,'dept') or contains(@class,'department')]/text()",
             "[class*='dept'],[class*='department']"),
    "院系": ("//*[contains(@class,'dept') or contains(@class,'department')]/text()",
             "[class*='dept'],[class*='department']"),
    "研究方向": ("//*[contains(@class,'research') or contains(@class,'direction')]/text()",
                 "[class*='research'],[class*='direction']"),
    "简介": ("//*[contains(@class,'bio') or contains(@class,'intro')]/text()",
             "[class*='bio'],[class*='intro']"),
    "图片": ("//img/@src", "img"),
    "照片": ("//img/@src", "img"),
    "链接": ("//a/@href", "a"),
    "网址": ("//a/@href", "a"),
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def generate_extraction_rules(html: str, instruction: str) -> dict[str, Any]:
    """Generate XPath and CSS extraction rules for *html* given *instruction*.

    Args:
        html: Raw HTML string of the target page.
        instruction: Natural-language description of what to extract
            (e.g. ``"提取所有教师姓名"``).

    Returns:
        A dict with at least ``"xpath"`` and ``"css"`` keys.  May also
        contain ``"confidence"`` (float 0-1) and ``"source"``
        (``"ai"`` or ``"fallback"``).
    """

    # ---- nested: JSON extraction -------------------------------------------
    def _extract_json(text: str) -> dict[str, Any] | None:
        """Try to pull a JSON object from *text* (3 strategies)."""
        text = text.strip()
        # Strategy 1: direct parse
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        # Strategy 2: first { ... } block
        match = re.search(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
        # Strategy 3: strip markdown code fences
        cleaned = re.sub(r"^```(?:json)?\s*", "", text)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        try:
            return json.loads(cleaned.strip())
        except json.JSONDecodeError:
            pass
        return None

    # 1. Simplify HTML
    summary = _simplify_html(html)

    # 2. Load prompt template & inject variables
    try:
        prompt_template = _PROMPT_PATH.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        logger.error("无法加载 Prompt 模板 %s: %s", _PROMPT_PATH, exc)
        return _fallback_rules(instruction)

    full_prompt = (
        f"{prompt_template}\n\n"
        f"用户指令：{instruction}\n"
        f"页面 DOM 树摘要：\n{summary}"
    )

    # 3. Call Ollama
    raw_response = ask_ollama(full_prompt)
    if not raw_response:
        logger.warning("Ollama 未返回有效响应，降级为兜底规则。")
        return _fallback_rules(instruction)

    # 4. Parse JSON from AI response
    parsed = _extract_json(raw_response)
    if parsed is None:
        logger.warning("无法解析 AI 返回的 JSON，降级为兜底规则。原始响应: %s", raw_response[:200])
        return _fallback_rules(instruction)

    if "error" in parsed:
        logger.warning("AI 返回错误: %s，降级为兜底规则。", parsed["error"])
        return _fallback_rules(instruction)

    # Ensure required keys
    result: dict[str, Any] = {
        "xpath": parsed.get("xpath", ""),
        "css": parsed.get("css", ""),
        "confidence": parsed.get("confidence", 0.5),
        "source": "ai",
    }
    return result


# ---------------------------------------------------------------------------
# HTML simplification
# ---------------------------------------------------------------------------
def _simplify_html(html: str) -> str:
    """Build a compact DOM-tree summary of *html*, keeping only text-bearing
    elements and their ``class`` / ``id`` attributes.

    The output is truncated to ``_MAX_HTML_SUMMARY_CHARS`` characters.
    """

    def _walk(node: Tag, lines: list[str], depth: int) -> None:
        """Recursively walk *node*, appending a compact representation of each
        element that has direct text or a ``class`` / ``id`` attribute."""
        indent = "  " * depth
        for child in node.children:
            if isinstance(child, NavigableString):
                text = child.strip()
                if text:
                    lines.append(f"{indent}#text: {text}")
                continue
            if not isinstance(child, Tag):
                continue
            tag_str = child.name
            cls = child.get("class")
            if cls:
                class_str = " ".join(cls) if isinstance(cls, list) else str(cls)
                tag_str += f"[class='{class_str}']"
            elem_id = child.get("id")
            if elem_id:
                tag_str += f"#{elem_id}"
            direct_text = "".join(
                c.strip() for c in child.children if isinstance(c, NavigableString)
            ).strip()
            if direct_text:
                tag_str += f' = "{direct_text}"'
            has_text = bool(direct_text)
            has_attrs = bool(child.get("class") or child.get("id"))
            if has_text or has_attrs:
                lines.append(f"{indent}<{tag_str}>")
            if len(list(child.children)) > 0:
                _walk(child, lines, depth + 1)
            if has_text or has_attrs:
                lines.append(f"{indent}</{child.name}>")

    soup = BeautifulSoup(html, "html.parser")
    body = soup.body or soup  # fall back to whole document if <body> missing
    lines: list[str] = []
    _walk(body, lines, depth=0)
    summary = "\n".join(lines)
    if len(summary) > _MAX_HTML_SUMMARY_CHARS:
        summary = summary[:_MAX_HTML_SUMMARY_CHARS] + "\n…(truncated)"
    return summary


# ---------------------------------------------------------------------------
# Fallback rules
# ---------------------------------------------------------------------------

def _fallback_rules(instruction: str) -> dict[str, Any]:
    """Generate XPath / CSS rules from *instruction* using keyword matching.

    Returns a dict with ``"xpath"``, ``"css"``, ``"confidence"``, and
    ``"source": "fallback"``.
    """
    xpath_parts: list[str] = []
    css_parts: list[str] = []

    for keyword, (xp, cs) in _FALLBACK_KEYWORD_MAP.items():
        if keyword in instruction:
            xpath_parts.append(xp)
            css_parts.append(cs)

    if not xpath_parts:
        # Generic fallback: grab all text-bearing elements
        xpath = "//body//text()[normalize-space()]"
        css = "body *"
    else:
        xpath = " | ".join(xpath_parts)
        css = ", ".join(css_parts)

    logger.info("兜底规则生成 — 关键词匹配: %s", instruction)

    return {
        "xpath": xpath,
        "css": css,
        "confidence": 0.3,
        "source": "fallback",
    }


# ---------------------------------------------------------------------------
# Smoke test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # A minimal faculty-page snippet for testing
    test_html = """
    <html>
      <head><title>师资队伍</title></head>
      <body>
        <div class="teacher-list">
          <div class="teacher">
            <span class="name">张三</span>
            <span class="title">教授</span>
            <span class="email">zhangsan@example.com</span>
          </div>
          <div class="teacher">
            <span class="name">李四</span>
            <span class="title">副教授</span>
            <span class="email">lisi@example.com</span>
          </div>
        </div>
      </body>
    </html>
    """

    print("=" * 60)
    print("测试 1: 提取所有教师姓名")
    print("=" * 60)
    rules1 = generate_extraction_rules(test_html, "提取所有教师姓名")
    print(json.dumps(rules1, ensure_ascii=False, indent=2))

    print("\n" + "=" * 60)
    print("测试 2: 提取所有教师的姓名和邮箱")
    print("=" * 60)
    rules2 = generate_extraction_rules(test_html, "提取所有教师的姓名和邮箱")
    print(json.dumps(rules2, ensure_ascii=False, indent=2))

    print("\n" + "=" * 60)
    print("测试 3: HTML 简化输出 (仅展示摘要) ")
    print("=" * 60)
    print(_simplify_html(test_html))
