"""前端代码实测评分器：用 Playwright 无头浏览器加载模型生成的 HTML 并执行交互检查"""
import asyncio
import json
import re

from . import judge


def extract_html(answer: str) -> str | None:
    """从模型回答中提取完整 HTML"""
    if not answer:
        return None
    m = re.search(r"```(?:html|htm)\s*\n(.*?)```", answer, re.S | re.I)
    if m:
        return m.group(1)
    m = re.search(r"```\s*\n(.*?)```", answer, re.S)
    if m and ("<html" in m.group(1) or "<!DOCTYPE" in m.group(1).upper() or "<body" in m.group(1)):
        return m.group(1)
    if re.search(r"<!DOCTYPE\s+html|<html[\s>]", answer, re.I):
        return answer
    return None


def run_browser_checks(html: str, checks: list[dict]) -> list[tuple[str, bool]]:
    """在无头 Chromium 中逐项执行检查，返回 [(描述, 是否通过)]"""
    results: list[tuple[str, bool]] = []
    console_errors: list[str] = []
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return [(c.get("description", "检查"), False) for c in checks] + [
            ("Playwright 未安装", False)
        ]

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1280, "height": 800})
            page.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)
            page.on("pageerror", lambda e: console_errors.append(str(e)))
            page.set_content(html, timeout=20000)
            page.wait_for_timeout(1200)

            for check in checks:
                kind = check.get("kind", "selector")
                desc = check.get("description", kind)
                timeout = check.get("timeout", 5000)
                try:
                    if kind == "selector":
                        ok = page.locator(check["selector"]).count() > 0
                        results.append((desc, ok))
                    elif kind == "click":
                        loc = page.locator(check["selector"])
                        if loc.count() == 0:
                            results.append((desc, False))
                            continue
                        loc.first.click(timeout=timeout)
                        wait_sel = check.get("wait_selector")
                        if wait_sel:
                            page.wait_for_selector(wait_sel, timeout=timeout)
                        results.append((desc, True))
                    elif kind == "pointer_move":
                        center = page.viewport_size
                        region = page.locator("body").bounding_box() or {"x": 0, "y": 0, "width": 1280, "height": 800}
                        x, y = center["width"] // 2, center["height"] // 2
                        before = page.screenshot()
                        page.mouse.move(x, y)
                        page.mouse.move(x + 40, y - 30)
                        page.wait_for_timeout(600)
                        after = page.screenshot()
                        results.append((desc, before != after))
                    elif kind == "no_console_errors":
                        results.append((desc, len(console_errors) == 0))
                    else:
                        results.append((desc, False))
                except Exception:  # noqa: BLE001
                    results.append((desc, False))
            browser.close()
    except Exception as exc:  # noqa: BLE001
        return [(c.get("description", "检查"), False) for c in checks] + [
            (f"浏览器执行失败: {type(exc).__name__}", False)
        ]
    return results


async def score_html(answer: str, question: dict, judge_model: dict | None) -> tuple[float, str]:
    """前端题评分：浏览器实测占 60%，裁判模型点评视觉表现占 40%（无裁判则按实测比例折算）"""
    html = extract_html(answer)
    if not html:
        return 0.0, "未能从回答中提取到 HTML 代码"

    harness = json.loads(question.get("test_harness") or "{}")
    checks = harness.get("checks") or []
    check_results = await asyncio.to_thread(run_browser_checks, html, checks)

    passed = sum(1 for _, ok in check_results if ok)
    total = len(check_results)
    detail_parts = [f"{d}：{'通过' if ok else '未通过'}" for d, ok in check_results]
    base = (passed / total) if total else 0.0

    if judge_model:
        judge_q = dict(question)
        judge_q["rubric"] = question.get("rubric") or "从视觉与设计角度综合点评。"
        judge_q["max_score"] = 4
        aesthetic, reason = await judge.judge_answer(judge_model, judge_q, html)
        score = round(base * 6 + aesthetic, 2)
        detail = f"浏览器实测 {passed}/{total}（{'; '.join(detail_parts)}）；视觉点评 {aesthetic}/4：{reason}"
    else:
        score = round(base * 10, 2)
        detail = f"浏览器实测 {passed}/{total}（{'; '.join(detail_parts)}）"
    return score, detail
