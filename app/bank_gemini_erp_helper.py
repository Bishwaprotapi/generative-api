"""Gemini helper for ERP keyset (credentials/gemini_keys-erp.json).

Supports:
- PDF (uploaded via Gemini Files API)
- Image inputs (png/jpg/jpeg/webp) sent as inline bytes
- DOC/DOCX converted to PDF via LibreOffice then uploaded

This is intentionally separate from existing helpers to avoid changing
behaviour in CV endpoints.
"""

from __future__ import annotations

import io
import json
import os
import pathlib
import pypdfium2
import re
import subprocess
import time
from itertools import cycle

from google import genai
from google.genai import types


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


def convert_doc_to_pdf(input_file: str) -> str:
    """Convert a DOC/DOCX file to PDF using LibreOffice headless."""
    if not os.path.exists(input_file):
        raise FileNotFoundError(input_file)

    soffice = _find_libreoffice()
    if not soffice:
        raise RuntimeError("LibreOffice not installed")

    out_dir = os.path.join(os.getcwd(), "uploads")
    os.makedirs(out_dir, exist_ok=True)

    base_name = os.path.splitext(os.path.basename(input_file))[0]
    cmd = [soffice, "--headless", "--convert-to", "pdf", input_file, "--outdir", out_dir]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "DOC/DOCX conversion failed")

    generated_pdf = os.path.join(out_dir, base_name + ".pdf")
    if not os.path.exists(generated_pdf):
        raise RuntimeError("PDF conversion failed")

    return generated_pdf


def process_file_to_pdf(file_path: str) -> str | None:
    """Return a PDF path for PDF/DOC/DOCX inputs; otherwise None."""
    ext = os.path.basename(file_path).rsplit(".", 1)[-1].lower()
    if ext == "pdf":
        return file_path
    if ext in ("doc", "docx"):
        return convert_doc_to_pdf(file_path)
    return None


def extract_first_last_pages_as_images(pdf_path: str, scale: float = 1.5) -> list[bytes]:
    """Extract first and last page as images using pypdfium2 (Google's PDFium).
    
    PDFium is the same PDF engine used by Chrome - extremely fast.
    
    Args:
        pdf_path: Path to the PDF file
        scale: Scale factor for image quality (1.5 = 150 DPI equivalent, optimal for speed/quality)
    
    Returns:
        List of image bytes (first page, last page if different from first)
    """
    pdf = pypdfium2.PdfDocument(pdf_path)
    page_count = len(pdf)
    
    images = []
    
    # Get first page
    first_page = pdf[0]
    pil_image = first_page.render(scale=scale).to_pil()
    img_byte_arr = io.BytesIO()
    pil_image.save(img_byte_arr, format='PNG')
    images.append(img_byte_arr.getvalue())
    
    # Get last page (only if different from first)
    if page_count > 1:
        last_page = pdf[page_count - 1]
        pil_image = last_page.render(scale=scale).to_pil()
        img_byte_arr = io.BytesIO()
        pil_image.save(img_byte_arr, format='PNG')
        images.append(img_byte_arr.getvalue())
    
    pdf.close()
    return images


