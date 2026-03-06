import asyncio
import shutil
import os
from datetime import datetime
from src.pipeline.core import Pipeline
from src.pipeline.processors import RawMessageToContent, ContentToNote, SaveNote
from src.adapters.filesystem import FilesystemWriter
import pytest
from src.domain.models import RawMessage

@pytest.mark.asyncio
async def test_pipeline():
    # Setup
    test_vault = "./test_vault"
    if os.path.exists(test_vault):
        shutil.rmtree(test_vault)
    
    fs_writer = FilesystemWriter(test_vault)
    
    pipeline = Pipeline()
    pipeline.add_step(RawMessageToContent())
    pipeline.add_step(ContentToNote())
    pipeline.add_step(SaveNote(fs_writer))
    
    # Mock Data
    raw_msg = RawMessage(
        chat_id=123,
        message_id=1,
        user_id=456,
        text="Check this out: https://example.com/cool-article\nIt's really interesting! #cool #tech",
        date=datetime.now(),
        forward_from="some_channel"
    )
    
    print("Running pipeline...")
    result = await pipeline.run(raw_msg)
    print("Pipeline finished.")
    
    # Verify
    print(f"Result type: {type(result)}")
    print(f"Filename: {result.filename}")
    
    files = os.listdir(test_vault)
    print(f"Files in vault: {files}")
    
    if files:
        with open(os.path.join(test_vault, files[0]), 'r') as f:
            content = f.read()
            print("--- File Content ---")
            print(content)
            print("--------------------")

if __name__ == "__main__":
    asyncio.run(test_pipeline())
