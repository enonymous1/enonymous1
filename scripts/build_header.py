"""Build an animated voxel/Minecraft-style header GIF: JUSTIN LYONS in pixel font.

Pure Pillow, deterministic. No generated imagery, no third-party assets.
Output: profile-readme-v2-push/header.gif (1200x360, 20 frames, looping).
"""
import math
import random
from pathlib import Path

from PIL import Image, ImageDraw

W, H = 1200, 360
FRAMES = 20
OUT = Path(__file__).resolve().parent.parent / "header.gif"

# 5x7 pixel font, only the glyphs we need. "1" = on, "0" = off.
FONT = {
    "E": ["11111", "10000", "10000", "11110", "10000", "10000", "11111"],
    "I": ["00100", "00100", "00100", "00100", "00100", "00100", "00100"],
    "J": ["00111", "00010", "00010", "00010", "00010", "10010", "01100"],
    "L": ["10000", "10000", "10000", "10000", "10000", "10000", "11111"],
    "M": ["10001", "11011", "10101", "10101", "10001", "10001", "10001"],
    "N": ["10001", "11001", "10101", "10011", "10001", "10001", "10001"],
    "O": ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
    "S": ["01111", "10000", "10000", "01110", "00001", "00001", "11110"],
    "T": ["11111", "00100", "00100", "00100", "00100", "00100", "00100"],
    "U": ["10001", "10001", "10001", "10001", "10001", "10001", "01110"],
    "Y": ["10001", "10001", "10001", "01110", "00100", "00100", "00100"],
    "1": ["00100", "01100", "00100", "00100", "00100", "00100", "01110"],
    " ": ["00000", "00000", "00000", "00000", "00000", "00000", "00000"],
}


def draw_pixel_word(draw, word, x0, y0, px, fill, shadow=None, shadow_off=(5, 5)):
    """Draw a pixel-font word; each glyph pixel is one solid square with a
    darker bottom/right edge for a voxel feel. Returns total width."""
    x = x0
    for ch in word:
        glyph = FONT[ch]
        for row in range(7):
            for col in range(5):
                if glyph[row][col] == "1":
                    px0, py0 = x + col * px, y0 + row * px
                    if shadow:
                        draw.rectangle(
                            [px0 + shadow_off[0], py0 + shadow_off[1],
                             px0 + px - 1 + shadow_off[0], py0 + px - 1 + shadow_off[1]],
                            fill=shadow,
                        )
                    draw.rectangle([px0, py0, px0 + px - 1, py0 + px - 1], fill=fill)
                    # voxel bevel: dark bottom/right edge only, so the
                    # letter fill stays solid against the light sky.
                    draw.line([(px0 + px - 1, py0), (px0 + px - 1, py0 + px - 1)], fill=(90, 90, 90), width=2)
                    draw.line([(px0, py0 + px - 1), (px0 + px - 1, py0 + px - 1)], fill=(90, 90, 90), width=2)
        x += 6 * px  # 5 glyph cols + 1 gap col
    return x - x0 - px  # width without trailing gap


def word_width(word, px):
    return len(word) * 6 * px - px


