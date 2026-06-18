import asyncio
import os
import sys

# Add project root to sys.path
sys.path.append(os.getcwd())

from app.ai.ocr.engine import extract_text_from_document
from app.core.config import settings

async def test_ocr():
    urls = {
        "KTP (709)": "https://boyblanco.my.id/documents/f0b1e3a32f684cb5a1f6d52f3e3817ce.pdf",
        "Ijazah (709/710)": "https://boyblanco.my.id/documents/9a40269295114294b9d683148b008a2a.pdf"
    }
    
    for label, url in urls.items():
        print(f"\n--- Extracting OCR for {label} ---")
        try:
            # force_fallback = False to make the real API call
            text = await extract_text_from_document(url, force_fallback=False)
            print(f"Extracted length: {len(text)}")
            print("Extracted Text:")
            print(text[:2000])
        except Exception as e:
            print(f"Failed to extract: {e}")

if __name__ == "__main__":
    asyncio.run(test_ocr())
