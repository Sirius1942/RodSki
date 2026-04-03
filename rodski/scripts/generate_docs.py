"""Generate documentation from source code"""
import ast
import sys
from pathlib import Path


def generate_keyword_reference(output_path=None):
    """Generate keyword reference from keyword_engine.py docstrings"""
    keyword_file = Path(__file__).parent.parent / 'core' / 'keyword_engine.py'
    if not keyword_file.exists():
        print("keyword_engine.py not found")
        return

    with open(keyword_file, 'r', encoding='utf-8') as f:
        tree = ast.parse(f.read())

    output = ["# Keyword Reference\n\n"]

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            docstring = ast.get_docstring(node)
            if docstring:
                output.append(f"## {node.name}\n\n")
                output.append(f"{docstring}\n\n")

    result = ''.join(output)
    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(result)
    else:
        print(result)


def generate_config_reference(output_path=None):
    """Generate config reference from default_config.yaml"""
    config_file = Path(__file__).parent.parent / 'config' / 'default_config.yaml'
    if not config_file.exists():
        print("default_config.yaml not found")
        return

    with open(config_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    output = ["# Configuration Reference\n\n"]
    output.append("| Key | Description |\n")
    output.append("|-----|-------------|\n")

    for line in lines:
        line = line.strip()
        if line and not line.startswith('#') and ':' in line:
            key = line.split(':')[0].strip()
            output.append(f"| {key} | Configuration option |\n")

    result = ''.join(output)
    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(result)
    else:
        print(result)


def generate_cli_reference(output_path=None):
    """Generate CLI reference from cli.py"""
    cli_file = Path(__file__).parent.parent / 'core' / 'cli.py'
    if not cli_file.exists():
        print("cli.py not found")
        return

    output = ["# CLI Reference\n\n"]
    output.append("Command-line interface documentation.\n\n")

    if cli_file.exists():
        with open(cli_file, 'r', encoding='utf-8') as f:
            tree = ast.parse(f.read())

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                docstring = ast.get_docstring(node)
                if docstring:
                    output.append(f"## {node.name}\n\n")
                    output.append(f"{docstring}\n\n")

    result = ''.join(output)
    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(result)
    else:
        print(result)


if __name__ == '__main__':
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        output = sys.argv[2] if len(sys.argv) > 2 else None

        if cmd == 'keywords':
            generate_keyword_reference(output)
        elif cmd == 'config':
            generate_config_reference(output)
        elif cmd == 'cli':
            generate_cli_reference(output)
        else:
            print("Usage: python generate_docs.py [keywords|config|cli] [output_file]")
    else:
        print("Usage: python generate_docs.py [keywords|config|cli] [output_file]")
