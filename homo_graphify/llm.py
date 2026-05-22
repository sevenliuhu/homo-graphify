"""国产 LLM 适配层 — DeepSeek/Kimi/通义千问/智谱GLM/文心一言

为 graphify 提供中文 LLM 后端的标准化接口。
"""
from __future__ import annotations
import json
import os
import sys
import time
import re
from pathlib import Path
from typing import Any

# ── 国产 LLM 配置 ──────────────────────────────────────────

LLM_CONFIGS = {
    "deepseek": {
        "name": "DeepSeek",
        "base_url": "https://api.deepseek.com",
        "default_model": "deepseek-chat",
        "env_key": "DEEPSEEK_API_KEY",
        "supports_stream": True,
        "supports_thinking": True,  # deepseek-reasoner
    },
    "kimi": {
        "name": "Kimi (月之暗面)",
        "base_url": "https://api.moonshot.ai/v1",
        "default_model": "kimi-k2.6",
        "env_key": "MOONSHOT_API_KEY",
        "supports_stream": False,
    },
    "qwen": {
        "name": "通义千问 (Qwen)",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "default_model": "qwen3-235b-a22b",
        "env_key": "QWEN_API_KEY",
        "supports_stream": True,
    },
    "glm": {
        "name": "智谱 GLM",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "default_model": "glm-6",
        "env_key": "ZHIPUAI_API_KEY",
        "supports_stream": False,
    },
    "baidu": {
        "name": "文心一言 (ERNIE)",
        "base_url": "https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat",
        "default_model": "ernie-4.5-8k",
        "env_key": "BAIDU_API_KEY",
        "supports_stream": False,
    },
    "stepfun": {
        "name": "阶跃星辰 (StepFun)",
        "base_url": "https://api.stepfun.com/v1",
        "default_model": "step-2",
        "env_key": "STEPFUN_API_KEY",
        "supports_stream": True,
    },
    "ollama": {
        "name": "Ollama (本地)",
        "base_url": "http://localhost:11434/v1",
        "default_model": "qwen2.5-coder:7b",
        "env_key": "OLLAMA_API_KEY",
        "supports_stream": True,
    },
}


def resolve_backend(backend_name: str) -> str:
    """解析后端别名为标准名称"""
    ALIAS_MAP = {
        "deepseek": "deepseek",
        "ds": "deepseek",
        "moonshot": "kimi",
        "kimi": "kimi",
        "qwen": "qwen",
        "qwq": "qwen",
        "tongyi": "qwen",
        "glm": "glm",
        "zhipu": "glm",
        "chatglm": "glm",
        "ernie": "baidu",
        "baidu": "baidu",
        "wenxin": "baidu",
        "stepfun": "stepfun",
        "step": "stepfun",
        "jijie": "stepfun",
        "ollama": "ollama",
        "local": "ollama",
    }
    return ALIAS_MAP.get(backend_name.lower(), backend_name)


def get_api_key(backend: str) -> str | None:
    """获取指定后端的 API Key"""
    cfg = LLM_CONFIGS.get(backend)
    if not cfg:
        return None
    key = os.environ.get(cfg["env_key"])
    if key:
        return key
    # 兼容原生 DeepSeek API Key 环境变量
    if backend == "deepseek":
        return os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("OPENAI_API_KEY")
    return None


def check_env(backend: str) -> tuple[bool, str]:
    """检查环境配置是否就绪"""
    if backend == "ollama":
        # 检查 Ollama 服务是否运行
        import urllib.request
        try:
            urllib.request.urlopen("http://localhost:11434/api/tags", timeout=3)
            return True, "Ollama 服务运行中"
        except Exception:
            return False, "Ollama 服务未运行，请执行: ollama serve"
    
    cfg = LLM_CONFIGS.get(backend)
    if not cfg:
        return False, f"未知后端: {backend}"
    
    key = get_api_key(backend)
    if not key:
        return False, f"请设置环境变量 {cfg['env_key']}"
    
    return True, f"{cfg['name']} 就绪"


def print_status() -> None:
    """打印所有后端的配置状态"""
    print("=" * 60)
    print("  🔧 国产 LLM 环境检查")
    print("=" * 60)
    for key, cfg in LLM_CONFIGS.items():
        ok, msg = check_env(key)
        status = "✅" if ok else "❌"
        print(f"  {status} {cfg['name']:12s} — {msg}")
    print("=" * 60)


# ── 中文语义提取提示词 ──────────────────────────────────────

CHINESE_EXTRACTION_SYSTEM = """\
你是一个代码知识图谱提取助手。请从提供的文件中提取知识图谱片段。
仅输出有效 JSON，不要添加任何解释、代码块标记或开场白。

规则：
- EXTRACTED: 关系在源代码中显式声明（import、调用、引用）
- INFERRED: 合理推断（共享数据结构、隐含依赖）
- AMBIGUOUS: 不确定的关系，标记供审查

节点 ID 格式：仅小写字母、数字、下划线，不含点或斜杠。
格式：{stem}_{entity}
其中 stem = 无扩展名的文件名，entity = 符号名（均标准化）

对中文实体：
- 保留中文标识符作为 label
- ID 使用拼音或英文翻译
- 如果是中文注释中的概念，type 用 "concept"

输出严格遵循以下 JSON 格式：

{"nodes":[{"id":"stem_entity","label":"人类可读名称","file_type":"code|document|paper|image|rationale|concept","source_file":"relative/path","source_location":null}],"edges":[{"source":"node_id","target":"node_id","relation":"calls|imports|uses|references|cites|contains|implements|extends","confidence":"EXTRACTED|INFERRED|AMBIGUOUS","source_file":"relative/path"}]}
"""


