import asyncio
from app.value_extractor import _check_openai_uptime
from app.value_extractor import _check_gemini_uptime

async def test_openai_uptime():
    result = await _check_openai_uptime()
    print(f"OpenAI uptime check result: {result}")

async def test_gemini_uptime():
    result = await _check_gemini_uptime()
    print(f"Gemini uptime check result: {result}")

if __name__ == "__main__":
    asyncio.run(test_openai_uptime())
    asyncio.run(test_gemini_uptime())
