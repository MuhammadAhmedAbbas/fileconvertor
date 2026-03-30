import os, glob

replacements = {
    "â†": "←",
    "âœ‚ï¸": "✂️"
}

for text_file in glob.glob('templates/*.html'):
    with open(text_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    changed = False
    for bad, good in replacements.items():
        if bad in content:
            content = content.replace(bad, good)
            changed = True
            
    if changed:
        with open(text_file, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Fixed {text_file}")
