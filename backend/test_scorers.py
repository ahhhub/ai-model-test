"""离线评分引擎自检（不需要任何 API Key）"""
import json
import sys
sys.path.insert(0, ".")

from app import database as db
from app.services import scorers

db.init_db()


def json_expected_first(q):
    return json.loads(q["expected"])[0]


cases = []

# 选择题
q = db.query_one("SELECT * FROM questions WHERE answer_type='choice' LIMIT 1")
cases.append(("choice 正确", scorers.score_choice("答案是 B。", q) == 1.0))
cases.append(("choice 全角括号", scorers.score_choice("（B）巴黎", q) == 1.0))
cases.append(("choice 错误", scorers.score_choice("选 C", q) == 0.0 if q and json_expected_first(q) != "C" else True))

# 数值题（苹果问题，期望 6）
q = db.query_one("SELECT * FROM questions WHERE answer_type='number' AND title='苹果问题'")
cases.append(("number 提取", scorers.score_number("计算结果为 6 个。", q) == 1.0))
cases.append(("number 错误", scorers.score_number("答案是 7", q) == 0.0))

# 文本题（三段论，期望 正确/是/对）
q = db.query_one("SELECT * FROM questions WHERE answer_type='text' AND judge=0 AND title='三段论'")
cases.append(("text 包含", scorers.score_text("我认为这个说法是正确的。", q) == 1.0))
cases.append(("text 否定判错", scorers.score_text("不正确", q) == 0.0))
cases.append(("text 无关", scorers.score_text("香蕉", q) == 0.0))

# 代码题（实际执行）
q = db.query_one("SELECT * FROM questions WHERE answer_type='code' LIMIT 1")
good_code = {
    "FizzBuzz": '```python\ndef solution(n):\n    out=[]\n    for i in range(1,n+1):\n        if i%15==0: out.append("FizzBuzz")\n        elif i%3==0: out.append("Fizz")\n        elif i%5==0: out.append("Buzz")\n        else: out.append(str(i))\n    return out\n```',
    "回文判断": '```python\ndef solution(s):\n    return s == s[::-1]\n```',
    "两数之和": '```python\ndef solution(nums, target):\n    for i in range(len(nums)):\n        for j in range(i+1, len(nums)):\n            if nums[i]+nums[j]==target:\n                return [i,j]\n```',
    "反转单词顺序": '```python\ndef solution(s):\n    return " ".join(s.split()[::-1])\n```',
    "阶乘": '```python\ndef solution(n):\n    return 1 if n==0 else n*solution(n-1)\n```',
    "斐波那契": '```python\ndef solution(n):\n    a,b=0,1\n    for _ in range(n):\n        a,b=b,a+b\n    return a\n```',
}
title = q["title"]
if title in good_code:
    score, detail = scorers.score_code(good_code[title], q)
    cases.append((f"code {title} 满分", score == 1.0, detail))
score, detail = scorers.score_code("```python\ndef solution(n):\n    return 0\n```", q)
cases.append((f"code {title} 错误答案", score < 1.0, detail))

failed = 0
for item in cases:
    name, ok = item[0], item[1]
    extra = item[2] if len(item) > 2 else ""
    print(("PASS" if ok else "FAIL"), name, ("| " + str(extra)[:100] if extra else ""))
    if not ok:
        failed += 1

print("\n结果:", "全部通过" if failed == 0 else f"{failed} 项失败")
sys.exit(1 if failed else 0)
