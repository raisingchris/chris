"""Private, metered Responses relay for Chris's local Codex worker.

Only the service holds the OpenAI key. The worker receives a separate token
which can call the bounded model/image endpoints, not account, billing or storage APIs.
"""
from __future__ import annotations

import asyncio
import hmac
import json
import os
import secrets
from pathlib import Path

import httpx
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse

from agent.budget import Meter
from agent.paths import safe_path

MODEL = "gpt-6-astra"
IMAGE_MODEL = "gpt-image-2.5-flare"
MAX_BODY = 2_000_000
MAX_OUTPUT = 8192
DAILY_USD = 5.0


def text_bound(value) -> int:
    """Conservative input-token reservation; base64 images use an image allowance."""
    if isinstance(value, str):
        return 40_000 if value.startswith("data:image/") else len(value.encode())
    if isinstance(value, dict):
        return sum(len(k.encode()) + text_bound(v) for k, v in value.items())
    if isinstance(value, list):
        return sum(text_bound(v) for v in value)
    return 8


def worker_request(body: dict) -> tuple[dict, float]:
    if not isinstance(body, dict) or body.get("model") != MODEL:
        raise HTTPException(400, "The creative worker uses gpt-6-astra.")
    if body.get("previous_response_id") or body.get("conversation") or body.get("background"):
        raise HTTPException(400, "Use a foreground, stateless worker request.")

    def check_tools(items):
        for tool in items:
            if not isinstance(tool, dict) or tool.get("type") not in {"function", "custom", "namespace"}:
                raise HTTPException(400, "Only local worker tools are enabled.")
            if tool.get("type") == "namespace":
                check_tools(tool.get("tools", []))

    check_tools(body.get("tools", []))
    body = dict(body)
    requested = body.get("max_output_tokens", MAX_OUTPUT)
    if type(requested) is not int or requested < 1:
        raise HTTPException(400, "Invalid output limit.")
    body.update(store=False, service_tier="default", max_output_tokens=min(requested, MAX_OUTPUT))
    bound = text_bound(body)
    if bound > 240_000:
        raise HTTPException(413, "Worker context too large; start a smaller task.")
    # Standard Astra: $10/M input, $50/M output. Treat input bytes as tokens
    # and ignore caching for reservations; settle against actual usage later.
    return body, round(bound * 10 / 1_000_000 + body["max_output_tokens"] * 50 / 1_000_000, 6)


def usage_usd(usage: dict) -> float:
    cached = min(int((usage.get("input_tokens_details") or {}).get("cached_tokens", 0)),
                 int(usage.get("input_tokens", 0)))
    return round(((int(usage.get("input_tokens", 0)) - cached) * 10 + cached
                  + int(usage.get("output_tokens", 0)) * 50) / 1_000_000, 6)


def image_request(body: dict) -> tuple[dict, float]:
    prompt = body.get("prompt") if isinstance(body, dict) else None
    if not isinstance(prompt, str) or not prompt.strip() or len(prompt.encode()) > 8000:
        raise HTTPException(400, "Provide an image prompt of at most 8,000 bytes.")
    size = body.get("size", "1024x1024")
    if size not in {"1024x1024", "1536x1024", "1024x1536"}:
        raise HTTPException(400, "Choose a supported image size.")
    if body.get("model", IMAGE_MODEL) != IMAGE_MODEL or body.get("n", 1) != 1:
        raise HTTPException(400, "Generate one Flare image at a time.")
    return {"model": IMAGE_MODEL, "prompt": prompt, "size": size, "quality": "medium",
            "n": 1, "output_format": "png"}, 1.0


def image_usage_usd(usage: dict) -> float:
    detail = usage.get("input_tokens_details") or {}
    text = int(detail.get("text_tokens", 0))
    image = int(detail.get("image_tokens", max(0, int(usage.get("input_tokens", 0)) - text)))
    return round((text * 5 + image * 8 + int(usage.get("output_tokens", 0)) * 30) / 1_000_000, 6)


