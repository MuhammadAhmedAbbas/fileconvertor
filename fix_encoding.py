import os
import glob

fix_count = 0
for text_file in glob.glob('templates/*.html'):
    with open(text_file, 'r', encoding='utf-8') as f:
        content = f.read()

    content = content.replace('\ufeff', '')

    if 'â' in content or 'ð' in content:
        try:
            fixed = content.encode('windows-1252').decode('utf-8')
            with open(text_file, 'w', encoding='utf-8') as f:
                f.write(fixed)
            print(f'Fixed {text_file}')
            fix_count += 1
        except Exception as e:
            print(f'Trying fallback for {text_file} due to {e}')
            changes = 0
            replacements = {
                "â† ": "← ", "ðŸ”—": "🔗", "ðŸ“„": "📄", "â€”": "—", "â€¦": "…", 
                "âœ…": "✅", "â¬‡": "⬇", "ðŸ”’": "🔒", "ðŸ–¼": "🖼", "âš™": "⚙", 
                "ðŸ”„": "🔄", "ðŸ’¾": "💾", "ðŸ“‚": "📂", "â€œ": '"', "â€ ": '"', 
                "â€˜": "'", "â€™": "'"
            }
            fixed = content
            for bad, good in replacements.items():
                if bad in fixed:
                    fixed = fixed.replace(bad, good)
                    changes += 1
            if changes > 0:
                with open(text_file, 'w', encoding='utf-8') as f:
                    f.write(fixed)
                print(f'Fallback fixed {text_file}')
                fix_count += 1
            else:
                print(f'Fallback no changes for {text_file}')

print(f'Total fixed: {fix_count}')
