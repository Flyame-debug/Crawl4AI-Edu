"""
文件名: ai_cleaner.py
作用: 模块3核心 —— AI智能清洗与信息提取（用户驱动 + Markdown输出）
主要功能:
    1. 根据 user_prompt 从Markdown中智能提取信息
    2. 输出排版美观的Markdown文本（非固定字段JSON）
    3. 独立调用 Ollama /api/generate（不复用 ai_service.py）
    4. 响应解析（清除代码块包裹、空响应检测）
    5. 置信度评估（high/medium/low）
调用方: cleaning_pipeline.py / tasks.py
"""

import logging
import requests
from typing import Dict, Any, Optional

logger = logging.getLogger('apps.api.services.ai_cleaner')

# ============================================================
# 常量配置
# ============================================================

OLLAMA_API_URL = "http://127.0.0.1:11434"
OLLAMA_MODEL = "qwen2:7b"
OLLAMA_TIMEOUT = 120  # 秒
MARKDOWN_TRUNCATE_LENGTH = 12000  # 字符截断长度
MIN_CONTENT_LENGTH = 20  # 内容过短阈值（字符）

# ============================================================
# System Prompt 模板
# ============================================================

SYSTEM_PROMPT_TEMPLATE = """你是一个专业的信息提取助手。你的任务是根据用户的需求，从给定的网页文本中提取相应信息，并以清晰、美观的 Markdown 格式输出。

工作规则：
1. 仔细阅读"网页内容"，根据"用户需求"找到对应的信息
2. 只提取明确存在的信息，绝对不要编造、猜测或补充不存在的内容
3. 如果某项信息在原文中找不到，不要强行填写，跳过即可
4. 输出使用 Markdown 格式，合理使用标题、列表、加粗等排版
5. 保持信息简洁准确，直接呈现提取结果，不需要额外解释
6. 如果用户需求过于模糊或原文完全不相关，直接回复"未能从页面中找到匹配的信息"

输出格式示例：
## 张三 教授

**院系**: 计算机科学与技术学院

**联系方式**
- 邮箱: zhangsan@edu.cn
- 电话: 010-12345678

**研究方向**
- 机器学习
- 数据挖掘

请严格遵循上述格式输出，只输出提取结果，不要添加任何额外的说明文字。"""


def ai_clean_and_extract(
    markdown: str,
    user_prompt: str = None,
    page_type_hint: str = None
) -> Dict[str, Any]:
    """
    作用: 调用 Ollama 大模型，根据用户指令从 Markdown 中提取信息并排版为 Markdown

    参数:
        markdown: 成员A通过Crawl4AI转换的未清洗Markdown文本
        user_prompt: 用户在前端输入的提取指令（如"提取邮箱、电话、研究方向"）
        page_type_hint: 成员A预填的页面类型（teacher/course/research），可选

    返回:
        {
            "success": True/False,
            "data": {
                "page_type": "teacher",
                "content": "## 张三 教授\\n\\n- **邮箱**: ...",
                "method": "ai_ollama",
                "confidence": "high"
            },
            "error": "错误信息或None"
        }
    """
    # 参数校验
    if not markdown or not markdown.strip():
        logger.warning("输入 Markdown 为空，跳过AI清洗")
        return {
            "success": False,
            "data": None,
            "error": "输入Markdown内容为空"
        }

    # 构建 Prompt
    system_prompt = _build_system_prompt()
    user_content = _build_user_prompt(markdown, user_prompt, page_type_hint)

    # 调用 Ollama
    raw_response = _call_ollama(system_prompt, user_content)
    if raw_response is None:
        return {
            "success": False,
            "data": None,
            "error": "Ollama API调用失败，请确认服务已启动"
        }

    # 解析响应
    cleaned_content = _parse_response(raw_response)

    # 空响应检测
    if not cleaned_content or len(cleaned_content.strip()) < MIN_CONTENT_LENGTH:
        logger.warning(f"AI返回内容过短或为空: {repr(raw_response[:200])}")
        return {
            "success": False,
            "data": None,
            "error": f"AI返回内容过短（{len(cleaned_content)}字符），可能无法提取有效信息"
        }

    # 置信度评估
    confidence = _assess_confidence(cleaned_content)

    # 确定 page_type
    page_type = page_type_hint or "unknown"

    logger.info(
        f"AI清洗完成: content长度={len(cleaned_content)}, "
        f"confidence={confidence}, page_type={page_type}"
    )

    return {
        "success": True,
        "data": {
            "page_type": page_type,
            "content": cleaned_content,
            "method": "ai_ollama",
            "confidence": confidence
        },
        "error": None
    }


