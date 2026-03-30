import os
import glob
import re

# Correct icons for each tool template
icons = {
    'merge.html': '🔗',
    'split.html': '✂️',
    'compress.html': '🗜️',
    'rotate.html': '🔄',
    'watermark.html': '💧',
    'page_numbers.html': '🔢',
    'protect.html': '🔒',
    'unlock.html': '🔓',
    'pdf_to_jpg.html': '🖼️',
    'jpg_to_pdf.html': '📷',
    'pdf_to_word.html': '📝',
    'word_to_pdf.html': '📃'
}

for filename, emoji in icons.items():
    path = os.path.join('templates', filename)
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()

        # We know the icon is inside <div class="tool-icon-lg">...</div>
        # Use regex to find and replace whatever is in there.
        # This safely blows away the mojibake.
        new_content = re.sub(r'<div class="tool-icon-lg">.*?</div>', 
                             f'<div class="tool-icon-lg">{emoji}</div>', 
                             content, 
                             flags=re.DOTALL)
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Updated icon for {filename} to {emoji}")
