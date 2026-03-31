#!/usr/bin/env python3
import subprocess
import sys

# Try converting using libreoffice with HTML intermediate
html_content = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial, sans-serif; max-width: 900px; margin: 40px auto; line-height: 1.6; }
        h1 { color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }
        h2 { color: #34495e; margin-top: 30px; border-bottom: 2px solid #95a5a6; padding-bottom: 8px; }
        h3 { color: #7f8c8d; margin-top: 20px; }
        h4 { color: #95a5a6; }
        table { border-collapse: collapse; width: 100%; margin: 20px 0; }
        th, td { border: 1px solid #bdc3c7; padding: 12px; text-align: left; }
        th { background-color: #3498db; color: white; }
        tr:nth-child(even) { background-color: #ecf0f1; }
        code { background-color: #f4f4f4; padding: 2px 6px; border-radius: 3px; font-family: 'Courier New', monospace; }
        pre { background-color: #2c3e50; color: #ecf0f1; padding: 15px; border-radius: 5px; overflow-x: auto; }
        ul, ol { margin-left: 20px; }
        strong { color: #2980b9; }
        hr { border: none; border-top: 2px solid #bdc3c7; margin: 30px 0; }
    </style>
</head>
<body>
"""

# Read markdown and do basic conversion
with open('DOCKER_SERVICES.md', 'r') as f:
    md_content = f.read()

# Simple markdown to HTML conversion
import re

lines = md_content.split('\n')
in_code_block = False
in_table = False
table_lines = []

for line in lines:
    # Code blocks
    if line.startswith('```'):
        if in_code_block:
            html_content += '</pre>\n'
            in_code_block = False
        else:
            html_content += '<pre><code>'
            in_code_block = True
        continue
    
    if in_code_block:
        html_content += line + '\n'
        continue
    
    # Tables
    if '|' in line and line.strip().startswith('|'):
        if '|---' in line:
            continue
        if not in_table:
            in_table = True
            html_content += '<table>\n'
            # Header row
            cells = [c.strip() for c in line.split('|')[1:-1]]
            html_content += '<tr>' + ''.join(f'<th>{c}</th>' for c in cells) + '</tr>\n'
        else:
            # Data row
            cells = [c.strip() for c in line.split('|')[1:-1]]
            # Remove markdown formatting from cells
            cells = [re.sub(r'`([^`]+)`', r'<code>\1</code>', c) for c in cells]
            html_content += '<tr>' + ''.join(f'<td>{c}</td>' for c in cells) + '</tr>\n'
        continue
    elif in_table:
        html_content += '</table>\n'
        in_table = False
    
    # Headers
    if line.startswith('# '):
        html_content += f'<h1>{line[2:]}</h1>\n'
    elif line.startswith('## '):
        html_content += f'<h2>{line[3:]}</h2>\n'
    elif line.startswith('### '):
        html_content += f'<h3>{line[4:]}</h3>\n'
    elif line.startswith('#### '):
        html_content += f'<h4>{line[5:]}</h4>\n'
    
    # Horizontal rule
    elif line.strip() == '---':
        html_content += '<hr>\n'
    
    # Lists
    elif line.strip().startswith('- ') or line.strip().startswith('* '):
        text = line.strip()[2:]
        text = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', text)
        text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
        html_content += f'<li>{text}</li>\n'
    
    # Regular paragraphs
    elif line.strip():
        text = line
        text = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', text)
        text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
        text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
        html_content += f'<p>{text}</p>\n'
    else:
        html_content += '<br>\n'

if in_table:
    html_content += '</table>\n'

html_content += """
</body>
</html>
"""

# Write HTML file
with open('DOCKER_SERVICES.html', 'w') as f:
    f.write(html_content)

print("Created HTML file")

# Try to convert to DOCX using libreoffice
try:
    result = subprocess.run(
        ['libreoffice', '--headless', '--convert-to', 'docx', 'DOCKER_SERVICES.html'],
        capture_output=True,
        text=True,
        cwd='/home/coldzera/Desktop/qcc-monitoring'
    )
    if result.returncode == 0:
        print("Successfully converted to DOCKER_SERVICES.docx")
    else:
        print(f"Conversion failed: {result.stderr}")
except Exception as e:
    print(f"Error: {e}")
    print("HTML file created, please open DOCKER_SERVICES.html in LibreOffice/Word and save as DOCX")
