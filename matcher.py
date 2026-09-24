"""matcher.py — 职位提取与匹配打分（第四/五课）"""

import json

from db import get_latest_job, get_resume
from llm_client import chat_json
from prompts import EXTRACT_SYSTEM_PROMPT, MATCH_SYSTEM_PROMPT


def extract_job(jd_text: str) -> dict:
    """从一段 JD 文本提取结构化职位信息。"""
    return chat_json(jd_text, system_prompt=EXTRACT_SYSTEM_PROMPT)


def format_resume(resume: dict) -> str:
    """把简历字典拼成给模型看的文本。"""
    return (
        f"姓名：{resume['name']}\n"
        f"学历：{resume['education']}\n"
        f"状态：{resume['status']}\n"
        f"技能：{', '.join(resume['skills'])}\n"
        f"项目经验：{resume['projects']}"
    )


def build_match_prompt(job: dict, resume: dict) -> str:
    """把职位 + 简历拼成一条 user 消息。"""
    return (
        f"【职位描述】\n"
        f"岗位名称：{job['job_title']}\n"
        f"要求年限：{job['years_experience']}\n"
        f"要求技能：{', '.join(job['required_skills'])}\n"
        f"岗位职责：{', '.join(job['responsibilities'])}\n\n"
        f"【候选人简历】\n{format_resume(resume)}"
    )


def match_job(job: dict, resume: dict) -> dict:
    """输入职位 + 简历，返回匹配评估（JSON 已解析成 dict）。"""
    return chat_json(build_match_prompt(job, resume), system_prompt=MATCH_SYSTEM_PROMPT)


if __name__ == "__main__":
    job = get_latest_job()
    resume = get_resume()
    # 边界 case：数据没准备好就给出清晰的提示，而不是神秘崩溃
    if job is None or resume is None:
        raise SystemExit("数据库里没有职位或简历，请先运行 python db.py")

    print(f"=== 正在匹配：{job['job_title']} ===")
    result = match_job(job, resume)
    print(json.dumps(result, ensure_ascii=False, indent=2))
