"""
CV Gemini Helper
Provides: process_file_to_pdf_nextjob, convert_pdf_to_base64_image,
          GeminiSession, CIRCULAR_EXTRACTION_PROMPT
"""

from __future__ import annotations

import base64
import json
import os
import platform
import re
import subprocess
from io import BytesIO
from itertools import cycle

from google import genai
from google.genai import types
from pdf2image import convert_from_path
from PIL import Image

system = platform.system()

# ── LibreOffice ───────────────────────────────────────────────────────────────

def find_libreoffice() -> str | None:
    if system == "Windows":
        paths = [
            r"C:\Program Files\LibreOffice\program\soffice.exe",
            r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
        ]
    elif system == "Linux":
        paths = ["/usr/bin/libreoffice", "/usr/bin/soffice"]
    elif system == "Darwin":
        paths = ["/Applications/LibreOffice.app/Contents/MacOS/soffice"]
    else:
        paths = []
    for p in paths:
        if os.path.exists(p):
            return p
    return None


def convert_doc_to_pdf(input_file: str) -> str:
    if not os.path.exists(input_file):
        raise FileNotFoundError(input_file)
    soffice = find_libreoffice()
    if not soffice:
        raise RuntimeError("LibreOffice not installed")
    uploads_dir = os.path.join(os.getcwd(), "uploads")
    os.makedirs(uploads_dir, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(input_file))[0]
    cmd = [soffice, "--headless", "--convert-to", "pdf", input_file, "--outdir", uploads_dir]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())
    generated_pdf = os.path.join(uploads_dir, base_name + ".pdf")
    if not os.path.exists(generated_pdf):
        raise RuntimeError("PDF conversion failed")
    return generated_pdf


# ── File → PDF ────────────────────────────────────────────────────────────────

def process_file_to_pdf_nextjob(file_path: str) -> str | None:
    """Return a valid PDF path, or None if conversion not possible."""
    filename = os.path.basename(file_path)
    file_ext = filename.rsplit(".", 1)[-1].lower()
    upload_folder = os.path.join(os.getcwd(), "uploads")
    os.makedirs(upload_folder, exist_ok=True)

    if file_ext == "pdf":
        return file_path

    if file_ext in ("doc", "docx"):
        temp_path = os.path.join(upload_folder, filename)
        with open(file_path, "rb") as f_in, open(temp_path, "wb") as f_out:
            f_out.write(f_in.read())
        converted = convert_doc_to_pdf(temp_path)
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return converted

    return None  # unsupported type


# ── PDF → base64 image (Poppler) ─────────────────────────────────────────────

def convert_pdf_to_base64_image(pdf_path: str) -> str | None:
    """Stitch all PDF pages vertically and return a base64 PNG string."""
    try:
        if system == "Windows":
            poppler_path = r"D:\iBOS\arl_automation\poppler-23.11.0\Library\bin"
            images = convert_from_path(pdf_path, poppler_path=poppler_path)
        else:
            images = convert_from_path(pdf_path)

        if not images:
            raise ValueError("No images converted from PDF")

        total_height = sum(img.height for img in images)
        max_width = max(img.width for img in images)
        stitched = Image.new("RGB", (max_width, total_height), (255, 255, 255))
        y = 0
        for img in images:
            stitched.paste(img, (0, y))
            y += img.height

        buf = BytesIO()
        stitched.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode("utf-8")
    except Exception:
        return None


# ── GeminiSession ─────────────────────────────────────────────────────────────

class GeminiSession:
    """Gemini API client with automatic key rotation via google.genai."""

    def __init__(self) -> None:
        self.keys = self._load_keys()
        if not self.keys:
            raise RuntimeError("No Google API keys available in gemini_keys.json")
        self._key_cycle = cycle(self.keys)
        self.current_key: str | None = None

    def _load_keys(self) -> list[str]:
        try:
            with open("credentials/gemini_keys.json", encoding="utf-8") as f:
                return list(json.load(f).values())
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def _get_client(self) -> genai.Client:
        self.current_key = next(self._key_cycle)
        return genai.Client(api_key=self.current_key)

    def call_api(self, prompt: str, base64_image: str) -> dict:
        """
        Send prompt + Poppler-rendered base64 PNG to Gemini.
        Rotates keys on failure.
        """
        last_error: Exception | None = None
        for _ in range(len(self.keys)):
            try:
                client = self._get_client()
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=[
                        types.Part.from_bytes(
                            data=base64.b64decode(base64_image),
                            mime_type="image/png",
                        ),
                        prompt,
                    ],
                )
                return self._parse_json(response.text.strip())
            except Exception as exc:
                last_error = exc
        raise RuntimeError(f"All Gemini API keys failed. Last error: {last_error}")

    def _parse_json(self, output: str) -> dict:
        start = output.find("{")
        end = output.rfind("}")
        if start == -1 or end == -1:
            raise ValueError("No valid JSON object found in Gemini response")
        json_text = output[start : end + 1]

        def escape_html(m: re.Match) -> str:
            return re.sub(r'="([^"]*)"', r'=\"\1\"', m.group(0))

        json_text = re.sub(r"<[^>]+>", escape_html, json_text)
        json_text = re.sub(r'(?<!")\b0+(\d+)\b(?!")', lambda m: str(int(m.group(0))), json_text)
        return json.loads(json_text)


# ── DDL data + system prompt ──────────────────────────────────────────────────
# Single source of truth: app/prompts/nextjobz_prompt.py

from app.prompts.nextjobz_prompt import (  # noqa: E402
    CIRCULAR_EXTRACTION_PROMPT,
    AccomplishmentTypeDDL,
    EDUCATION_LEVEL_DDL,
    employmentTypeDDL,
    GENDER_DDL,
    INDUSTRY_TYPE_DDL,
    district_Upazila_DDL,
    portfolioTypeDDL,
    RESULT_TYPE_DDL,
    TRAINING_MODE_DDL,
)

__all__ = [
    "CIRCULAR_EXTRACTION_PROMPT",
    "GeminiSession",
    "convert_pdf_to_base64_image",
    "process_file_to_pdf_nextjob",
    "district_Upazila_DDL",
    "GENDER_DDL",
    "EDUCATION_LEVEL_DDL",
    "INDUSTRY_TYPE_DDL",
    "RESULT_TYPE_DDL",
    "TRAINING_MODE_DDL",
    "employmentTypeDDL",
    "portfolioTypeDDL",
    "AccomplishmentTypeDDL",
]
