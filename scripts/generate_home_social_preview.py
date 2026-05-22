#!/usr/bin/env python3
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import math

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'public' / 'branding' / 'leescoop-social-preview.png'
W, H = 1216, 704

COLORS = {
    'deep': '#07506F',
    'teal': '#197894',
    'coastal': '#4FA7BC',
    'glass': '#8BD2DE',
    'coral': '#D94B32',
    'orange': '#F28B42',
    'yellow': '#F7DE69',
    'sand': '#F8F3E8',
    'ink': '#063A52',
    'mist': '#DDEEF1',
    'black': '#031A25',
}

def font(size, bold=False):
    candidates = [
        '/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf' if bold else '/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf',
        '/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf' if bold else '/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf' if bold else '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()

def hex_to_rgb(value):
    value = value.lstrip('#')
    return tuple(int(value[i:i+2], 16) for i in (0, 2, 4))

def lerp(a, b, t):
    return int(a + (b - a) * t)

def gradient_bg():
    img = Image.new('RGB', (W, H), COLORS['ink'])
    px = img.load()
    c1 = hex_to_rgb(COLORS['deep'])
    c2 = hex_to_rgb(COLORS['teal'])
    c3 = hex_to_rgb(COLORS['black'])
    for y in range(H):
        ty = y / (H - 1)
        for x in range(W):
            tx = x / (W - 1)
            radial = max(0, 1 - math.hypot((tx - 0.82) * 1.05, (ty - 0.16) * 1.6))
            base = tuple(lerp(c1[i], c3[i], ty * 0.72) for i in range(3))
            glow = tuple(lerp(base[i], c2[i], radial * 0.42) for i in range(3))
            px[x, y] = glow
    return img.convert('RGBA')

def rounded_crop(im, size, radius=34):
    im = Image.open(ROOT / im).convert('RGB') if isinstance(im, str) else im.convert('RGB')
    im.thumbnail((size[0] * 1.15, size[1] * 1.15), Image.Resampling.LANCZOS)
    left = max(0, (im.width - size[0]) // 2)
    top = max(0, (im.height - size[1]) // 2)
    im = im.crop((left, top, left + size[0], top + size[1]))
    mask = Image.new('L', size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, size[0], size[1]), radius=radius, fill=255)
    out = Image.new('RGBA', size, (0,0,0,0))
    out.paste(im.convert('RGBA'), (0,0), mask)
    return out

def paste_card(base, path, xy, size, angle=0, radius=28):
    card = Image.new('RGBA', (size[0] + 28, size[1] + 28), (0,0,0,0))
    shadow = Image.new('RGBA', card.size, (0,0,0,0))
    sd = ImageDraw.Draw(shadow)
    sd.rounded_rectangle((14, 14, 14 + size[0], 14 + size[1]), radius=radius+4, fill=(0,0,0,105))
    shadow = shadow.filter(ImageFilter.GaussianBlur(12))
    card.alpha_composite(shadow)
    img = rounded_crop(path, size, radius=radius)
    border = Image.new('RGBA', size, (0,0,0,0))
    bd = ImageDraw.Draw(border)
    bd.rounded_rectangle((0,0,size[0]-1,size[1]-1), radius=radius, outline=(248,243,232,210), width=5)
    img.alpha_composite(border)
    card.alpha_composite(img, (14,14))
    if angle:
        card = card.rotate(angle, resample=Image.Resampling.BICUBIC, expand=True)
    base.alpha_composite(card, xy)

img = gradient_bg()
d = ImageDraw.Draw(img)

# Decorative coastal shapes.
d.ellipse((830, -128, 1285, 330), fill=(79,167,188,48))
d.ellipse((910, 34, 1224, 348), fill=(247,222,105,28))
d.ellipse((-96, 438, 326, 854), fill=(25,120,148,60))
for offset, color, width in [(0, COLORS['glass'], 13), (34, COLORS['yellow'], 9), (68, COLORS['orange'], 7)]:
    points = []
    for x in range(-20, 540, 12):
        y = 512 + offset + math.sin(x / 54) * 18
        points.append((x, y))
    d.line(points, fill=color, width=width, joint='curve')

# Right-side stack of LeeScoop story visuals.
paste_card(img, 'public/covers/american-sand-sculpting-championship-2026.png', (780, 55), (365, 212), angle=4)
paste_card(img, 'public/covers/jaycee-park-reopens-after-major-renovation.png', (714, 253), (430, 250), angle=-3)
paste_card(img, 'public/covers/hurricane-preparedness-expo-2026.png', (854, 442), (320, 185), angle=5)

# Left content panel.
panel = Image.new('RGBA', (648, 494), (0,0,0,0))
pd = ImageDraw.Draw(panel)
pd.rounded_rectangle((0,0,648,494), radius=42, fill=(248,243,232,242), outline=(139,210,222,120), width=3)
panel = panel.filter(ImageFilter.GaussianBlur(0.15))
img.alpha_composite(panel, (64, 88))

d = ImageDraw.Draw(img)
# Logo mark inspired by site SVG.
d.ellipse((112, 138, 220, 246), fill=COLORS['deep'])
d.arc((132, 166, 238, 234), 185, 350, fill=COLORS['glass'], width=12)
d.arc((126, 143, 236, 211), 185, 350, fill=COLORS['yellow'], width=8)

# Text lockup.
d.text((245, 135), 'LeeScoop', font=font(78, True), fill=COLORS['ink'])
d.text((249, 216), 'Your scoop on Lee County.', font=font(29, True), fill=COLORS['teal'])

tag = 'LOCAL EVENTS • NEWS • USEFUL UPDATES'
tag_font = font(22, True)
bb = d.textbbox((0,0), tag, font=tag_font)
d.rounded_rectangle((112, 298, 112 + (bb[2]-bb[0]) + 40, 344), radius=23, fill=COLORS['yellow'])
d.text((132, 307), tag, font=tag_font, fill=COLORS['ink'])

headline = ['No ads. No promotion.', 'Just what’s happening nearby.']
y = 382
for line in headline:
    d.text((112, y), line, font=font(38, True), fill=COLORS['ink'])
    y += 49

# Small footer URL.
d.text((112, 522), 'leescoop.com', font=font(24, True), fill=COLORS['coral'])

# Subtle outline frame.
d.rounded_rectangle((22,22,W-23,H-23), radius=42, outline=(139,210,222,100), width=3)
d.rounded_rectangle((35,35,W-36,H-36), radius=34, outline=(248,243,232,45), width=1)

OUT.parent.mkdir(parents=True, exist_ok=True)
img.convert('RGB').save(OUT, quality=95, optimize=True)
print(OUT, Image.open(OUT).size)