def prepare_extraction_prompt(file_content: str, file_path: str, max_chars: int = 20000) -> str:
    """生成中文语义提取的提示词"""
    truncated = file_content[:max_chars]
    if len(file_content) > max_chars:
        truncated += f"\n\n... [文件截断: 仅显示前 {max_chars} 字符]"
    
    return f"""请分析以下文件并提取知识图谱：

文件: {file_path}

```
{truncated}
```

请仅输出有效的 JSON 对象。"""


# ── OpenAI 兼容接口 ────────────────────────────────────────

def call_llm(
    backend: str,
    messages: list[dict],
    model: str | None = None,
    temperature: float = 0,
    max_tokens: int = 16384,
    timeout: int = 600,
) -> dict[str, Any]:
    """调用国产 LLM 的 OpenAI 兼容接口

    返回 {"content": "...", "input_tokens": N, "output_tokens": N,
           "model": "...", "error": None|"..."}
    """
    cfg = LLM_CONFIGS.get(resolve_backend(backend))
    if not cfg:
        return {"content": None, "input_tokens": 0, "output_tokens": 0,
                "model": backend, "error": f"Unknown backend: {backend}"}

    api_key = get_api_key(backend)
    if not api_key and backend != "ollama":
        return {"content": None, "input_tokens": 0, "output_tokens": 0,
                "model": backend,
                "error": f"Missing API key for {backend}. Set {cfg['env_key']}"}

    try:
        from openai import OpenAI
    except ImportError:
        return {"content": None, "input_tokens": 0, "output_tokens": 0,
                "model": backend,
                "error": "openai package not installed. Run: pip install openai tiktoken"}

    client = OpenAI(
        api_key=api_key or "",
        base_url=cfg["base_url"],
        timeout=timeout,
    )

    kwargs = {
        "model": model or cfg["default_model"],
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }

    # Kimi K2.6 固定温度，不可自定义
    if backend == "kimi":
        del kwargs["temperature"]

    start = time.time()
    try:
        resp = client.chat.completions.create(**kwargs)
    except Exception as e:
        elapsed = time.time() - start
        return {"content": None, "input_tokens": 0, "output_tokens": 0,
                "model": model or cfg["default_model"],
                "error": f"{type(e).__name__}: {e} (elapsed: {elapsed:.1f}s)"}

    result = {
        "content": resp.choices[0].message.content if resp.choices else None,
        "input_tokens": resp.usage.prompt_tokens if resp.usage else 0,
        "output_tokens": resp.usage.completion_tokens if resp.usage else 0,
        "model": resp.model,
        "error": None,
    }

    return result


def extract_with_llm(
    backend: str,
    file_path: Path,
    root: Path,
    model: str | None = None,
) -> dict:
    """使用 LLM 从文件中提取知识图谱节点和边

    返回 {"nodes": [...], "edges": [...], "input_tokens": N, "output_tokens": N}
    """
    try:
        rel_path = str(file_path.relative_to(root))
    except ValueError:
        rel_path = str(file_path)

    try:
        text = file_path.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        return {"nodes": [], "edges": [], "input_tokens": 0, "output_tokens": 0,
                "error": str(e)}

    # 跳过空文件
    if not text.strip():
        return {"nodes": [], "edges": [], "input_tokens": 0, "output_tokens": 0}

    # 准备提示词
    user_message = prepare_extraction_prompt(text, rel_path)
    messages = [
        {"role": "system", "content": CHINESE_EXTRACTION_SYSTEM},
        {"role": "user", "content": user_message},
    ]

    result = call_llm(backend, messages, model=model)

    if result["error"]:
        print(f"  ⚠️  {rel_path}: LLM 调用失败 — {result['error']}", file=sys.stderr)
        return {"nodes": [], "edges": [], "input_tokens": result["input_tokens"],
                "output_tokens": result["output_tokens"], "error": result["error"]}

    content = result["content"]
    if not content:
        return {"nodes": [], "edges": [], "input_tokens": result["input_tokens"],
                "output_tokens": result["output_tokens"]}

    # 清理 JSON (移除可能的 markdown 代码块标记)
    content = content.strip()
    if content.startswith("```"):
        content = re.sub(r'^```(?:json)?\s*', '', content)
        content = re.sub(r'\s*```$', '', content)
    content = content.strip()

    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        print(f"  ⚠️  {rel_path}: JSON 解析失败 — {e}", file=sys.stderr)
        return {"nodes": [], "edges": [], "input_tokens": result["input_tokens"],
                "output_tokens": result["output_tokens"], "error": str(e)}

    if not isinstance(data, dict):
        return {"nodes": [], "edges": [], "input_tokens": result["input_tokens"],
                "output_tokens": result["output_tokens"]}

    data.setdefault("nodes", [])
    data.setdefault("edges", [])
    data["input_tokens"] = result["input_tokens"]
    data["output_tokens"] = result["output_tokens"]

    # 补充 source_file
    for node in data["nodes"]:
        node.setdefault("source_file", rel_path)
    for edge in data["edges"]:
        edge.setdefault("source_file", rel_path)

    return data


def list_available_backends() -> str:
    """列出所有可用的国产 LLM 后端"""
    lines = ["📋 支持的中文 LLM 后端：\n"]
    for key, cfg in LLM_CONFIGS.items():
        status, msg = check_env(key)
        icon = "✅" if status else "⬜"
        lines.append(f"  {icon} {cfg['name']:14s} — {cfg['default_model']}")
    lines.append(f"\n  使用: homo-graphify extract . --backend <name>")
    return "\n".join(lines)
