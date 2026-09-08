"""裁判模型评分（用于开放式主观题）"""
import json
import re

from . import llm

JUDGE_PROMPT_TEMPLATE = """你是一位严格、公正的 AI 评测裁判。请根据评分标准，为下面这个 AI 助手对用户问题的回答打分。

【用户问题】
{question}

【AI 助手的回答】
{answer}

【评分标准】
{rubric}

【参考答案（供参考，非唯一标准）】
{reference}

请只输出一个 JSON 对象，格式如下（不要输出任何其他内容）：
{{"score": <0 到 {max_score} 之间的数字>, "reason": "<一句话中文评分理由>"}}
"""


async def judge_answer(judge_model: dict, question: dict, answer: str) -> tuple[float, str]:
    """用裁判模型给开放式回答打分，返回 (得分, 评分理由)"""
    rubric = question.get("rubric") or "从正确性、完整性和表达质量三个维度综合评分。"
    reference = question.get("reference") or "无"
    max_score = question.get("max_score") or 10
    prompt = JUDGE_PROMPT_TEMPLATE.format(
        question=question["prompt"],
        answer=answer or "（空回答）",
        rubric=rubric,
        reference=reference,
        max_score=max_score,
    )
    text, _, error = await llm.chat_once(judge_model, [{"role": "user", "content": prompt}])
    if error or not text:
        return 0.0, f"裁判调用失败: {error or '无输出'}"
    # 提取 JSON
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return 0.0, f"裁判输出无法解析: {text[:120]}"
    try:
        data = json.loads(m.group(0))
        score = float(data.get("score", 0))
        reason = str(data.get("reason", ""))[:300]
        score = max(0.0, min(float(max_score), score))
        return score, reason
    except (ValueError, TypeError):
        # 尝试从文本中提取数字
        nums = re.findall(r"\d+(?:\.\d+)?", text)
        if nums:
            try:
                score = max(0.0, min(float(max_score), float(nums[0])))
                return score, f"（解析降级）{text[:200]}"
            except ValueError:
                pass
        return 0.0, f"裁判输出解析失败: {text[:120]}"
