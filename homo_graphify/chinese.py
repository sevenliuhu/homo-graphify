"""中文实体识别与 NLP 增强模块

支持从中文代码、文档中提取实体和关系。
适用于包含中文标识符、中文注释、中文文档的项目。
"""
from __future__ import annotations
import re
from pathlib import Path

# ── 中文标识符检测 ──────────────────────────────────────────

# 中文字符 Unicode 范围
CJK_RANGES = (
    (0x4E00, 0x9FFF),   # CJK 统一表意文字
    (0x3400, 0x4DBF),   # CJK 统一表意文字扩展 A
    (0x2E80, 0x2EFF),   # CJK 部首补充
    (0x3000, 0x303F),   # CJK 符号和标点
    (0xFF00, 0xFFEF),   # 全角 ASCII / 半角片假名
    (0xF900, 0xFAFF),   # CJK 兼容表意文字
    (0x2F800, 0x2FA1F), # CJK 兼容表意文字补充
)

_CJK_PATTERN = re.compile(
    "[" + "".join(
        f"\\u{start:04X}-\\u{end:04X}"
        for start, end in CJK_RANGES
    ) + "]"
)


def has_chinese(text: str) -> bool:
    """检测字符串中是否包含中文字符"""
    return bool(_CJK_PATTERN.search(text))


def chinese_ratio(text: str) -> float:
    """计算字符串中中文字符占比"""
    if not text:
        return 0.0
    total = len(text)
    cjk_count = len(_CJK_PATTERN.findall(text))
    return cjk_count / total if total > 0 else 0.0


def extract_chinese_entities(text: str) -> list[dict]:
    """从文本中提取中文实体（函数名、类名、变量名等）

    返回 [{"name": "...", "kind": "function|class|variable"}]
    """
    entities = []

    # 中文函数定义: def 函数名(...)
    func_pattern = re.compile(
        r'(?:def|function|func|fn)\s+'
        r'([\u4e00-\u9fff\w]+)'
        r'\s*\(',
        re.MULTILINE
    )
    for m in func_pattern.finditer(text):
        name = m.group(1)
        if has_chinese(name):
            entities.append({"name": name, "kind": "function"})

    # 中文类定义: class 类名
    class_pattern = re.compile(
        r'(?:class|class|type)\s+'
        r'([\u4e00-\u9fff\w]+)',
        re.MULTILINE
    )
    for m in class_pattern.finditer(text):
        name = m.group(1)
        if has_chinese(name):
            entities.append({"name": name, "kind": "class"})

    # 中文变量赋值: 变量名 = ...
    var_pattern = re.compile(
        r'^\s*([\u4e00-\u9fff\w]+)\s*[=:=]\s*',
        re.MULTILINE
    )
    for m in var_pattern.finditer(text):
        name = m.group(1)
        if has_chinese(name) and chinese_ratio(name) > 0.5:
            entities.append({"name": name, "kind": "variable"})

    # 中文注释中的关键概念
    comment_pattern = re.compile(
        r'#.*?[\u4e00-\u9fff]+.*?$|//.*?[\u4e00-\u9fff]+.*?$|'
        r'/\*[\s\S]*?[\u4e00-\u9fff]+[\s\S]*?\*/',
        re.MULTILINE
    )
    for m in comment_pattern.finditer():
        comment = m.group(0)
        # 从注释中提取中文关键词
        keywords = re.findall(
            r'[\u4e00-\u9fff]{2,}(?:[（(][^)）]*[)）])?',
            comment
        )
        for kw in keywords:
            kw_clean = kw.strip()
            if len(kw_clean) >= 2 and chinese_ratio(kw_clean) > 0.5:
                entities.append({
                    "name": kw_clean,
                    "kind": "concept",
                    "source": "comment"
                })

    return entities


# ── 中文文档分析 ──────────────────────────────────────────

def analyze_chinese_doc(path: Path) -> dict | None:
    """分析包含中文的文档文件，提取结构和关键信息

    返回结构化的文档分析结果，可用于知识图谱节点
    """
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return None

    if not has_chinese(text):
        return None

    result = {
        "has_chinese": True,
        "chinese_ratio": chinese_ratio(text),
        "entities": extract_chinese_entities(text),
        "sections": [],
    }

    # 提取 Markdown 标题结构
    for m in re.finditer(r'^(#{1,6})\s+(.+)$', text, re.MULTILINE):
        level = len(m.group(1))
        title = m.group(2).strip()
        result["sections"].append({
            "level": level,
            "title": title,
        })

    return result


# ── 文件名 / 路径中文检测 ──────────────────────────────────

def has_chinese_path(path: Path) -> bool:
    """检测路径中是否包含中文字符"""
    return any(has_chinese(part) for part in path.parts)


