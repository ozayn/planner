#!/usr/bin/env python3
"""
Generate Planner favicon and app icons in SignalMap style:
gray rounded square with 3 horizontal white bars (progressively shorter).
"""
from PIL import Image, ImageDraw

# White background, black bars
BG = (255, 255, 255)
BARS = (0, 0, 0)


def draw_icon(size: int) -> Image.Image:
    """Draw the icon at given size. Design matches SignalMap icon.svg."""
    img = Image.new("RGB", (size, size), color=BG)
    draw = ImageDraw.Draw(img)

    # Rounded rect: scale corner radius with size (6 at 32px)
    rx = max(2, int(6 * size / 32))
    draw.rounded_rectangle([(0, 0), (size - 1, size - 1)], radius=rx, fill=BG, outline=BG)

    # 3 bars: scale from 32px base
    # Bar 1: x=8, y=12, w=16, h=2
    # Bar 2: x=8, y=16, w=12, h=2
    # Bar 3: x=8, y=20, w=8, h=2
    scale = size / 32
    bars = [
        (8 * scale, 12 * scale, 16 * scale, 2 * scale),
        (8 * scale, 16 * scale, 12 * scale, 2 * scale),
        (8 * scale, 20 * scale, 8 * scale, 2 * scale),
    ]
    for x, y, w, h in bars:
        x, y, w, h = int(x), int(y), max(1, int(w)), max(1, int(h))
        draw.rounded_rectangle([(x, y), (x + w, y + h)], radius=max(1, int(scale)), fill=BARS)

    return img


def main():
    import os
    out_dir = os.path.join(os.path.dirname(__file__), "..", "static", "icons")
    os.makedirs(out_dir, exist_ok=True)

    for sz in (32, 180, 192, 512):
        img = draw_icon(sz)
        path = os.path.join(out_dir, f"planner-icon-{sz}.png")
        img.save(path, "PNG")
        print(f"Wrote {path}")


if __name__ == "__main__":
    main()
