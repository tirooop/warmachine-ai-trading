import os

def fix_encoding_issues(directory="."):
    """Recursively fix encoding issues in all Python files"""
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                try:
                    # Try to read file content
                    with open(file_path, "rb") as f:
                        content = f.read()
                    
                    # Check if file has encoding issues
                    if content.startswith(b"\xff") or b"\x00" in content:
                        print(f"Fixing file: {file_path}")
                        # Try to create a clean version
                        if file == "__init__.py":
                            with open(file_path, "w", encoding="utf-8") as f:
                                f.write("# Auto-fixed by repair script\n")
                                f.write("\"\"\"Automatic generated file\"\"\"\n")
                        else:
                            # Remove all null bytes
                            clean_content = content.replace(b"\x00", b"")
                            # If it starts with bad bytes, replace it
                            if clean_content.startswith(b"\xff"):
                                clean_content = b"# Fixed file\n" + clean_content[1:]
                            with open(file_path, "wb") as f:
                                f.write(clean_content)
                except Exception as e:
                    print(f"Cannot fix {file_path}: {str(e)}")

if __name__ == "__main__":
    print("Starting to fix all files...")
    fix_encoding_issues()
    print("Fix completed!")
