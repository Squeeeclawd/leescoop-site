#!/usr/bin/env python3
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'public' / 'branding' / 'leescoop-social-art.png'
OUT = ROOT / 'public' / 'branding' / 'leescoop-social-preview.png'
W, H = 1216, 704

if not SOURCE.exists():
    raise SystemExit(f'Missing source art: {SOURCE}')

art = Image.open(SOURCE).convert('RGB')

# Use the uploaded square art as the visual source, but convert it to a
# standard large social-card ratio. A direct square OG image gets cropped badly
# in too many places; this keeps the full logo readable.
bg = art.resize((W, W), Image.Resampling.LANCZOS).crop((0, (W - H) // 2, W, (W - H) // 2 + H))
bg = bg.filter(ImageFilter.GaussianBlur(24))

# Slight dark teal wash to keep the centered mark crisp and reduce noisy edges.
overlay = Image.new('RGBA', (W, H), (3, 26, 37, 74))
card = bg.convert('RGBA')
card.alpha_composite(overlay)

d = ImageDraw.Draw(card)
# Soft vignette/frame.
d.rounded_rectangle((20, 20, W - 20, H - 20), radius=42, outline=(248, 243, 232, 72), width=3)
d.rounded_rectangle((36, 36, W - 36, H - 36), radius=34, outline=(139, 210, 222, 82), width=2)

# Fit the complete square logo safely inside the landscape preview.
logo_size = 650
logo = art.resize((logo_size, logo_size), Image.Resampling.LANCZOS).convert('RGBA')
mask = Image.new('L', (logo_size, logo_size), 0)
md = ImageDraw.Draw(mask)
md.rounded_rectangle((0, 0, logo_size, logo_size), radius=36, fill=255)
shadow = Image.new('RGBA', (logo_size + 44, logo_size + 44), (0, 0, 0, 0))
sd = ImageDraw.Draw(shadow)
sd.rounded_rectangle((22, 22, 22 + logo_size, 22 + logo_size), radius=42, fill=(0, 0, 0, 122))
shadow = shadow.filter(ImageFilter.GaussianBlur(18))

x = (W - logo_size) // 2
y = (H - logo_size) // 2
card.alpha_composite(shadow, (x - 22, y - 22))
logo_card = Image.new('RGBA', (logo_size, logo_size), (0, 0, 0, 0))
logo_card.paste(logo, (0, 0), mask)
bd = ImageDraw.Draw(logo_card)
bd.rounded_rectangle((0, 0, logo_size - 1, logo_size - 1), radius=36, outline=(248, 243, 232, 228), width=5)
card.alpha_composite(logo_card, (x, y))

OUT.parent.mkdir(parents=True, exist_ok=True)
card.convert('RGB').save(OUT, quality=95, optimize=True)
print(OUT)
