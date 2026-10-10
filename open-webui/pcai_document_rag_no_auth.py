"""
title: PCAI Document RAG
author: PCAI Demo
version: 1.1.0
description: Open WebUI Pipelines bridge to an n8n Chat Trigger (no authentication).
"""

import hashlib
from typing import List

import requests
from pydantic import BaseModel, Field


class Pipeline:
    class Valves(BaseModel):
        N8N_CHAT_URL: str = Field(
            default="https://n8n-workspace.hpepcai4.demo.local/webhook/6ed3f6ac-4cda-4007-b742-4b816239e7fd/chat",
            description="n8n Chat Trigger production URL (POST).",
        )
        VERIFY_SSL: bool = Field(
            default=True,
            description="Verify the HTTPS certificate. Keep enabled whenever possible.",
        )
        TIMEOUT_SECONDS: int = Field(
            default=180,
            ge=10,
            le=600,
            description="Maximum time to wait for the n8n RAG response.",
        )

    def __init__(self):
        # The pipeline ID is inferred from this file name.
        self.name = "PCAI Document RAG"
        self.valves = self.Valves()

    @staticmethod
    def _get_text(content) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            return "\n".join(
                item.get("text", "")
                for item in content
                if isinstance(item, dict)
                and item.get("type") == "text"
                and isinstance(item.get("text"), str)
            )
        return ""

    @staticmethod
    def _session_id(body: dict, messages: List[dict]) -> str:
        metadata = body.get("metadata") or {}
        if not isinstance(metadata, dict):
            metadata = {}
        for key in ("chat_id", "session_id"):
            identifier = metadata.get(key) or body.get(key)
            if identifier:
                return str(identifier)
        # Stable fallback when the client does not provide a conversation ID.
        user = body.get("user") or metadata.get("user_id") or "anonymous"
        if isinstance(user, dict):
            user = user.get("id", "anonymous")
        first_question = next(
            (
                Pipeline._get_text(m.get("content"))
                for m in messages
                if isinstance(m, dict) and m.get("role") == "user"
            ),
            "",
        )
        fingerprint = hashlib.sha256(
            (str(user) + ":" + first_question).encode("utf-8")
        ).hexdigest()
        return "openwebui-" + fingerprint[:32]

    @staticmethod
    def _answer(data):
        if isinstance(data, str):
            return data.strip() or None
        if isinstance(data, list):
            for item in data:
                answer = Pipeline._answer(item)
                if answer:
                    return answer
        if isinstance(data, dict):
            for field in ("output", "text", "answer", "response", "result"):
                if field in data:
                    answer = Pipeline._answer(data[field])
                    if answer:
                        return answer
        return None

    def pipe(
        self,
        user_message: str,
        model_id: str,
        messages: List[dict],
        body: dict,
    ) -> str:
        body = body or {}
        messages = messages or []
        if body.get("title"):
            return "PCAI Document RAG"

        url = self.valves.N8N_CHAT_URL.strip()
        if not url.startswith(("http://", "https://")):
            return "Set N8N_CHAT_URL to your n8n Chat Trigger production URL."

        question = self._get_text(user_message)
        if not question.strip():
            question = next(
                (
                    self._get_text(m.get("content"))
                    for m in reversed(messages)
                    if isinstance(m, dict) and m.get("role") == "user"
                ),
                "",
            )
        if not question.strip():
            return "Please enter a question about the uploaded documents."

        payload = {
            "action": "sendMessage",
            "sessionId": self._session_id(body, messages),
            "chatInput": question,
        }
        try:
            response = requests.post(
                url,
                json=payload,
                headers={"Accept": "application/json"},
                timeout=self.valves.TIMEOUT_SECONDS,
                verify=self.valves.VERIFY_SSL,
            )
        except requests.exceptions.SSLError:
            return "n8n HTTPS certificate could not be verified. Configure the cluster CA or VERIFY_SSL in the pipeline settings."
        except requests.exceptions.Timeout:
            return "n8n timed out. Check its workflow executions."
        except requests.exceptions.RequestException as exc:
            return f"Cannot reach n8n: {type(exc).__name__}. Check N8N_CHAT_URL and network access."

        if not response.ok:
            return (
                f"n8n returned HTTP {response.status_code}. "
                "Check that the workflow is active and its Chat Trigger production URL is correct."
            )
        try:
            data = response.json()
        except ValueError:
            data = response.text
        return self._answer(data) or (
            "n8n responded but no answer was found. "
            "Inspect the 'Chat reply' node output in n8n."
        )