class GeminiSessionERP:
    """Gemini client that rotates keys loaded from gemini_keys-erp.json."""

    def __init__(self) -> None:
        self.keys = self._load_keys()
        if not self.keys:
            raise RuntimeError("No Google API keys available in credentials/gemini_keys-erp.json")
        self._key_cycle = cycle(self.keys)
        self.current_key: str | None = None

    def _load_keys(self) -> list[str]:
        try:
            with open("credentials/gemini_keys-erp.json", encoding="utf-8") as f:
                return list(json.load(f).values())
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def _get_client(self) -> genai.Client:
        self.current_key = next(self._key_cycle)
        return genai.Client(api_key=self.current_key)

    def call_api_with_pdf_file(self, prompt: str, pdf_path: str) -> dict:
        """Upload a PDF via Files API and call Gemini; rotate keys on failure."""
        last_error: Exception | None = None
        for _ in range(len(self.keys)):
            try:
                client = self._get_client()
                uploaded = client.files.upload(file=pathlib.Path(pdf_path))

                # Wait for processing with optimized polling (0.5s intervals, 60s timeout)
                max_wait_time = 60
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

                try:
                    client.files.delete(name=uploaded.name)
                except Exception:
                    pass

                return self._parse_json(response.text.strip())
            except Exception as exc:
                last_error = exc

        raise RuntimeError(f"All Gemini ERP keys failed. Last error: {last_error}")

    def call_api_with_image_bytes(self, prompt: str, image_bytes: bytes, mime_type: str) -> dict:
        """Send prompt + image bytes to Gemini; rotate keys on failure."""
        last_error: Exception | None = None
        for _ in range(len(self.keys)):
            try:
                client = self._get_client()
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=[
                        types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                        prompt,
                    ],
                )
                return self._parse_json(response.text.strip())
            except Exception as exc:
                last_error = exc

        raise RuntimeError(f"All Gemini ERP keys failed. Last error: {last_error}")

    def analyze_bank_statement_optimized(self, pdf_path: str) -> dict:
        """Analyze bank statement using pypdfium2 (Google's PDFium) for fast image conversion.
        
        Optimized for speed (2-3 seconds) by:
        1. Using pypdfium2 (Chrome's PDF engine) for ultra-fast PDF to image conversion
        2. Converting only first and last pages to images
        3. Analyzing first page first
        4. Only analyzing last page if needed
        
        Args:
            pdf_path: Path to the bank statement PDF
            
        Returns:
            Dictionary with extracted bank statement data
        """
        prompt = """Extract the following information from this bank statement page and return as JSON:
{
  "Account_Number": "string",
  "Account_Name": "string",
  "Opening_Balance": number,
  "Closing_Balance": number,
  "Bank_Name": "string",
  "Bank_Branch": "string",
  "Statement_Generation_Date": "string",
  "Client_Address": "string"
}

If any field is not found on this page, set it to null."""

        # Extract first and last pages as images using pypdfium2
        images = extract_first_last_pages_as_images(pdf_path, scale=1.5)
        
        # Try first page first
        try:
            result = self.call_api_with_image_bytes(prompt, images[0], "image/png")
            
            # Check if all required fields are present (not null)
            required_fields = ["Account_Number", "Account_Name", "Bank_Name"]
            missing_fields = [field for field in required_fields if result.get(field) is None]
            
            # If all critical fields found, return result
            if not missing_fields:
                return result
            
            # Otherwise, try last page if available
            if len(images) > 1:
                last_page_result = self.call_api_with_image_bytes(prompt, images[1], "image/png")
                # Merge results: prefer first page values, use last page for missing fields
                for key, value in last_page_result.items():
                    if result.get(key) is None and value is not None:
                        result[key] = value
                
        except Exception:
            # If first page fails, try last page if available
            if len(images) > 1:
                result = self.call_api_with_image_bytes(prompt, images[1], "image/png")
            else:
                raise
        
        return result

    def _parse_json(self, output: str) -> dict:
        start = output.find("{")
        end = output.rfind("}")
        if start == -1 or end == -1:
            raise ValueError("No valid JSON object found in Gemini response")
        json_text = output[start : end + 1]

        def escape_html(m: re.Match) -> str:
            return re.sub(r'="([^"]*)"', r'=\\"\\1\\"', m.group(0))

        json_text = re.sub(r"<[^>]+>", escape_html, json_text)
        json_text = re.sub(r"\uFEFF", "", json_text)
        return json.loads(json_text)

def guess_image_mime(filename: str) -> str:
    ext = os.path.basename(filename).rsplit(".", 1)[-1].lower()
    if ext in ("jpg", "jpeg"):
        return "image/jpeg"
    if ext == "png":
        return "image/png"
    if ext == "webp":
        return "image/webp"
    return "application/octet-stream"