def sanitize_chinese_id(text: str) -> str:
    """将包含中文的文本转换为安全的节点 ID

    保留中文拼音/英文部分，中文直接保留（支持 Unicode）
    """
    # 保留中文、字母、数字、下划线
    # 中文在 _make_id 中由 graphify 原生的 unicodedata.normalize 处理
    return text


# ── 中文编程语言检测 ──────────────────────────────────────

# 常见的带有中文标识符的编程语言和框架
CHINESE_CODE_SIGNALS = [
    # 中文注释开头
    re.compile(r'^#\s*[\u4e00-\u9fff]', re.MULTILINE),
    re.compile(r'^//\s*[\u4e00-\u9fff]', re.MULTILINE),
    # 中文变量名
    re.compile(r'(?:var|let|const)\s+[\u4e00-\u9fff]+\s*='),
    # 中文函数名
    re.compile(r'def\s+[\u4e00-\u9fff]+[\u4e00-\u9fff\w]*\s*\('),
    # 中文类名
    re.compile(r'class\s+[\u4e00-\u9fff]+[\u4e00-\u9fff\w]*'),
    # 中文文档字符串
    re.compile(r'"""[\s\S]*?[\u4e00-\u9fff]+[\s\S]*?"""'),
    re.compile(r"'''[\s\S]*?[\u4e00-\u9fff]+[\s\S]*?'''"),
]


def detect_chinese_code(path: Path) -> bool:
    """检测源代码文件是否包含中文标识符或注释"""
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return False

    # 快速过滤：至少要有中文字符
    if not has_chinese(text):
        return False

    # 检查中文密度
    ratio = chinese_ratio(text)
    if ratio > 0.1:
        return True

    # 检查信号模式
    for pattern in CHINESE_CODE_SIGNALS:
        if pattern.search(text):
            return True

    return False


# ── 中文项目元数据检测 ────────────────────────────────────

CHINESE_PROJECT_FILES = {
    "README.zh-CN.md",
    "README.zh_CN.md",
    "README.zh.md",
    "README.中文.md",
    "中文文档.md",
    "CONTRIBUTING.zh-CN.md",
    "CHANGELOG.zh-CN.md",
}


def is_chinese_project(root: Path) -> bool:
    """检测项目是否为中文项目

    检查：
    1. 存在中文 README 文件
    2. 源码中有中文标识符/注释
    """
    # 检查中文项目文件
    for f in CHINESE_PROJECT_FILES:
        if (root / f).exists():
            return True

    # 快速采样几个源码文件
    for ext in [".py", ".js", ".ts", ".java", ".rs", ".go", ".md"]:
        for f in root.rglob(f"*{ext}"):
            if f.is_file() and f.stat().st_size < 100000:  # 小于 100KB
                try:
                    text = f.read_text(encoding="utf-8", errors="ignore")[:2000]
                    if has_chinese(text) and chinese_ratio(text) > 0.05:
                        return True
                except Exception:
                    continue
            break  # 每种扩展名只检查第一个文件

    return False


# ── 输出中文增强的提取结果 ──────────────────────────────────

def enhance_with_chinese(
    nodes: list[dict],
    edges: list[dict],
    file_paths: list[Path],
    root: Path,
) -> tuple[list[dict], list[dict]]:
    """对提取结果进行中文增强

    为包含中文的文件添加额外的语义节点和关系。
    """
    extra_nodes: list[dict] = []
    extra_edges: list[dict] = []

    for fp in file_paths:
        try:
            rel = str(fp.relative_to(root))
        except ValueError:
            rel = str(fp)

        # 跳过非文本文件
        ext = fp.suffix.lower()
        if ext in ('.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg',
                    '.mp4', '.mov', '.avi', '.pdf'):
            continue

        # 检测中文内容
        if detect_chinese_code(fp):
            # 添加中文项目标签
            extra_nodes.append({
                "id": f"chinese_file_{_safe_id(rel)}",
                "label": f"中文文件: {fp.name}",
                "file_type": "code",
                "source_file": rel,
                "source_location": None,
            })

        # 提取中文实体
        try:
            text = fp.read_text(encoding="utf-8", errors="ignore")
            entities = extract_chinese_entities(text)
            for ent in entities:
                nid = f"chinese_entity_{_safe_id(ent['name'])}"
                extra_nodes.append({
                    "id": nid,
                    "label": ent["name"],
                    "file_type": "concept",
                    "source_file": rel,
                    "source_location": None,
                })
        except Exception:
            pass

    return extra_nodes, extra_edges


def _safe_id(s: str) -> str:
    """生成安全的 ID 片段"""
    import unicodedata
    s = unicodedata.normalize("NFKC", s)
    s = re.sub(r"[^\w]+", "_", s, flags=re.UNICODE)
    s = re.sub(r"_+", "_", s)
    return s.strip("_").lower()[:64]
