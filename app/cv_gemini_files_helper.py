"""
CV Gemini Files Helper (v3)
Uses google.genai Files API — no Poppler needed.
PDF is uploaded directly to Gemini for processing.
"""

from __future__ import annotations

import base64
import json
import os
import pathlib
import re
import subprocess
import tempfile
import time
from io import BytesIO
from itertools import cycle

from google import genai
from google.genai import types
from PIL import Image


# ── LibreOffice (DOC/DOCX → PDF) ─────────────────────────────────────────────

def _find_libreoffice() -> str | None:
    import platform
    system = platform.system()
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


def convert_doc_to_pdf_v3(input_file: str) -> str:
    if not os.path.exists(input_file):
        raise FileNotFoundError(input_file)
    soffice = _find_libreoffice()
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


def process_file_to_pdf_v3(file_path: str) -> str | None:
    """Return a valid PDF path, or None if unsupported."""
    ext = os.path.basename(file_path).rsplit(".", 1)[-1].lower()
    if ext == "pdf":
        return file_path
    if ext in ("doc", "docx"):
        upload_folder = os.path.join(os.getcwd(), "uploads")
        os.makedirs(upload_folder, exist_ok=True)
        temp_path = os.path.join(upload_folder, os.path.basename(file_path))
        with open(file_path, "rb") as fin, open(temp_path, "wb") as fout:
            fout.write(fin.read())
        converted = convert_doc_to_pdf_v3(temp_path)
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return converted
    return None


# ── ImageProcessor (for image-only files) ────────────────────────────────────

class ImageProcessor:
    def encode_image_to_base64(self, pil_image) -> str:
        buffer = BytesIO()
        pil_image.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode("utf-8")


def convert_image_to_base64(image_path: str) -> str | None:
    """Convert an image file to base64 PNG — no Poppler needed."""
    try:
        img = Image.open(image_path).convert("RGB")
        return ImageProcessor().encode_image_to_base64(img)
    except Exception:
        return None


# ── PDF splitter (pypdf — no Poppler) ────────────────────────────────────────

def split_pdf_to_pages(pdf_path: str) -> list[str]:
    """Split a PDF into single-page temp PDFs. Returns list of paths."""
    try:
        from pypdf import PdfReader, PdfWriter
    except ImportError:
        print("❌ pypdf not installed. Run: pip install pypdf")
        return []
    try:
        reader = PdfReader(pdf_path)
        print(f"  📄 PDF has {len(reader.pages)} page(s). Splitting...")
        temp_dir = tempfile.mkdtemp(prefix="gemini_pdf_")
        paths: list[str] = []
        for i, page in enumerate(reader.pages):
            writer = PdfWriter()
            writer.add_page(page)
            p = os.path.join(temp_dir, f"page_{i + 1:04d}.pdf")
            with open(p, "wb") as f:
                writer.write(f)
            paths.append(p)
        return paths
    except Exception as e:
        print(f"❌ Error splitting PDF: {e}")
        return []


def cleanup_temp_files(paths: list[str]) -> None:
    for p in paths:
        try:
            os.remove(p)
        except Exception:
            pass
    if paths:
        try:
            os.rmdir(os.path.dirname(paths[0]))
        except Exception:
            pass


# ── GeminiSession (Files API) ─────────────────────────────────────────────────

class GeminiSessionV3:
    """
    Gemini API client using the Files API — no Poppler needed.
    PDF is uploaded directly; Gemini reads it natively.
    Key rotation via itertools.cycle.
    """

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

    # ------------------------------------------------------------------
    # PRIMARY — upload PDF directly (no Poppler)
    # ------------------------------------------------------------------

    def call_api_with_file(self, prompt: str, file_path: str) -> dict:
        """Upload a PDF via Files API and call Gemini. Rotates keys on failure."""
        last_error: Exception | None = None
        for _ in range(len(self.keys)):
            try:
                client = self._get_client()
                print(f"  🔄 Trying key: {self.current_key[:8]}...")

                uploaded = client.files.upload(file=pathlib.Path(file_path))

                # Wait for processing with optimized polling (0.5s intervals, 60s timeout)
                max_wait_time = 30
                start_time = time.time()
                while uploaded.state and uploaded.state.name == "PROCESSING":
                    if time.time() - start_time > max_wait_time:
                        raise RuntimeError(f"File processing timeout after {max_wait_time}s")
                    time.sleep(0.5)
                    uploaded = client.files.get(name=uploaded.name)

                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=[uploaded, prompt],
                )
                output = response.text.strip()
                print("  🔎 Raw output:", output[:200], "...")

                # Cleanup uploaded file
                try:
                    client.files.delete(name=uploaded.name)
                except Exception:
                    pass

                return self._parse_json(output)

            except Exception as exc:
                print(f"  ❌ Key failed: {self.current_key[:8]}... — {exc}")
                last_error = exc

        raise RuntimeError(f"All Gemini keys failed. Last error: {last_error}")

    # ------------------------------------------------------------------
    # SECONDARY — base64 image (for image files)
    # ------------------------------------------------------------------

    def call_api(self, prompt: str, base64_image: str) -> dict:
        """Send prompt + inline base64 image to Gemini. Rotates keys on failure."""
        last_error: Exception | None = None
        for _ in range(len(self.keys)):
            try:
                client = self._get_client()
                print(f"  🔄 Trying key: {self.current_key[:8]}...")
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
                output = response.text.strip()
                return self._parse_json(output)
            except Exception as exc:
                print(f"  ❌ Key failed: {self.current_key[:8]}... — {exc}")
                last_error = exc

        raise RuntimeError(f"All Gemini keys failed. Last error: {last_error}")

    # ------------------------------------------------------------------
    # JSON parser
    # ------------------------------------------------------------------

    def _parse_json(self, output: str) -> dict:
        start = output.find("{")
        end = output.rfind("}")
        if start == -1 or end == -1:
            raise ValueError("No valid JSON object found between { and }")
        json_text = output[start : end + 1]

        def escape_html(m: re.Match) -> str:
            return re.sub(r'="([^"]*)"', r'=\"\1\"', m.group(0))

        json_text = re.sub(r"<[^>]+>", escape_html, json_text)
        json_text = re.sub(r'(?<!")\b0+(\d+)\b(?!")', lambda m: str(int(m.group(0))), json_text)
        return json.loads(json_text)