class CreativeRelay:
    def __init__(self, services, api_key: str, token: str, client_factory=httpx.AsyncClient):
        self.services = services
        self.api_key = api_key
        self.token = token
        self.lock = asyncio.Lock()
        self.meter = Meter("creative", "day", services.cfg.state_dir, services.cfg.tz)
        self.cap = float(os.environ.get("CREATIVE_DAILY_USD", DAILY_USD))
        self.client_factory = client_factory

    def authenticate(self, request: Request):
        if not hmac.compare_digest(request.headers.get("authorization", ""), "Bearer " + self.token):
            raise HTTPException(401, "Creative worker authentication required.")

    async def responses(self, request: Request):
        return await self._forward(request, image=False)

    async def images(self, request: Request):
        return await self._forward(request, image=True)

    async def _forward(self, request: Request, *, image: bool):
        self.authenticate(request)
        raw = bytearray()
        async for chunk in request.stream():
            raw.extend(chunk)
            if len(raw) > MAX_BODY:
                raise HTTPException(413, "Worker request too large.")
        try:
            body, reserve = (image_request if image else worker_request)(json.loads(raw))
        except (ValueError, TypeError):
            raise HTTPException(400, "Invalid worker request.") from None
        if self.lock.locked():
            raise HTTPException(429, "One creative request at a time; retry after the current request.")
        await self.lock.acquire()
        if self.meter.remaining(self.cap) < reserve or self.services.inference.remaining(self.services.cfg.hard_usd) < reserve:
            self.lock.release()
            raise HTTPException(429, "Creative budget exhausted for today; ask a parent if more is needed.")
        period = self.meter.period_key()
        self.meter.add_usd(reserve, "Astra request reservation")
        self.services.inference.add_usd(reserve, "Astra request reservation")
        settled = False

        def settle(actual=None):
            nonlocal settled
            if settled:
                return
            settled = True
            charge = reserve if actual is None else actual
            if self.meter.period_key() == period:
                self.meter.add_usd(charge - reserve, "Astra usage settlement")
                self.services.inference.add_usd(charge - reserve, "Astra usage settlement")
            self.services.archive.append("creative_usage", {
                "model": body["model"], "usd": charge, "estimated": actual is None})

        client = self.client_factory(timeout=httpx.Timeout(300, connect=20), follow_redirects=False)
        try:
            endpoint = "images/generations" if image else "responses"
            req = client.build_request("POST", "https://api.openai.com/v1/" + endpoint, json=body,
                                       headers={"Authorization": "Bearer " + self.api_key})
            response = await client.send(req, stream=True)
            if response.status_code != 200:
                await response.aclose()
                settle(0)
                # Never return upstream errors/headers containing project/account information.
                raise HTTPException(502, "Astra request rejected upstream; ask a parent to inspect the model connection.")
        except BaseException:
            settle()
            await client.aclose()
            self.lock.release()
            raise

        async def events():
            usage = None
            try:
                async for line in response.aiter_lines():
                    if line.startswith("data:"):
                        try:
                            item = json.loads(line[5:])
                        except ValueError:
                            item = {}
                        result = item.get("response") or {}
                        if result.get("usage"):
                            usage = result["usage"]
                        if item.get("type") in {"error", "response.failed"}:
                            line = 'data: {"type":"error","message":"Creative generation failed; retry or ask a parent."}'
                    yield (line + "\n").encode()
            finally:
                settle(usage_usd(usage) if usage is not None else None)
                await response.aclose()
                await client.aclose()
                self.lock.release()

        if body.get("stream"):
            return StreamingResponse(events(), media_type="text/event-stream")
        try:
            await response.aread()
            data = response.json()
            settle((image_usage_usd if image else usage_usd)(data["usage"]) if data.get("usage") else None)
            return JSONResponse(data)
        finally:
            settle()
            await response.aclose()
            await client.aclose()
            self.lock.release()


def register_creative(app, services):
    key = os.environ.get("OPENAI_API_KEY", "")
    if not key or services.cfg.dry_run:
        return
    # safe_path rejects symlinks planted in the shared repo before brain writes.
    access = safe_path(services.cfg.repo_dir, "memory/inbox/.creative/access.json")
    access.parent.mkdir(parents=True, exist_ok=True)
    access.parent.chmod(0o2770)
    token_path = Path(services.cfg.state_dir) / "creative_token"
    if token_path.exists():
        token = token_path.read_text().strip()
    else:
        token = secrets.token_urlsafe(32)
        fd = os.open(token_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as f:
            f.write(token)
    fd = os.open(access, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o640)
    with os.fdopen(fd, "w") as f:
        json.dump({"base_url": "http://127.0.0.1:8080/creative/v1", "token": token, "model": MODEL}, f)
    access.chmod(0o640)
    relay = CreativeRelay(services, key, token)
    app.add_api_route("/creative/v1/responses", relay.responses, methods=["POST"])
    app.add_api_route("/creative/v1/images/generations", relay.images, methods=["POST"])
    app.state.creative_relay = relay
