#!/usr/bin/env python3
"""homo-graphify CLI — 中文适配版一键代码知识图谱"""
from __future__ import annotations
import json
import os
import sys
import shutil
import subprocess
from pathlib import Path

from . import __version__, VERSION_STRING

# ── 依赖检查 ──────────────────────────────────────────────

def _check_graphify_installed() -> bool:
    """检查 graphifyy 是否已安装"""
    try:
        subprocess.run(
            ["graphify", "--version"],
            capture_output=True, timeout=5
        )
        return True
    except (FileNotFoundError, subprocess.SubprocessError):
        pass
    try:
        import graphify  # noqa
        return True
    except ImportError:
        return False


def _install_graphify() -> None:
    """自动安装 graphifyy 依赖"""
    print("📦 正在安装 graphifyy 依赖...")
    cmds = [
        ["uv", "tool", "install", "graphifyy"],
        ["pipx", "install", "graphifyy"],
        ["pip", "install", "graphifyy"],
    ]
    for cmd in cmds:
        try:
            r = subprocess.run(cmd, capture_output=True, text=True)
            if r.returncode == 0:
                print("✅ graphifyy 安装成功")
                return
        except FileNotFoundError:
            continue
    print("❌ 无法自动安装 graphifyy。请手动运行：")
    print("   pip install graphifyy")
    sys.exit(1)


# ── 中文增强 LLM 配置 ──────────────────────────────────────

CHINESE_LLM_BACKENDS = {
    "deepseek": {
        "name": "DeepSeek",
        "base_url": "https://api.deepseek.com",
        "default_model": "deepseek-chat",
        "env_key": "DEEPSEEK_API_KEY",
        "description": "DeepSeek V3/R1 — 国产最强推理模型",
    },
    "kimi": {
        "name": "Kimi (月之暗面)",
        "base_url": "https://api.moonshot.ai/v1",
        "default_model": "kimi-k2.6",
        "env_key": "MOONSHOT_API_KEY",
        "description": "Kimi K2.6 — 国产多模态推理模型",
    },
    "qwen": {
        "name": "通义千问 (Qwen)",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "default_model": "qwen3-235b-a22b",
        "env_key": "QWEN_API_KEY",
        "description": "阿里通义千问 — 国产大模型",
    },
    "glm": {
        "name": "智谱 GLM",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "default_model": "glm-6",
        "env_key": "ZHIPUAI_API_KEY",
        "description": "智谱 GLM-6 — 国产双语模型",
    },
    "baidu": {
        "name": "文心一言 (ERNIE)",
        "base_url": "https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat",
        "default_model": "ernie-4.5-8k",
        "env_key": "BAIDU_API_KEY",
        "description": "百度文心一言 ERNIE",
    },
    "stepfun": {
        "name": "阶跃星辰 (StepFun)",
        "base_url": "https://api.stepfun.com/v1",
        "default_model": "step-2",
        "env_key": "STEPFUN_API_KEY",
        "description": "阶跃星辰 Step-2",
    },
    "ollama": {
        "name": "Ollama (本地)",
        "base_url": "http://localhost:11434/v1",
        "default_model": "qwen2.5-coder:7b",
        "env_key": "OLLAMA_API_KEY",
        "description": "本地部署 — 推荐 qwen2.5-coder / deepseek-coder",
    },
}

# 为 graphify 原生后端添加中文别名映射
_BACKEND_ALIAS = {
    "deepseek": "deepseek",
    "moonshot": "kimi",
    "kimi": "kimi",
    "qwen": "qwen",
    "glm": "glm",
    "zhipu": "glm",
    "ernie": "baidu",
    "baidu": "baidu",
    "stepfun": "stepfun",
    "step": "stepfun",
}


def print_llm_guide() -> None:
    """打印国产 LLM 配置指南"""
    print("=" * 60)
    print("  🔧 国产 LLM 配置指南")
    print("=" * 60)
    for key, cfg in CHINESE_LLM_BACKENDS.items():
        print(f"\n  【{cfg['name']}】")
        print(f"    模型: {cfg['default_model']}")
        print(f"    说明: {cfg['description']}")
        print(f"    环境变量: {cfg['env_key']}")
        if key == "deepseek":
            print(f"    申请: https://platform.deepseek.com/api_keys")
        elif key == "kimi":
            print(f"    申请: https://platform.moonshot.cn/console/api-keys")
        elif key == "qwen":
            print(f"    申请: https://help.aliyun.com/zh/model-studio/developer-reference/get-api-key")
        elif key == "glm":
            print(f"    申请: https://open.bigmodel.cn/usercenter/apikeys")
        elif key == "baidu":
            print(f"    申请: https://console.bce.baidu.com/iam/#/iam/accesskey")
        elif key == "stepfun":
            print(f"    申请: https://platform.stepfun.com/request-key")
        elif key == "ollama":
            print(f"    安装: curl -fsSL https://ollama.com/install.sh | sh")
    print()
    print("  📝 使用示例：")
    print("     export DEEPSEEK_API_KEY=sk-xxxx")
    print("     homo-graphify extract . --backend deepseek")
    print()
    print("     export MOONSHOT_API_KEY=sk-xxxx")
    print("     homo-graphify extract . --backend kimi")
    print()
    print("  💡 推荐配置（免费/廉价）：")
    print("     1. DeepSeek: 最便宜，v3 推理强")
    print("     2. Ollama: 完全免费，本地运行")
    print("=" * 60)