def _build_system_prompt() -> str:
    """
    作用: 返回清洗提取的 System Prompt 模板
    """
    return SYSTEM_PROMPT_TEMPLATE


def _build_user_prompt(
    markdown: str,
    user_prompt: str = None,
    page_type_hint: str = None
) -> str:
    """
    作用: 组装发送给 Ollama 的 User Prompt
    """
    # 截断 Markdown 到指定长度
    truncated_markdown = markdown[:MARKDOWN_TRUNCATE_LENGTH]
    if len(markdown) > MARKDOWN_TRUNCATE_LENGTH:
        truncated_markdown += "\n\n...（内容过长，已截断）"

    # 构建页面类型提示
    type_hint_text = ""
    if page_type_hint:
        type_hint_text = f"页面类型提示: 这是一个{page_type_hint}页面。\n\n"

    # 构建用户需求
    if user_prompt and user_prompt.strip():
        demand_text = f"用户需求: {user_prompt.strip()}"
    else:
        demand_text = "用户需求: 请提取页面中的关键信息（如姓名、联系方式、研究方向等）"

    return f"""{type_hint_text}{demand_text}

网页内容:
{truncated_markdown}

请根据用户需求，从以上网页内容中提取信息并排版输出:"""


def _call_ollama(system_prompt: str, user_prompt: str) -> Optional[str]:
    """
    作用: 直接调用 Ollama /api/generate，返回模型生成的原始文本
          独立实现，不复用 ai_service.py

    返回: 模型响应文本，失败返回 None
    """
    try:
        url = f"{OLLAMA_API_URL}/api/generate"

        payload = {
            "model": OLLAMA_MODEL,
            "prompt": user_prompt,
            "system": system_prompt,
            "stream": False,
            "options": {
                "temperature": 0.3,
                "top_p": 0.9,
            }
        }

        logger.debug(f"调用 Ollama: model={OLLAMA_MODEL}, prompt长度={len(user_prompt)}")
        response = requests.post(url, json=payload, timeout=OLLAMA_TIMEOUT)
        response.raise_for_status()

        result = response.json()
        raw_text = result.get("response", "")

        logger.debug(f"Ollama 响应长度: {len(raw_text)}")
        return raw_text

    except requests.exceptions.Timeout:
        logger.error(f"Ollama API 超时 ({OLLAMA_TIMEOUT}秒): {OLLAMA_API_URL}")
        return None
    except requests.exceptions.ConnectionError:
        logger.error(f"无法连接到 Ollama: {OLLAMA_API_URL}")
        return None
    except requests.exceptions.HTTPError as e:
        logger.error(f"Ollama HTTP错误: {e}")
        return None
    except Exception as e:
        logger.error(f"Ollama 调用异常: {str(e)}")
        return None


def _parse_response(raw_response: str) -> str:
    """
    作用: 解析 AI 返回的原始文本，清除可能的代码块包裹

    处理情况:
        1. ```markdown ... ``` 包裹 → 提取内部内容
        2. ``` ... ``` 包裹（无语言标识）→ 提取内部内容
        3. 无包裹的纯文本 → 直接返回
        4. 首尾空白 → 去除
    """
    if not raw_response:
        return ""

    text = raw_response.strip()

    # 清除 ```markdown ... ``` 包裹
    if text.startswith("```markdown"):
        # 找到第一个换行后的内容
        first_newline = text.find("\n")
        if first_newline != -1:
            text = text[first_newline + 1:]
        else:
            text = text[len("```markdown"):]
        # 去掉末尾的 ```
        if text.endswith("```"):
            text = text[:-3]
    elif text.startswith("```"):
        # 通用代码块包裹
        first_newline = text.find("\n")
        if first_newline != -1:
            text = text[first_newline + 1:]
        else:
            # 整行只有 ``` 开头，跳过
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]

    # 清除首尾空白
    return text.strip()


def _assess_confidence(content: str) -> str:
    """
    作用: 根据输出内容长度评估置信度

    评估规则:
        - 内容 >= 100 字符 → "high"（信息较为丰富）
        - 内容 >= 40 字符 → "medium"（有一定信息但偏少）
        - 内容 < 40 字符 → "low"（几乎无有效信息）

    注意: 此处判断的是 _parse_response 之后的内容，
    _parse_response 调用前已确保长度 >= MIN_CONTENT_LENGTH(20)
    """
    length = len(content.strip())

    if length >= 100:
        return "high"
    elif length >= 40:
        return "medium"
    else:
        return "low"
