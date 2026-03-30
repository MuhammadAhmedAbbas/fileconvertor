import os
import glob
import re

for text_file in glob.glob('templates/*.html'):
    with open(text_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # We enforce correct icons for the other UI elements
    # All tools use the same drop zone icon, result icon, and download arrow anyway!
    
    # 1. Drop zone icon
    content = re.sub(r'<div class="dz-icon">.*?</div>', '<div class="dz-icon">📄</div>', content, flags=re.DOTALL)
    
    # 2. Result icon
    content = re.sub(r'<div class="result-icon">.*?</div>', '<div class="result-icon">✅</div>', content, flags=re.DOTALL)
    
    # 3. Download button arrow
    # The arrow is usually at the start of the button text. Let's just blindly replace the known mojibake for it.
    if 'â¬‡' in content:
        content = content.replace('â¬‡', '⬇')
    if 'ðŸ“„' in content: 
         content = content.replace('ðŸ“„', '📄')
    
    # 4. In case the spinner has anything weird (it usually has: <p>Merging your PDFs...</p>)
    # Replace â€¦ with ellipsis ...
    if 'â€¦' in content:
        content = content.replace('â€¦', '…')
        
    # Replace other known symbols
    content = content.replace('â€”', '—')
    
    with open(text_file, 'w', encoding='utf-8') as f:
        f.write(content)
        
    print(f"Fixed rest of UI for {text_file}")
