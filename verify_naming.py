import sys
import os
sys.path.append(os.getcwd())
from src.adapters.filesystem import FilesystemWriter
import asyncio

async def verify():
    writer = FilesystemWriter("./vault_test")
    raw_title = '少个分号 on X: "如何在路由器上部署 Clash'
    sanitized = writer._sanitize_filename(raw_title)
    print(f"Original: {raw_title}")
    print(f"Sanitized: {sanitized}")
    
    # Expected: 少个分号 on X- '如何在路由器上部署 Clash
    if ":" in sanitized or '"' in sanitized:
        print("FAILURE: Invalid characters remaining")
    else:
        print("SUCCESS: Filename is safe and readable")

if __name__ == "__main__":
    asyncio.run(verify())
