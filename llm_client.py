"""llm_client.py — 封装 DeepSeek 调用的模块（第二课：结构化 JSON 输出）"""

import json
import os
from openai import OpenAI
from dotenv import load_dotenv

# ---------- 基础配置 ----------
load_dotenv()

API_KEY = os.environ.get("DEEPSEEK_API_KEY")
if not API_KEY:
    raise SystemExit("没找到 DEEPSEEK_API_KEY，请先把它填进 .env 文件")

client = OpenAI(
    api_key=API_KEY,
    base_url="https://api.deepseek.com",
)

SYSTEM_PROMPT = "你是一个乐于助人的 AI 助手。"


# ---------- 功能 1：普通对话（第一课） ----------
def chat(user_message: str, system_prompt: str = SYSTEM_PROMPT) -> str:
    """发送一条用户消息，返回模型的文字回复。"""
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]
    response = client.chat.completions.create(
        model="deepseek-flash",
        messages=messages,
    )
    return response.choices[0].message.content


# ---------- 功能 2：结构化 JSON 输出（第二课） ----------
def chat_json(user_message: str, system_prompt: str = SYSTEM_PROMPT) -> dict:
    """让模型按 JSON 格式回答，并解析成 Python 字典。

    两个硬性规则（官方文档要求）：
    1. 用 response_format 锁定 JSON 模式；
    2. system 或 user 消息里必须出现 "json" 字样，否则会报错。
    """
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]
    response = client.chat.completions.create(
        model="deepseek-flash",
        messages=messages,
        response_format={"type": "json_object"},
    )
    # 模型返回的是"长得像 JSON 的文本"，必须自己解析成 Python 字典
    return parse_json_safely(response.choices[0].message.content)


# ---------- 功能 3：容错解析（边界 case 重灾区） ----------
def parse_json_safely(text: str) -> dict:
    """把模型输出的文本解析成 dict，处理常见的三种脏数据。"""
    text = text.strip()

    # 脏数据 1：模型用 ```json ... ``` 包裹（最常见）
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].strip()

    # 脏数据 2：前后夹带无关文字 → 只截取第一个 { 到最后一个 }
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        text = text[start : end + 1]

    # 脏数据 3：还是解析失败 → 抛出带原文的清晰错误，方便排查
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"模型返回的不是合法 JSON：{e}\n原文：{text}") from e


if __name__ == "__main__":
    # 自测 1：普通对话
    print("=== 测试 1：普通对话 ===")
    print(chat("用一句话解释什么是 Agent（智能体）？"))
    print()

    # 自测 2：从职位 JD 提取结构化信息（这就是后面要存进数据库的数据）
    print("=== 测试 2：JD → 结构化 JSON ===")
    sample_jd = """
    岗位名称：AI应用开发工程师
    岗位职责：负责LLM应用产品开发，包括Agent工作流搭建、Prompt优化、RAG知识库检索。
    任职要求：3年以上Python开发经验，熟悉Flask或FastAPI，熟悉OpenAI或DeepSeek API，
    有LangChain或Agent开发经验者优先。
    """
    system_prompt = (
        "你是一个职位信息提取助手。请从用户提供的职位描述中提取信息，"
        "并以 JSON 格式输出。字段必须包含："
        "job_title（岗位名称，字符串）、"
        "required_skills（技能列表，字符串数组）、"
        "years_experience（要求年限，字符串）、"
        "responsibilities（职责列表，字符串数组）。"
    )
    result = chat_json(sample_jd, system_prompt=system_prompt)
    print(json.dumps(result, ensure_ascii=False, indent=2))
