# AI 求职助手（AI Job Assistant）

一个以 **Agent 应用开发** 为核心思路的求职辅助工具：把职位描述（JD）交给大模型做结构化提取，与你的简历做匹配打分，并提供能自主调用工具的 **Agent 求职顾问**。

> 求职作品项目 · 由 Python 从零构建 · 用于展示 LLM 应用 / Agent 开发能力

## 核心功能

| 功能 | 说明 |
| ---- | ---- |
| JD 结构化提取 | 粘贴任意职位描述，自动提取岗位名、技能、职责、年限要求（结构化 JSON） |
| JD × 简历匹配打分 | 结合主简历，输出匹配分数、命中/缺失技能、风险与建议 |
| Agent 求职顾问 | 输入求职目标，模型自主决定调用 `search_jobs` / `match_job` 工具，多轮循环后给出综合建议 |

## 技术栈

- Python 3.14 · Flask 3.1 · SQLite
- DeepSeek API（OpenAI 兼容接口，openai SDK）
- 分层架构：通用 LLM 调用层 / 数据存取层 / 业务层 / Web 表现层

## 架构

```
JD/求职目标输入
        │
        ▼
┌──────────────┐      ┌──────────────┐      ┌────────────────┐
│    app.py    │─────▶│  matcher.py  │─────▶│  llm_client.py │─────▶ DeepSeek API
│   (Flask)    │      │ (提取/匹配)   │      │   (chat_json)  │
└──────────────┘      └──────┬───────┘      └────────────────┘
                             │
                       ┌─────▼──────┐
                       │   db.py    │  SQLite（jobs / resumes）
                       └────────────┘

agent.py：Agent 循环（tools schema → tool_calls → 执行工具 → 结果回传 → 综合回答）
prompts.py：提示词集中管理（提取 / 匹配 / Agent 三套 system prompt）
```

## 快速开始

```bash
git clone <你的仓库地址>
cd ai-job-assistant
python -m venv venv
venv\Scripts\activate        # Windows；macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
```

1. 在 [DeepSeek 开放平台](https://platform.deepseek.com) 创建 API Key
2. `copy .env.example .env`，把 `DEEPSEEK_API_KEY` 填成你的 key
3. 初始化演示数据：`python db.py`（存入示例职位 + 主简历，之后可在 db.py 里改成你的真实简历）
4. 启动：`python app.py`，打开 http://127.0.0.1:5000

## 页面

- `/` —— 职位匹配：粘贴 JD → 自动提取 → 匹配打分
- `/agent` —— Agent 求职顾问：输入求职目标 → 模型自主调工具 → 综合求职建议（含决策轨迹展示）

## 设计亮点（面试可讲）

- **提示词集中管理**（`prompts.py`）：字段定义精确到互斥（如 `risks` 不重复 `missing_skills`），改提示词不翻业务代码
- **容错 JSON 解析**：模型输出带 ```json 包裹、夹带废话都能兜底，失败时给出带原文的清晰错误
- **Agent 循环安全阀**：`max_rounds` 限制轮数，防止模型无限调用工具
- **分层架构**：路由层零 SQL、零 API 调用；Agent 工具直接复用业务函数
- **边界 case 全覆盖**：空输入、无简历、模型调用失败都在页面友好提示

## 待改进

- 职位去重（JD 指纹 + UNIQUE 约束）
- 接入真实职位源（爬虫 / 职位 API）
- 回答的 Markdown 渲染、简历文件上传
- 部署上线（见下方在线演示）

## 在线演示

（部署后填写）
