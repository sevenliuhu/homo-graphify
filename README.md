# 📊 homo-graphify — 一键代码知识图谱 · 中文版

> 🔗 基于 graphify (50k+ ⭐) 深度汉化，支持 DeepSeek / 国产 LLM

**一条命令，你的整个项目变成可查询的知识图谱。**

```
homo-graphify extract .
```

三文件输出：

```
graphify-out/
├── graph.html        🌐 交互式图谱 — 浏览器打开，点击节点、筛选、搜索
├── GRAPH_REPORT.md   📝 架构分析报告 — 关键概念、隐藏关联、建议问题
└── graph.json        🔗 完整图谱数据 — 可随时查询，无需重读源文件
```

---

## ✨ 特性

| 特性 | 说明 |
|------|------|
| 🚀 **一键构建** | `homo-graphify extract .` 自动提取实体关系 |
| 🇨🇳 **中文原生** | 完美支持中文变量名、注释、文档中的实体识别 |
| 🤖 **国产 LLM** | 深度适配 DeepSeek、Kimi、通义千问、智谱 GLM、文心一言 |
| 💰 **极致省钱** | DeepSeek API 约 $0.14/百万 tokens，Kimi 约 $0.74/百万 tokens |
| 🏠 **完全离线** | 支持 Ollama 本地模型，零 API 费用 |
| 🔌 **17 种平台** | Claude Code、Cursor、Gemini CLI、GitHub Copilot 等全支持 |

---

## 🚀 快速开始

### 安装

```bash
# 推荐方式（一键安装）
pip install homo-graphify

# 或者使用 uv（更快）
uv tool install homo-graphify

# 安装 LLM 支持
pip install homo-graphify[llm]
```

### 使用

```bash
# 1️⃣ 提取当前目录的知识图谱
homo-graphify extract .

# 2️⃣ 指定后端（默认 DeepSeek）
homo-graphify extract ./my-project --backend deepseek
homo-graphify extract ./my-project --backend kimi
homo-graphify extract ./my-project --backend qwen

# 3️⃣ 安装到 AI 编码助手
homo-graphify install  # 默认安装到 Claude Code
homo-graphify install --platform cursor
homo-graphify install --platform gemini

# 4️⃣ 查看国产 LLM 配置帮助
homo-graphify llm-guide
```

---

## 🤖 国产 LLM 配置

### DeepSeek（推荐 · 最便宜）

```bash
export DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
homo-graphify extract . --backend deepseek
```

👉 申请 API Key: https://platform.deepseek.com/api_keys

### Kimi（月之暗面 K2.6）

```bash
export MOONSHOT_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
homo-graphify extract . --backend kimi
```

👉 申请 API Key: https://platform.moonshot.cn/console/api-keys

### 通义千问（阿里云 Qwen）

```bash
export QWEN_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
homo-graphify extract . --backend qwen
```

👉 申请 API Key: https://help.aliyun.com/zh/model-studio/developer-reference/get-api-key

### 智谱 GLM

```bash
export ZHIPUAI_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
homo-graphify extract . --backend glm
```

👉 申请 API Key: https://open.bigmodel.cn/usercenter/apikeys

### 文心一言（百度 ERNIE）

```bash
export BAIDU_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
homo-graphify extract . --backend baidu
```

### Ollama（本地 · 完全免费）

```bash
# 1. 先启动 Ollama
ollama pull qwen2.5-coder:7b
ollama serve

# 2. 再运行
homo-graphify extract . --backend ollama
```

---

## 🔌 安装到 AI 编码助手

```bash
# Claude Code
homo-graphify install claude

# Cursor
homo-graphify install --platform cursor

# Gemini CLI
homo-graphify install --platform gemini

# GitHub Copilot
homo-graphify install --platform copilot

# VS Code Copilot Chat
homo-graphify install --platform vscode

# OpenClaw
homo-graphify install --platform claw

# 查看所有支持的平台
graphify --help
```

安装后在 AI 助手中输入 `/graphify .` 即可使用。

---

## 📂 输出说明

| 文件 | 用途 | 打开方式 |
|------|------|----------|
| `graphify-out/graph.html` | 交互式知识图谱 | 浏览器打开 |
| `graphify-out/GRAPH_REPORT.md` | 架构分析报告 | Markdown 阅读器 |
| `graphify-out/graph.json` | 完整图谱数据 | 程序化查询 |

进阶查询：

```bash
# 查询概念
graphify query "这个项目的核心架构是什么？"

# 查询两个节点的关系
graphify path "AuthService" "Database"

# 解释某个概念
graphify explain "依赖注入"
```

---

## 📞 联系方式

- 📧 邮箱：16208204@qq.com
- 📦 GitHub: https://github.com/sevenliuhu/homo-graphify

---

## ⚖️ License

MIT License — 基于 [graphify](https://github.com/safishamsi/graphify) (MIT, © Safi Shamsi)
