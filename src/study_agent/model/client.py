"""Local multimodal model client and fallback logic."""

from __future__ import annotations

import base64
import json
import re
from io import BytesIO
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests
from PIL import Image

from study_agent.config import Settings
from study_agent.types import Observation, StudyAssessment


class LocalMultimodalClient:
    """Send observations to a local multimodal model and parse its output."""

    def __init__(self, settings: Settings) -> None:
        """Store model-related runtime settings."""
        # Runtime settings used for model requests.
        self.settings = settings

    def assess(self, observation: Observation, recent_summary: dict[str, Any]) -> StudyAssessment:
        """Generate a study-state assessment from the observation and recent summary."""
        if not self.settings.model_enabled:
            return self._heuristic_assessment(observation)

        payload_variants = [
            self._build_payload(
                observation, recent_summary, include_images=True, enforce_json_response=True
            ),
            self._build_payload(
                observation, recent_summary, include_images=True, enforce_json_response=False
            ),
            self._build_payload(
                observation, recent_summary, include_images=False, enforce_json_response=False
            ),
        ]
        for payload in payload_variants:
            try:
                response = self._post_completion(payload)
                response.raise_for_status()
                parsed = self._parse_response(response.json())
                if parsed is not None:
                    return parsed
            except requests.RequestException:
                continue
        return self._heuristic_assessment(observation)

    def _build_headers(self) -> dict[str, str]:
        """Build HTTP headers for the model request."""
        headers = {"Content-Type": "application/json"}
        if self.settings.model_api_key:
            headers["Authorization"] = f"Bearer {self.settings.model_api_key}"
        return headers

    def _post_completion(self, payload: dict[str, Any]) -> requests.Response:
        """Post one completion request, bypassing env proxies for local model servers."""
        url = f"{self.settings.model_base_url.rstrip('/')}/chat/completions"
        hostname = (urlparse(url).hostname or "").lower()
        if hostname in {"127.0.0.1", "localhost"}:
            with requests.Session() as session:
                session.trust_env = False
                return session.post(url, headers=self._build_headers(), json=payload, timeout=180)
        return requests.post(url, headers=self._build_headers(), json=payload, timeout=180)

    def _build_payload(
        self,
        observation: Observation,
        recent_summary: dict[str, Any],
        *,
        include_images: bool,
        enforce_json_response: bool,
    ) -> dict[str, Any]:
        """Build an OpenAI-compatible multimodal request payload."""
        # User message content containing text and optional images.
        user_content: list[dict[str, Any]] = [
            {"type": "text", "text": self._build_prompt(observation, recent_summary)}
        ]
        if include_images and observation.screen_path:
            user_content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": self._to_data_url(observation.screen_path)},
                }
            )
        if include_images and observation.camera_path:
            user_content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": self._to_data_url(observation.camera_path)},
                }
            )
        payload = {
            "model": self.settings.model_name,
            "messages": [
                {
                    "role": "system",
                    "content": "你是学习状态分析代理。你必须仅输出 JSON。",
                },
                {
                    "role": "user",
                    "content": user_content,
                },
            ],
            "temperature": 0.1,
        }
        if enforce_json_response:
            payload["response_format"] = {"type": "json_object"}
        return payload

    def _build_prompt(self, observation: Observation, recent_summary: dict[str, Any]) -> str:
        """Build the structured prompt used for study-state inference."""
        # System context attached to the current observation.
        context = observation.context
        return "".join(
            [
                "请根据屏幕截图、摄像头截图和上下文判断用户当前学习状态。\n",
                "输出 JSON 字段: ",
                (
                    "state, confidence, learning_related, is_present, "
                    "is_looking_at_screen, focus_score, reason, distraction_signals。\n"
                ),
                (
                    f"当前上下文: active_app={context.active_app}, "
                    f"window_title={context.window_title}, "
                    f"idle_seconds={context.idle_seconds}, "
                    f"app_switch_count_5m={context.app_switch_count_5m}\n"
                ),
                f"最近摘要: {json.dumps(recent_summary, ensure_ascii=False)}\n",
                "state 只允许: studying, distracted, away, uncertain。",
            ]
        )

    def _parse_response(self, response_json: dict[str, Any]) -> StudyAssessment | None:
        """Parse the JSON response returned by the model."""
        try:
            # Standard Chat Completions text content location.
            content = response_json["choices"][0]["message"]["content"]
            # Parsed structured JSON produced by the model.
            parsed = self._extract_json_object(content)
            if parsed is None:
                return None
            return StudyAssessment(
                state=str(parsed.get("state", "uncertain")),
                confidence=float(parsed.get("confidence", 0.5)),
                learning_related=bool(parsed.get("learning_related", False)),
                is_present=bool(parsed.get("is_present", True)),
                is_looking_at_screen=parsed.get("is_looking_at_screen"),
                focus_score=float(parsed.get("focus_score", 0.5)),
                reason=str(parsed.get("reason", "model assessment")),
                distraction_signals=list(parsed.get("distraction_signals", [])),
                raw_response=response_json,
            )
        except (KeyError, ValueError, TypeError, json.JSONDecodeError):
            return None

    def _extract_json_object(self, content: Any) -> dict[str, Any] | None:
        """Extract the first valid JSON object from a model response."""
        if isinstance(content, list):
            text = "\n".join(
                str(item.get("text", "")) for item in content if isinstance(item, dict)
            )
        else:
            text = str(content)

        candidates = [text.strip()]
        candidates.append(re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip())

        fenced_matches = re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
        candidates.extend(match.strip() for match in fenced_matches)

        decoder = json.JSONDecoder()
        for candidate in candidates:
            if not candidate:
                continue
            try:
                parsed = json.loads(candidate)
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                pass

            for start_index, char in enumerate(candidate):
                if char != "{":
                    continue
                try:
                    parsed, _ = decoder.raw_decode(candidate[start_index:])
                    if isinstance(parsed, dict):
                        return parsed
                except json.JSONDecodeError:
                    continue
        return None

    def _heuristic_assessment(self, observation: Observation) -> StudyAssessment:
        """Run heuristic fallback logic when the model is unavailable."""
        # Lowercased window title used for keyword matching.
        title = (observation.context.window_title or "").lower()
        # Keywords that suggest learning-related activity.
        learning_keywords = [
            "notion",
            "obsidian",
            "vscode",
            "jupyter",
            "coursera",
            "leetcode",
            "论文",
            "课程",
            "study",
            "doc",
            "pdf",
            "github",
        ]
        # Keywords that suggest distracting activity.
        distracted_keywords = [
            "bilibili",
            "youtube",
            "douyin",
            "wechat",
            "discord",
            "game",
            "steam",
        ]
        # Whether a camera image was captured successfully.
        has_camera = observation.camera_path is not None

        if any(keyword in title for keyword in learning_keywords):
            return StudyAssessment(
                state="studying",
                confidence=0.68,
                learning_related=True,
                is_present=has_camera,
                is_looking_at_screen=True if has_camera else None,
                focus_score=0.72,
                reason="heuristic matched learning-related active window",
                distraction_signals=[],
                raw_response={"mode": "heuristic"},
            )
        if any(keyword in title for keyword in distracted_keywords):
            return StudyAssessment(
                state="distracted",
                confidence=0.7,
                learning_related=False,
                is_present=has_camera,
                is_looking_at_screen=True if has_camera else None,
                focus_score=0.25,
                reason="heuristic matched distraction-related active window",
                distraction_signals=["window_content_non_learning"],
                raw_response={"mode": "heuristic"},
            )
        if not has_camera:
            return StudyAssessment(
                state="away",
                confidence=0.6,
                learning_related=False,
                is_present=False,
                is_looking_at_screen=False,
                focus_score=0.1,
                reason="camera capture unavailable",
                distraction_signals=["camera_unavailable"],
                raw_response={"mode": "heuristic"},
            )
        return StudyAssessment(
            state="uncertain",
            confidence=0.4,
            learning_related=False,
            is_present=True,
            is_looking_at_screen=None,
            focus_score=0.45,
            reason="insufficient heuristic signals",
            distraction_signals=[],
            raw_response={"mode": "heuristic"},
        )

    def _to_data_url(self, path: Path) -> str:
        """Encode an image file as a compressed data URL for local vision models."""
        mime_type = "image/jpeg"
        with Image.open(path) as image:
            optimized = image.convert("RGB")
            optimized.thumbnail((768, 768))
            buffer = BytesIO()
            optimized.save(buffer, format="JPEG", quality=60, optimize=True)
        encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
        return f"data:{mime_type};base64,{encoded}"
