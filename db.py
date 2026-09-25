"""db.py — SQLite 存取层（第三课：职位表；第四课：简历表）"""

import json
import os
import sqlite3

# 数据库文件固定放在 db.py 旁边：不管从哪里启动（本地命令行 / 云端 WSGI），
# 都不会因为"当前目录"不同而把数据写到奇怪的地方
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jobs.db")


def get_conn():
    """每次操作新建一个连接。用完后必须 close，否则可能锁库。"""
    return sqlite3.connect(DB_PATH)


def init_db():
    """建表。IF NOT EXISTS 让它可以重复执行（幂等），不会报错。"""
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_title TEXT NOT NULL,
            years_experience TEXT,
            required_skills TEXT,   -- 技能是数组，SQLite 没有数组类型，存 JSON 字符串
            responsibilities TEXT,  -- 同理
            created_at TEXT DEFAULT (datetime('now', 'localtime'))
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS resumes (
            id INTEGER PRIMARY KEY,   -- 主简历固定用 id=1，方便读取
            name TEXT,
            education TEXT,
            status TEXT,
            skills TEXT,              -- JSON 字符串
            projects TEXT,
            updated_at TEXT DEFAULT (datetime('now', 'localtime'))
        )
    """)
    conn.commit()
    conn.close()


# ---------- 职位 ----------

def save_job(job: dict) -> int:
    """把 chat_json 返回的 dict 存进数据库，返回新记录的 id。"""
    conn = get_conn()
    cur = conn.execute(
        """
        INSERT INTO jobs (job_title, years_experience, required_skills, responsibilities)
        VALUES (?, ?, ?, ?)
        """,
        (
            job.get("job_title", "未命名岗位"),  # 边界 case：模型漏了字段就填默认值
            job.get("years_experience", ""),
            json.dumps(job.get("required_skills", []), ensure_ascii=False),
            json.dumps(job.get("responsibilities", []), ensure_ascii=False),
        ),
    )
    conn.commit()
    new_id = cur.lastrowid  # 拿数据库自动生成的 id
    conn.close()
    return new_id


def list_jobs() -> list:
    """查出全部职位，把 JSON 字符串还原成列表再返回。"""
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, job_title, years_experience, required_skills, responsibilities, created_at "
        "FROM jobs ORDER BY id DESC"
    ).fetchall()
    conn.close()
    return [
        {
            "id": row[0],
            "job_title": row[1],
            "years_experience": row[2],
            "required_skills": json.loads(row[3] or "[]"),
            "responsibilities": json.loads(row[4] or "[]"),
            "created_at": row[5],
        }
        for row in rows
    ]


def get_latest_job() -> dict | None:
    """取出最新存入的一条职位（匹配演示用）。没数据返回 None。"""
    conn = get_conn()
    row = conn.execute(
        "SELECT id, job_title, years_experience, required_skills, responsibilities, created_at "
        "FROM jobs ORDER BY id DESC LIMIT 1"
    ).fetchone()
    conn.close()
    if row is None:
        return None
    return {
        "id": row[0],
        "job_title": row[1],
        "years_experience": row[2],
        "required_skills": json.loads(row[3] or "[]"),
        "responsibilities": json.loads(row[4] or "[]"),
        "created_at": row[5],
    }


# ---------- 简历 ----------

def save_resume(resume: dict) -> None:
    """保存主简历。id 固定为 1，重复保存会覆盖旧内容（INSERT OR REPLACE）。"""
    conn = get_conn()
    conn.execute(
        """
        INSERT OR REPLACE INTO resumes
            (id, name, education, status, skills, projects)
        VALUES (1, ?, ?, ?, ?, ?)
        """,
        (
            resume.get("name", ""),
            resume.get("education", ""),
            resume.get("status", ""),
            json.dumps(resume.get("skills", []), ensure_ascii=False),
            resume.get("projects", ""),
        ),
    )
    conn.commit()
    conn.close()


def get_resume() -> dict | None:
    """读取主简历，技能还原成列表。没存过返回 None。"""
    conn = get_conn()
    row = conn.execute(
        "SELECT name, education, status, skills, projects FROM resumes WHERE id = 1"
    ).fetchone()
    conn.close()
    if row is None:
        return None
    return {
        "name": row[0],
        "education": row[1],
        "status": row[2],
        "skills": json.loads(row[3] or "[]"),
        "projects": row[4],
    }


# ---------- 演示/初始化数据 ----------

DEMO_RESUME = {
    "name": "姚蕃淇",
    "education": "本科 · 计算机科学与技术",
    "status": "待业，全职求职中（目标：Agent 应用开发）",
    "skills": ["Python", "Flask", "SQLite", "REST API", "Git", "算法与数据结构", "DeepSeek API", "提示词工程", "Agent 概念"],
    "projects": "AI求职助手（当前项目）：用 Flask + SQLite + DeepSeek API 实现职位信息提取与匹配打分",
}


def seed_if_empty() -> None:
    """第一次运行时若没有主简历，自动写入演示简历。

    部署环境的数据库是全新的，没人能手动执行 python db.py，
    所以应用启动时自动初始化，保证演示页面直接可用。
    """
    if get_resume() is None:
        save_resume(DEMO_RESUME)
        print("已自动写入演示简历")


if __name__ == "__main__":
    # 演示数据：存一条示例职位 + 一份主简历
    from llm_client import chat_json
    from prompts import EXTRACT_SYSTEM_PROMPT

    init_db()

    sample_jd = """
    岗位名称：AI应用开发工程师
    岗位职责：负责LLM应用产品开发，包括Agent工作流搭建、Prompt优化、RAG知识库检索。
    任职要求：3年以上Python开发经验，熟悉Flask或FastAPI，熟悉OpenAI或DeepSeek API，
    有LangChain或Agent开发经验者优先。
    """
    job = chat_json(sample_jd, system_prompt=EXTRACT_SYSTEM_PROMPT)
    job_id = save_job(job)
    print(f"已存入职位 #{job_id}")

    # 主简历：按你的真实情况填好了，以后随时来改 DEMO_RESUME
    save_resume(DEMO_RESUME)
    print("已保存主简历")

    print("=== 数据库里的职位 ===")
    for j in list_jobs():
        print(f"[{j['id']}] {j['job_title']} | 年限: {j['years_experience']} | 技能: {j['required_skills']}")

    r = get_resume()
    print("=== 数据库里的简历 ===")
    print(f"{r['name']} | {r['education']} | 技能: {r['skills']}")
