from __future__ import annotations
import base64
import json
from typing import Any

import anthropic


class ClaudeClient:
    def __init__(self, api_key: str):
        self.client = anthropic.Anthropic(api_key=api_key)

    def analyze_frames(self, frame_paths: list[str], prompt: str) -> str:
        """Send up to 12 frames + prompt to claude-sonnet-4-6 vision. Returns text response."""
        content: list[Any] = []
        for path in frame_paths[:12]:
            with open(path, "rb") as f:
                data = base64.standard_b64encode(f.read()).decode()
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": data,
                },
            })
        content.append({"type": "text", "text": prompt})

        response = self.client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            system=[{
                "type": "text",
                "text": (
                    "You are an expert at analyzing software UI and screen recordings. "
                    "Always respond with valid JSON when asked."
                ),
                "cache_control": {"type": "ephemeral"},
            }],
            messages=[{"role": "user", "content": content}],
        )
        return response.content[0].text

    def generate_script(
        self,
        context_json: str,
        target_duration_s: int,
        output_style: str,
    ) -> str:
        """Generate narration script from narrative context. Returns JSON string."""
        response = self.client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            thinking={"type": "enabled", "budget_tokens": 8000},
            messages=[{
                "role": "user",
                "content": f"""You are a professional product demo scriptwriter.

Given this app analysis and scene list, write a {target_duration_s}-second {output_style} video narration script.

Context:
{context_json}

Return a JSON object with this exact schema:
{{
  "app_name": "string",
  "app_description": "string",
  "user_journey_summary": "string",
  "full_narration_text": "string (complete narration read aloud)",
  "estimated_read_duration_s": number,
  "chapters": [
    {{
      "index": 0,
      "title": "string",
      "start_scene_index": 0,
      "end_scene_index": 0,
      "narration_text": "string",
      "feature_highlights": ["string"]
    }}
  ],
  "subtitle_segments": [
    {{
      "start_s": 0.0,
      "end_s": 5.0,
      "text": "string"
    }}
  ]
}}

Return only the JSON, no other text.""",
            }],
        )
        # Extract text from response (skip thinking blocks)
        for block in response.content:
            if block.type == "text":
                return block.text
        return "{}"
