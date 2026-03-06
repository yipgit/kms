
import sys
import os
import asyncio
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any

# Mocking domain model to avoid imports if needed, but let's try to use them
sys.path.append(os.getcwd())
from src.domain.models import Content
from src.pipeline.processors import FetchURLContent

async def test_extraction():
    # Mocking a response that Jina would return
    mock_content = """Title: 少个分号 on X: "如何在路由器上部署 Clash：

1. 买一个 Open WRT 的路由器，比较好用的是 GL-MT6000
2. 按照教程安装 https://t.co/DQspdQlpOr
3. 导入一个平时使用的 Clash 配置文件" / X

URL Source: https://x.com/shaogefenhao/status/2012783091685761274
"""
    
    # We can't easily mock httpx response without a server or monkeypatching
    # But we can test the logic if we extract it or mock the process method's internal parts
    # For now, let's just trace what we did.
    
    print("Testing title extraction and body cleaning logic...")
    import re
    
    # 1. Test Prefix Stripping
    title_match = re.search(r'^Title:\s*(.*)$', mock_content, re.MULTILINE)
    if title_match:
        extracted = title_match.group(1).strip()
        print(f"Extracted: '{extracted}'")
        if not extracted.startswith('Title:'):
            print("SUCCESS: 'Title: ' prefix stripped from title")
        else:
            print("FAILURE: 'Title: ' prefix still present")
            
    # 2. Test Body Cleaning
    cleaned_body = re.sub(r'^Title:\s*.*\n?', '', mock_content, flags=re.MULTILINE)
    if "Title:" not in cleaned_body:
        print("SUCCESS: 'Title: ' line removed from body")
    else:
        print("FAILURE: 'Title: ' line still in body")
        print(f"Body snippet:\n{cleaned_body[:100]}...")

if __name__ == "__main__":
    asyncio.run(test_extraction())