def iso_cube(draw, cx, cy, s, top, left, right):
    """Isometric cube centred at (cx, cy), half-width s. Top/left/right faces."""
    draw.polygon([(cx, cy - s), (cx + s, cy - s // 2), (cx, cy), (cx - s, cy - s // 2)], fill=top)
    draw.polygon([(cx - s, cy - s // 2), (cx, cy), (cx, cy + s), (cx - s, cy + s // 2)], fill=left)
    draw.polygon([(cx, cy), (cx + s, cy - s // 2), (cx + s, cy + s // 2), (cx, cy + s)], fill=right)
    draw.line([(cx, cy - s), (cx + s, cy - s // 2), (cx, cy), (cx - s, cy - s // 2), (cx, cy - s)],
              fill=(0, 0, 0), width=2)


def sparkle(draw, cx, cy, r, color, phase):
    if phase % 2:
        draw.line([(cx - r, cy), (cx + r, cy)], fill=color, width=2)
        draw.line([(cx, cy - r), (cx, cy + r)], fill=color, width=2)
    else:
        draw.polygon([(cx, cy - r), (cx + 2, cy - 2), (cx + r, cy), (cx + 2, cy + 2),
                      (cx, cy + r), (cx - 2, cy + 2), (cx - r, cy), (cx - 2, cy - 2)], fill=color)


def static_background():
    """Sky, sun, ground blocks. Drawn once; frames copy it."""
    img = Image.new("RGB", (W, H))
    draw = ImageDraw.Draw(img)
    # Sky gradient: Minecraft blue at top to pale near horizon.
    top, bottom = (110, 190, 235), (190, 225, 245)
    for y in range(282):
        t = y / 281
        draw.line([(0, y), (W, y)], fill=tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)))
    # Square sun with lighter core.
    draw.rectangle([1060, 28, 1116, 84], fill=(255, 214, 64))
    draw.rectangle([1072, 40, 1104, 72], fill=(255, 236, 140))
    # Ground: grass / dirt / stone block rows, 20px blocks, seeded noise.
    rng = random.Random(42)
    block = 20
    for row, (base, speck) in enumerate([
        ((86, 170, 52), (70, 145, 40)),      # grass
        ((134, 96, 52), (110, 76, 40)),      # dirt
        ((128, 128, 128), (105, 105, 105)),  # stone
    ]):
        y0 = 282 + row * 26
        for bx in range(0, W, block):
            draw.rectangle([bx, y0, bx + block - 1, y0 + 25], fill=base)
            for _ in range(14):
                sx = bx + rng.randrange(block)
                sy = y0 + rng.randrange(26)
                draw.point((sx, sy), fill=speck)
            draw.rectangle([bx, y0, bx + block - 1, y0 + 25], outline=(0, 0, 0))
    # Grass blades on the top edge.
    for bx in range(0, W, 20):
        if rng.random() < 0.6:
            gx = bx + rng.randrange(4, 16)
            draw.line([(gx, 282), (gx, 274)], fill=(70, 145, 40), width=3)
    return img


def cloud(draw, x, y, scale, color=(255, 255, 255)):
    """Blocky pixel cloud from rectangles."""
    parts = [(0, 12, 70, 24), (18, 0, 52, 14), (62, 8, 96, 26), (88, 14, 118, 28)]
    for x0, y0, x1, y1 in parts:
        draw.rectangle([x + x0 * scale, y + y0 * scale, x + x1 * scale, y + y1 * scale], fill=color)


def torch(draw, x, y, frame):
    draw.rectangle([x - 3, y, x + 3, y + 26], fill=(101, 67, 50))
    flame_h = 16 if frame % 2 == 0 else 12
    draw.polygon([(x - 7, y), (x + 7, y), (x, y - flame_h)], fill=(255, 140, 0))
    draw.polygon([(x - 3, y), (x + 3, y), (x, y - flame_h + 6)], fill=(255, 220, 80))


def build_frame(base, frame):
    img = base.copy()
    draw = ImageDraw.Draw(img)
    # Drifting clouds (wrap around).
    for (cx, cy, speed, scale) in [(60, 40, 6, 1), (430, 22, 4, 1), (820, 58, 8, 1)]:
        x = (cx + frame * speed) % (W + 160) - 80
        cloud(draw, int(x), cy, scale)
    # Floating voxel cubes, bobbing.
    cubes = [
        (78, 210, 26, (120, 220, 120), (86, 170, 52), (60, 130, 38), 0.0),   # grass
        (78, 148, 20, (150, 225, 255), (90, 170, 235), (60, 130, 200), 1.1),  # diamond ore
        (1122, 205, 26, (255, 215, 90), (220, 170, 50), (180, 135, 35), 0.6),  # gold
        (1122, 142, 20, (255, 120, 120), (210, 60, 60), (170, 45, 45), 1.8),  # redstone
    ]
    for cx, cy, s, top, left, right, ph in cubes:
        bob = round(5 * math.sin(frame * 0.45 + ph))
        iso_cube(draw, cx, cy + bob, s, top, left, right)
        sparkle(draw, cx + s + 8, cy + bob - s, 7, (255, 255, 255), frame + int(ph * 3))
    # Torches flanking the name.
    torch(draw, 108, 246, frame)
    torch(draw, 1092, 246, frame + 1)

    # Name: letters drop in one by one, then bob gently.
    name = "JUSTIN LYONS"
    px = 13
    total_w = word_width(name, px)
    x0 = (W - total_w) // 2
    y0 = 108
    x = x0
    for idx, ch in enumerate(name):
        if ch == " ":
            x += 6 * px
            continue
        delay = idx  # one frame per letter
        t = frame - delay
        if t < 0:
            x += 6 * px
            continue
        if t < 4:
            off = -72 * ((4 - t) / 4) ** 2
        else:
            off = 3 * math.sin((frame - 4) * 0.35 + idx * 0.4)
        # Shadow word pass first for this letter, then the letter itself.
        draw_pixel_word(draw, ch, x, int(y0 + off), px, (240, 240, 240),
                        shadow=(30, 30, 30), shadow_off=(5, 6))
        x += 6 * px

    # Subtitle: gamertag in small pixel font, gold.
    sub = "ENONYMOUS1"
    spx = 6
    sw = word_width(sub, spx)
    draw_pixel_word(draw, sub, (W - sw) // 2, 232, spx, (255, 200, 60),
                    shadow=(60, 40, 0), shadow_off=(2, 2))
    return img


def main():
    base = static_background()
    frames = [build_frame(base, f) for f in range(FRAMES)]
    frames[0].save(
        OUT, save_all=True, append_images=frames[1:],
        duration=120, loop=0, optimize=True,
    )
    # Export stills for visual verification.
    for i in (0, 5, 11, 19):
        frames[i].save(f"/tmp/header-frame-{i}.png")  # verification stills, not shipped
    print(f"wrote {OUT} {OUT.stat().st_size} bytes, {len(frames)} frames, {frames[0].size}")


if __name__ == "__main__":
    main()
