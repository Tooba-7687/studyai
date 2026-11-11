import io

from google import genai
from django.conf import settings

from .ai_helper import GENERATION_MODEL, get_client


def extract_text(image_file) -> dict:
    """
    Extract text from uploaded image file using Gemini vision.
    Returns dict with text and success status.

    Works on any OS — no Tesseract install needed.
    """
    try:
        mime_type = getattr(image_file, 'content_type', 'image/jpeg') or 'image/jpeg'
        image_bytes = image_file.read()

        part = genai.types.Part.from_bytes(data=image_bytes, mime_type=mime_type)

        client = get_client()
        response = client.models.generate_content(
            model=GENERATION_MODEL,
            contents=[
                part,
                "Extract ALL text from this image. Return exactly the text you see, "
                "preserving layout, math symbols, and equations where possible. "
                "Do not add explanations or commentary — only the extracted text.",
            ],
            config=genai.types.GenerateContentConfig(
                max_output_tokens=900,
                temperature=0.1,
            ),
        )

        text = (response.text or "").strip()

        if text:
            return {
                "success": True,
                "text": text,
                "char_count": len(text),
                "message": f"Successfully extracted {len(text)} characters",
            }
        else:
            return {
                "success": False,
                "text": "",
                "char_count": 0,
                "message": "No text found in image. Try a clearer photo.",
            }

    except Exception as e:
        return {
            "success": False,
            "text": "",
            "char_count": 0,
            "message": f"OCR failed: {str(e)}",
        }
