"""app.py — Flask 网页入口（第五课：职位匹配；第七课：Agent 模式）"""

from flask import Flask, render_template, request

from agent import run_agent
from db import get_resume, save_job
from matcher import extract_job, match_job

app = Flask(__name__)


@app.route("/")
def index():
    """首页：粘贴 JD 的表单。"""
    return render_template("index.html")


@app.route("/match", methods=["POST"])
def match():
    """接收表单里的 JD → 提取 → 存库 → 匹配打分 → 渲染结果。"""
    jd_text = request.form.get("jd", "").strip()

    # 边界 case 1：JD 为空
    if not jd_text:
        return render_template("index.html", error="JD 不能为空，请粘贴一段职位描述。")

    # 边界 case 2：还没有简历
    resume = get_resume()
    if resume is None:
        return render_template(
            "index.html", error="数据库里还没有简历，请先在终端运行 python db.py 存入主简历。"
        )

    # 边界 case 3：模型调用失败（网络、余额、超时等），页面提示而不是白屏
    try:
        job = extract_job(jd_text)
        save_job(job)
        result = match_job(job, resume)
    except Exception as e:
        return render_template("index.html", error=f"匹配失败：{e}")

    return render_template("index.html", job=job, result=result)


@app.route("/agent")
def agent_page():
    """Agent 模式：输入求职目标，模型自主调用工具完成多步任务。"""
    return render_template("agent.html")


@app.route("/agent", methods=["POST"])
def agent_run():
    """接收求职目标 → 运行 Agent → 展示决策轨迹和最终回答。"""
    goal = request.form.get("goal", "").strip()

    if not goal:
        return render_template("agent.html", error="请先输入你的求职目标。")

    try:
        result = run_agent(goal)
    except Exception as e:
        return render_template("agent.html", error=f"Agent 运行失败：{e}")

    return render_template(
        "agent.html", goal=goal, trace=result["trace"], answer=result["answer"]
    )


if __name__ == "__main__":
    # 生产环境配置：平台会注入 PORT 环境变量；FLASK_DEBUG=1 时才开启调试模式
    import os

    debug = os.environ.get("FLASK_DEBUG") == "1"
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=debug)
