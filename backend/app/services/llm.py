"""OpenAI 兼容协议的 LLM 客户端"""
import asyncio
import time
from typing import Any

from openai import AsyncOpenAI

from ..config import MAX_CONCURRENT_REQUESTS, REQUEST_TIMEOUT_SECONDS

# 全局并发信号量，避免同时请求过多
_semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)


def build_client(model: dict) -> AsyncOpenAI:
    kwargs: dict[str, Any] = {"api_key": (model.get("api_key") or "").strip() or "EMPTY"}
    base_url = (model.get("base_url") or "").strip()
    if base_url:
        kwargs["base_url"] = base_url
    return AsyncOpenAI(timeout=REQUEST_TIMEOUT_SECONDS, max_retries=1, **kwargs)


async def chat_once(model: dict, messages: list[dict]) -> tuple[str, float, str | None]:
    """发送一次对话请求，返回 (回答文本, 耗时ms, 错误信息或None)"""
    client = build_client(model)
    start = time.perf_counter()
    async with _semaphore:
        try:
            resp = await _create_completion(client, model, messages)
        except Exception as exc:  # noqa: BLE001
            return "", (time.perf_counter() - start) * 1000, f"{type(exc).__name__}: {exc}"
        finally:
            await client.close()
    latency = (time.perf_counter() - start) * 1000
    try:
        content = resp.choices[0].message.content or ""
    except (IndexError, AttributeError):
        return "", latency, "模型返回格式异常（无 content）"
    return content, latency, None


async def _create_completion(client: AsyncOpenAI, model: dict, messages: list[dict]):
    """发起请求；默认关闭思考模式（逐个降级以兼容不同供应商的参数集）"""
    attempts: list[dict | None] = [None]
    if model.get("disable_thinking", 1):
        attempts = [
            {"thinking": {"type": "disabled"}, "enable_thinking": False},
            {"thinking": {"type": "disabled"}},
            {"enable_thinking": False},
            None,
        ]
    last_error: Exception | None = None
    for extra in attempts:
        kwargs: dict[str, Any] = {"model": model["name"], "messages": messages}
        if extra is not None:
            kwargs["extra_body"] = extra
        try:
            return await client.chat.completions.create(**kwargs)
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            # 参数不被支持（非鉴权/限流类错误）才尝试降级
            text = str(exc)
            if extra is None or not any(
                k in text.lower()
                for k in ("unexpected", "unknown", "invalid", "not support", "unrecognized", "parameter", "字段", "参数")
            ):
                raise
    assert last_error is not None
    raise last_error


def build_messages(question: dict) -> list[dict]:
    """根据题目类型构造消息（支持图像输入）"""
    image_url = question.get("image_url") or ""
    if image_url:
        return [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": question["prompt"]},
                    {"type": "image_url", "image_url": {"url": image_url}},
                ],
            }
        ]
    return [{"role": "user", "content": question["prompt"]}]
