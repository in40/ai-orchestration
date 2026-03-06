import asyncio
import sys
sys.path.insert(0, '/root/qwen/base/it-lead-mcp-server/web-ui/backend')
from main import browse_git_directory

async def test():
    try:
        result = await browse_git_directory("ae01686a-e9a7-4825-9022-7d6c3c1801a0")
        print("✅ Function returned:", result)
    except Exception as e:
        print("❌ Exception:", type(e).__name__, e)

asyncio.run(test())