# ── 主 CLI ────────────────────────────────────────────────

HELP_TEXT = f"""{VERSION_STRING}
📊 一键代码知识图谱 · 中文适配版
基亍 graphify (50k+⭐) 深度汉化，支持 DeepSeek/国产 LLM

用法: homo-graphify <command> [options]

命令:
  extract <path>    一键提取代码知识图谱
      --backend       LLM 后端：deepseek|kimi|qwen|glm|ollama (默认: deepseek)
      --model         指定模型名称
      --out DIR       输出目录

  install           安装 graphify 到 AI 编码助手
      --platform      平台: claude|codex|cursor|gemini|aider|opencode (默认: claude)

  llm-guide         查看国产 LLM 配置指南
  version, -v       显示版本信息
  help, -h          显示帮助

  更多 graphify 原生命令请运行: graphify --help

示例:
  homo-graphify extract .    # 提取当前目录的知识图谱
  homo-graphify extract ./src --backend deepseek --model deepseek-chat
  homo-graphify install --platform cursor
  homo-graphify llm-guide

输出:
  graphify-out/
  ├── graph.html        交互式知识图谱（浏览器打开）
  └── GRAPH_REPORT.md   架构分析报告

联系方式: 16208204@qq.com
"""


def main() -> None:
    if len(sys.argv) < 2:
        print(HELP_TEXT)
        return

    cmd = sys.argv[1]

    if cmd in ("-v", "--version", "version"):
        print(VERSION_STRING)
        return

    if cmd in ("-h", "--help", "help"):
        print(HELP_TEXT)
        return

    if cmd == "llm-guide":
        print_llm_guide()
        return

    if cmd == "install":
        # 快速安装：先确保 graphifyy 已安装
        if not _check_graphify_installed():
            _install_graphify()

        platform = "claude"
        if len(sys.argv) >= 4 and sys.argv[2] == "--platform":
            platform = sys.argv[3]
        elif len(sys.argv) >= 3 and not sys.argv[2].startswith("-"):
            platform = sys.argv[2]

        env_hint = ""
        if platform in ("claude",):
            env_hint = "\n💡 提示：使用国产 LLM 请设置环境变量，如: export DEEPSEEK_API_KEY=sk-xxxx"

        print(f"\n📦 正在安装到 {platform}...")
        r = subprocess.run(["graphify", "install", platform])
        if r.returncode == 0:
            print(f"✅ 安装成功！在 AI 编码助手中输入 /graphify . 即可使用{env_hint}")
        else:
            print("❌ 安装失败，请检查 graphify 是否安装正确")
        return

    if cmd == "extract":
        # 解析参数
        target = "."
        backend = "deepseek"
        model = None
        extra_args = []

        i = 2
        while i < len(sys.argv):
            a = sys.argv[i]
            if a == "--backend" and i + 1 < len(sys.argv):
                backend = sys.argv[i + 1]
                i += 2
            elif a == "--model" and i + 1 < len(sys.argv):
                model = sys.argv[i + 1]
                i += 2
            elif a.startswith("--backend="):
                backend = a.split("=", 1)[1]
                i += 1
            elif a.startswith("--model="):
                model = a.split("=", 1)[1]
                i += 1
            elif a.startswith("-"):
                extra_args.append(a)
                i += 1
            else:
                target = a
                i += 1

        # 检查 graphifyy 是否安装
        if not _check_graphify_installed():
            _install_graphify()

        # 映射后端别名
        backend_real = _BACKEND_ALIAS.get(backend, backend)

        # 设置环境变量提示
        env_key = None
        for key, cfg in CHINESE_LLM_BACKENDS.items():
            if key == backend_real:
                env_key = cfg["env_key"]
                break

        print(f"\n🔍 homo-graphify extract {target}")
        print(f"   LLM 后端: {backend}")
        if env_key and not os.environ.get(env_key):
            print(f"   ⚠️  未设置 {env_key} 环境变量")
            if env_key == "OLLAMA_API_KEY":
                print(f"   使用 Ollama 本地模型，无需 API Key")
            elif backend_real == "deepseek":
                print(f"   请设置: export DEEPSEEK_API_KEY=sk-xxxx")
                print(f"   申请: https://platform.deepseek.com/api_keys")

        # 构建 graphify extract 命令
        cmd_parts = ["graphify", "extract", target,
                     "--backend", backend_real]
        if model:
            cmd_parts.extend(["--model", model])
        cmd_parts.extend(extra_args)

        print(f"\n🚀 运行: {' '.join(cmd_parts)}\n")

        r = subprocess.run(cmd_parts)
        if r.returncode == 0:
            print(f"\n✅ 知识图谱构建完成！")
            out_dir = Path(target) / "graphify-out"
            if out_dir.exists():
                html = out_dir / "graph.html"
                report = out_dir / "GRAPH_REPORT.md"
                print(f"\n📂 输出目录: {out_dir}/")
                if html.exists():
                    print(f"   🌐 graph.html — 打开浏览器查看交互式图谱")
                if report.exists():
                    print(f"   📝 GRAPH_REPORT.md — 查看架构分析报告")
        else:
            print(f"\n❌ 提取失败，请检查错误信息")
        return

    # 未知命令 — 尝试透传到 graphify 自身
    print(f"⚠️  未知命令: {cmd}")
    print(f"💡 尝试将命令透传到 graphify...\n")
    r = subprocess.run(["graphify"] + sys.argv[1:])
    sys.exit(r.returncode)


if __name__ == "__main__":
    main()
