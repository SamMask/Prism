#!/usr/bin/env python3
"""Download Google Fonts for Local Insight (offline-first)"""
import requests
import os

# Create fonts directory
os.makedirs('static/fonts', exist_ok=True)

# Font URLs (woff2 format for modern browsers)
fonts = [
    # Inter - Body text
    ('https://fonts.gstatic.com/s/inter/v13/UcC73FwrK3iLTeHuS_fvQtMwCp50KnMa1ZL7.woff2', 'Inter-Regular.woff2'),
    ('https://fonts.gstatic.com/s/inter/v13/UcC73FwrK3iLTeHuS_fvQtMwCp50KnMa0ZL7SUc.woff2', 'Inter-Medium.woff2'),
    ('https://fonts.gstatic.com/s/inter/v13/UcC73FwrK3iLTeHuS_fvQtMwCp50KnMa2pL7SUc.woff2', 'Inter-SemiBold.woff2'),
    ('https://fonts.gstatic.com/s/inter/v13/UcC73FwrK3iLTeHuS_fvQtMwCp50KnMa25L7SUc.woff2', 'Inter-Bold.woff2'),
    
    # Outfit - Headings
    ('https://fonts.gstatic.com/s/outfit/v11/QGYyz_MVcBeNP4NjuGObqx1XmO1I4TC1C4G-EiAou6Y.woff2', 'Outfit-Regular.woff2'),
    ('https://fonts.gstatic.com/s/outfit/v11/QGYyz_MVcBeNP4NjuGObqx1XmO1I4TC1O4G-EiAou6Y.woff2', 'Outfit-Medium.woff2'),
    ('https://fonts.gstatic.com/s/outfit/v11/QGYyz_MVcBeNP4NjuGObqx1XmO1I4TC1x4a-EiAou6Y.woff2', 'Outfit-SemiBold.woff2'),
    ('https://fonts.gstatic.com/s/outfit/v11/QGYyz_MVcBeNP4NjuGObqx1XmO1I4TC1_oa-EiAou6Y.woff2', 'Outfit-Bold.woff2'),
    
    # JetBrains Mono - Code
    ('https://fonts.gstatic.com/s/jetbrainsmono/v18/tDbY2o-flEEny0FZhsfKu5WU4zr3E_BX0PnT8RD8yKxjOVGa.woff2', 'JetBrainsMono-Regular.woff2'),
]

print("Downloading fonts for Local Insight...")
for url, filename in fonts:
    filepath = f'static/fonts/{filename}'
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        with open(filepath, 'wb') as f:
            f.write(response.content)
        print(f"  ✅ {filename} ({len(response.content):,} bytes)")
    except Exception as e:
        print(f"  ❌ {filename}: {e}")

print("\n✅ Fonts downloaded successfully!")
