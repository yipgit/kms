
import sys
import os
import asyncio
import shutil

sys.path.append(os.getcwd())
from src.adapters.filesystem import FilesystemWriter

async def test_folders():
    vault_path = "./test_vault_folders"
    if os.path.exists(vault_path):
        shutil.rmtree(vault_path)
    os.makedirs(vault_path)
    
    writer = FilesystemWriter(vault_path)
    
    # 1. Test Directory Listing
    os.makedirs(os.path.join(vault_path, "Travel/Yunnan"))
    os.makedirs(os.path.join(vault_path, "Work/Projects"))
    os.makedirs(os.path.join(vault_path, ".obsidian")) # Should be hidden
    
    dirs = writer.list_vault_directories()
    print(f"Detected directories: {dirs}")
    expected = ['/', 'Travel', 'Travel/Yunnan', 'Work', 'Work/Projects']
    if all(d in dirs for d in expected) and '.obsidian' not in dirs:
        print("SUCCESS: Directory listing works correctly and ignores hidden folders.")
    else:
        print(f"FAILURE: Directory listing mismatch. Got {dirs}")

    # 2. Test File Moving
    file_path = os.path.join(vault_path, "TestNote.md")
    with open(file_path, 'w') as f:
        f.write("test content")
    
    print(f"Moving {file_path} to 'Travel/Yunnan'...")
    new_path = await writer.move_note(file_path, "Travel/Yunnan")
    
    if os.path.exists(new_path) and "Travel/Yunnan" in new_path:
        print(f"SUCCESS: File moved to {new_path}")
    else:
        print(f"FAILURE: File not found at destination: {new_path}")

    # 3. Test Moving to Root
    print(f"Moving back to root...")
    root_path = await writer.move_note(new_path, "/")
    if os.path.dirname(root_path) == os.path.abspath(vault_path):
        print(f"SUCCESS: File moved back to root: {root_path}")
    else:
        print(f"FAILURE: File not in root. Path: {root_path}")

    # 4. Test Auto-creating folders
    print("Moving to new folder 'New/Subfolder'...")
    final_path = await writer.move_note(root_path, "New/Subfolder")
    if os.path.exists(final_path) and "New/Subfolder" in final_path:
        print(f"SUCCESS: Auto-created folder and moved file: {final_path}")
    else:
        print(f"FAILURE: Auto-create move failed.")

if __name__ == "__main__":
    asyncio.run(test_folders())
    # Cleanup
    # shutil.rmtree("./test_vault_folders")
