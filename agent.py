"""agent.py — Agent 循环：让模型自己决定调用哪些工具（第六课，P2 核心）

这是整个项目最"Agent"的部分：模型不再被动回答问题，
而是主动决定"我需要 search_jobs 找职位"、"我需要 match_job 做评估"，
一步步拿到信息后，再综合给出最终回答。
"""

import json

from db import get_resume
from llm_client import client
from matcher import match_job

# ---------- 工具 1：内置职位库 ----------
# 真实项目里这里会接爬虫或职位 API；先用内置数据演示 Agent 循环本身
SAMPLE_JOBS = [
    {
        "id": "s1",
        "job_title": "AI应用开发工程师（初级）",
        "company": "示例公司A",
        "years_experience": "1-3年",
        "required_skills": ["Python", "Flask", "DeepSeek API", "RAG", "Agent 开发"],
        "responsibilities": ["LLM应用开发", "Agent工作流搭建", "Prompt优化"],
    },
    {
        "id": "s2",
        "job_title": "Agent 应用开发实习生",
        "company": "示例公司B",
        "years_experience": "不限",
        "required_skills": ["Python", "FastAPI", "LangChain", "Function Calling"],
        "responsibilities": ["Agent 工具调用开发", "Prompt 工程", "数据接入"],
    },
    {
        "id": "s3",
        "job_title": "RAG 检索工程师",
        "company": "示例公司C",
        "years_experience": "2-4年",
        "required_skills": ["Python", "向量数据库", "RAG", "Elasticsearch"],
        "responsibilities": ["知识库搭建", "检索链路优化"],
    },
]


def search_jobs(keyword: str) -> list:
    """按关键词过滤内置职位库，返回匹配的职位列表。"""
    kw = keyword.lower()
    hits = []
    for job in SAMPLE_JOBS:
        text = " ".join(
            [job["job_title"], job["company"], *job["required_skills"], *job["responsibilities"]]
        ).lower()
        if kw in text:
            hits.append(job)
    return hits


def handle_match_job(job_id: str) -> dict:
    """对内置职位库中的某条职位做匹配评估。"""
    job = next((j for j in SAMPLE_JOBS if j["id"] == job_id), None)
    if job is None:
        return {"error": f"找不到职位 id={job_id}"}
    resume = get_resume()
    if resume is None:
        return {"error": "数据库里没有简历，请先运行 python db.py"}
    return match_job(job, resume)


# ---------- 工具说明书（给模型看的 schema，OpenAI 兼容标准格式） ----------
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "search_jobs",
            "description": "根据关键词搜索职位，返回职位列表（含岗位名、公司、要求技能、职责）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {"type": "string", "description": "搜索关键词，如 Agent、Python、RAG"},
                },
                "required": ["keyword"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "match_job",
            "description": "用我的主简历对某条职位做匹配打分，返回分数、命中/缺失技能、风险和建议。",
            "parameters": {
                "type": "object",
                "properties": {
                    "job_id": {"type": "string", "description": "职位 id（search_jobs 返回的 id）"},
                },
                "required": ["job_id"],
            },
        },
    },
]


def execute_tool(name: str, args: dict):
    """根据工具名执行对应的 Python 函数。这是模型和真实世界之间的桥。"""
    if name == "search_jobs":
        return search_jobs(args["keyword"])
    if name == "match_job":
        return handle_match_job(args["job_id"])
    raise ValueError(f"未知工具：{name}")


AGENT_SYSTEM_PROMPT = (
    "你是一个求职规划 Agent。你可以调用工具获取信息："
    "search_jobs 搜索职位，match_job 评估我与某职位的匹配度。"
    "请根据用户的求职目标，主动决定调用哪些工具、调用几次，"
    "拿到结果后再综合分析，最后用中文给出完整的求职建议。"
    "只能依据工具返回的信息作答，不要编造工具没有返回的内容。"
)


def run_agent(user_goal: str, max_rounds: int = 5) -> dict:
    """运行 Agent 循环，返回 {"answer": 最终回答, "trace": 工具调用日志}。

    边界 case：max_rounds 限制轮数，防止模型陷入"无限调工具"死循环。
    """
    messages = [
        {"role": "system", "content": AGENT_SYSTEM_PROMPT},
        {"role": "user", "content": user_goal},
    ]
    trace = []  # 记录每一步工具调用，网页版要展示这个"决策轨迹"

    for _ in range(max_rounds):
        response = client.chat.completions.create(
            model="deepseek-flash",
            messages=messages,
            tools=TOOL_SCHEMAS,
        )
        msg = response.choices[0].message

        # 情况 1：模型要调用工具
        if msg.tool_calls:
            messages.append(msg)  # 先把模型这条"想调工具"的话记入对话历史
            for tc in msg.tool_calls:
                entry = f"调用工具: {tc.function.name}({tc.function.arguments})"
                trace.append(entry)
                print(f"  [Agent] {entry}")
                result = execute_tool(tc.function.name, json.loads(tc.function.arguments))
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,  # 把结果挂回对应的那次调用
                        "content": json.dumps(result, ensure_ascii=False),
                    }
                )
            continue  # 带着工具结果进入下一轮

        # 情况 2：模型直接给出最终回答
        return {"answer": msg.content, "trace": trace}

    raise SystemExit(f"Agent 循环超过最大轮数（{max_rounds}）仍没有结束，已终止")


if __name__ == "__main__":
    goal = (
        "我想找 Python / Agent 应用开发方向的初级岗位。"
        "请帮我搜索合适的职位，对它们逐一做匹配评估，"
        "最后按匹配度排序给出我的求职建议和学习优先级。"
    )
    print("=== Agent 开始工作 ===")
    result = run_agent(goal)
    print("=== 最终回答 ===")
    print(result["answer"])
