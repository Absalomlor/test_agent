from __future__ import annotations

from typing import Any

def render_message(message: Any) -> str:
    """
    Normalize Strands agent messages into plain text.
    Standardizes output handling by preferring direct attribute access (.text, .content)
    over manual dictionary crawling.
    """
    if message is None:
        return ""

    # กรณีเป็นข้อความอยู่แล้ว
    if isinstance(message, str):
        return message

    # กรณีเป็น Object ของ Strands/LangChain (มักจะมี .text หรือ .content)
    # เราเช็ค .text ก่อนเพราะมักจะเป็น Final Answer ที่ผ่านการ Render แล้ว
    if hasattr(message, "text"):
        return str(message.text)
    
    if hasattr(message, "content"):
        content = message.content
        # บางครั้ง content อาจมาเป็น List ของ Text Block
        if isinstance(content, list):
            return "\n".join(str(item) for item in content)
        return str(content)

    # กรณีเป็น Dictionary (Fallback สำหรับ Raw Result)
    if isinstance(message, dict):
        # พยายามหา key ที่สื่อความหมายที่สุด
        return str(message.get("text") or message.get("content") or message.get("output") or "")

    # กรณีอื่นๆ แปลงเป็น String ตรงๆ
    return str(message)