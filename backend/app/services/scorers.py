"""客观题自动评分器"""
import json
import re
import subprocess
import tempfile
from pathlib import Path


def _normalize(text: str) -> str:
    text = (text or "").strip().lower()
    text = re.sub(r"[\s,，。.!！?？、;；:：]+", "", text)
    return text


def score_choice(answer: str, question: dict) -> float:
    """选择题：匹配选项字母或选项文本"""
    expected = json.loads(question.get("expected") or "[]")
    options = json.loads(question.get("options") or "[]")
    if not expected:
        return 0.0
    exp = expected[0]
    # 期望值可能是字母
    if len(exp) == 1 and exp.isalpha():
        letter = exp.upper()
        text = (answer or "").strip()
        # 答案中出现 "A" / "A." / "A)" / "A、" / "（A）" 等形式
        if re.search(rf"(?<![A-Za-z]){letter}(?![A-Za-z0-9])", text, re.IGNORECASE):
            return 1.0
        # 模型直接输出选项文本
        for opt in options:
            if letter in opt[:4] and opt[3:].strip() and _normalize(opt[3:]) in _normalize(text):
                return 1.0
        return 0.0
    # 期望值是完整文本
    norm = _normalize(answer)
    if _normalize(exp) in norm or norm == _normalize(exp):
        return 1.0
    return 0.0


def score_number(answer: str, question: dict) -> float:
    """数值题：提取答案中的数字并比较"""
    expected = json.loads(question.get("expected") or "[]")
    if not expected:
        return 0.0
    try:
        exp_val = float(expected[0])
    except ValueError:
        return 0.0
    # 取答案中最后一个数字
    nums = re.findall(r"-?\d+(?:\.\d+)?", (answer or "").replace(",", ""))
    if not nums:
        return 0.0
    try:
        got_val = float(nums[-1])
    except ValueError:
        return 0.0
    return 1.0 if abs(got_val - exp_val) < 1e-6 else 0.0


def score_text(answer: str, question: dict) -> float:
    """文本题：归一化后包含匹配（排除否定形式）"""
    expected = json.loads(question.get("expected") or "[]")
    norm = _normalize(answer)
    for exp in expected:
        e = _normalize(str(exp))
        if not e:
            continue
        # 出现“不/并非+期望答案”的否定形式 → 该期望不成立
        negated = any((prefix + e) in norm for prefix in ("不", "不是", "并非", "非"))
        if not negated and (e in norm or norm == e):
            return 1.0
    return 0.0


def _extract_code_block(answer: str) -> str | None:
    """从模型回答中提取 Python 代码块"""
    m = re.search(r"```(?:python|py)?\s*\n(.*?)```", answer or "", re.S | re.I)
    if m:
        return m.group(1)
    # 无代码围栏时尝试整段作为代码
    if "def solution" in (answer or ""):
        return answer
    return None


def score_code(answer: str, question: dict) -> tuple[float, str]:
    """编程题：提取代码写入临时文件，执行测试用例"""
    harness = json.loads(question.get("test_harness") or "[]")
    if not harness:
        return 0.0, "缺少测试用例"
    code = _extract_code_block(answer)
    if not code:
        return 0.0, "未能从回答中提取代码"
    passed = 0
    detail_parts: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        (tmp_path / "solution.py").write_text(code, encoding="utf-8")
        for i, (args, expected) in enumerate(harness):
            test_code = (
                "from solution import solution\n"
                f"args = {args!r}\n"
                f"expected = {expected!r}\n"
                "try:\n"
                "    got = solution(*args)\n"
                "    print('PASS' if got == expected else 'FAIL_GOT_' + repr(got))\n"
                "except Exception as exc:\n"
                "    print('ERR_' + type(exc).__name__ + '_' + str(exc))\n"
            )
            test_file = tmp_path / f"test_{i}.py"
            test_file.write_text(test_code, encoding="utf-8")
            try:
                proc = subprocess.run(
                    ["python", str(test_file)],
                    capture_output=True,
                    text=True,
                    timeout=15,
                    cwd=str(tmp_path),
                )
                out = (proc.stdout or "").strip()
                if out.startswith("PASS"):
                    passed += 1
                else:
                    detail_parts.append(f"用例{i+1}: {out[:120] or proc.stderr[:120]}")
            except subprocess.TimeoutExpired:
                detail_parts.append(f"用例{i+1}: 执行超时")
    score = passed / len(harness)
    detail = f"通过 {passed}/{len(harness)} 个用例" + (("；" + "；".join(detail_parts[:2])) if detail_parts else "")
    return score, detail


def score_objective(answer: str, question: dict) -> tuple[float, str]:
    """按题目类型选择评分器"""
    answer_type = question.get("answer_type") or "text"
    if answer_type == "choice":
        return score_choice(answer, question), ""
    if answer_type == "number":
        return score_number(answer, question), ""
    if answer_type == "code":
        return score_code(answer, question)
    return score_text(answer, question), ""
