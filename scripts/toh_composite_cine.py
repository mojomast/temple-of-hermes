#!/usr/bin/env python3
"""Composite cinematic portraits onto generated temple backgrounds.

Run from the temple-of-hermes repo root after the source files already live
under art/source/. Then run toh_art_convert.py on art/source/composites/.

Portraits are cropped/resized cine v3 stills from clawpocalypse-now (Southpaw
uses the turbofit portrait file). Backgrounds contain no generated faces.
Nous Girl is flipped horizontally on the splash, wallpaper, and threshold
header so she faces the temple.
"""
from __future__ import annotations
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageChops

ROOT = Path(__file__).resolve().parents[1]
FONT = Path("/usr/share/fonts/truetype/sand-box/google/IBM Plex Serif/IBMPlexSerif-Bold.ttf")


def fit_cover(img, tw, th):
    img = img.convert("RGB")
    sw, sh = img.size
    sc = max(tw / sw, th / sh)
    nw, nh = max(1, int(sw * sc + 0.5)), max(1, int(sh * sc + 0.5))
    img = img.resize((nw, nh), Image.Resampling.LANCZOS)
    L, T = (nw - tw) // 2, (nh - th) // 2
    return img.crop((L, T, L + tw, T + th))


def clean_portrait(im: Image.Image) -> Image.Image:
    im = im.convert("RGBA")
    px = im.load()
    w, h = im.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a == 0:
                px[x, y] = (0, 0, 0, 0)
                continue
            if a < 252 and r > g + 25 and b > g + 15:
                l = (int(g) * 2 + min(r, b)) // 3
                px[x, y] = (l, l, l, max(0, a - 90))
            elif a < 24:
                px[x, y] = (r, g, b, 0)
    a = im.getchannel("A")
    a = ImageChops.multiply(a, a.filter(ImageFilter.MinFilter(3)))
    im.putalpha(a)
    return im


def scale_to_height(im: Image.Image, height: int) -> Image.Image:
    w, h = im.size
    nw = max(1, int(w * (height / h) + 0.5))
    return im.resize((nw, height), Image.Resampling.LANCZOS)


def paste_shadow(base: Image.Image, sprite: Image.Image, xy, blur=8, opacity=110):
    x, y = xy
    sh = Image.new("RGBA", base.size, (0, 0, 0, 0))
    shadow = Image.new("RGBA", sprite.size, (0, 0, 0, 0))
    a = sprite.getchannel("A").point(lambda v: int(v * opacity / 255) if v else 0)
    shadow.putalpha(a)
    sh.alpha_composite(shadow, (x + 6, y + 8))
    sh = sh.filter(ImageFilter.GaussianBlur(blur))
    out = Image.alpha_composite(base.convert("RGBA"), sh)
    out.alpha_composite(sprite, (x, y))
    return out


def outlined_text(draw, xy, text, font, fill, outline=(0, 0, 0, 220), width=3):
    x, y = xy
    for dx in range(-width, width + 1):
        for dy in range(-width, width + 1):
            if dx * dx + dy * dy <= width * width:
                draw.text((x + dx, y + dy), text, font=font, fill=outline)
    draw.text((x, y), text, font=font, fill=fill)


def crop_band(img: Image.Image, tw, th, top_ratio=0.22):
    img = img.convert("RGB")
    w, h = img.size
    sc = tw / w
    nw, nh = tw, max(th, int(h * sc + 0.5))
    img = img.resize((nw, nh), Image.Resampling.LANCZOS)
    top = max(0, min(nh - th, int((nh - th) * top_ratio)))
    return img.crop((0, top, tw, top + th))


def compose_splash():
    bg = fit_cover(Image.open(ROOT / "art/source/generated/toh-bg-boot-splash.jpg"), 640, 480)
    girl = clean_portrait(Image.open(ROOT / "art/source/cine/nous_girl.png"))
    girl = girl.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    girl = scale_to_height(girl, 470)
    x = 640 - girl.size[0] + 18
    y = 480 - girl.size[1] + 8
    canvas = paste_shadow(bg, girl, (x, y), blur=10, opacity=140)
    title = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(title)
    f1 = ImageFont.truetype(str(FONT), 34)
    f2 = ImageFont.truetype(str(FONT), 42)
    outlined_text(d, (22, 368), "THE TEMPLE", f1, (255, 255, 85, 255), width=3)
    outlined_text(d, (22, 408), "OF HERMES", f2, (255, 255, 85, 255), width=3)
    canvas = Image.alpha_composite(canvas, title)
    out = ROOT / "art/source/composites/toh-boot-splash.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(out, "PNG")
    print("wrote", out)


def compose_wallpaper():
    bg = fit_cover(Image.open(ROOT / "art/source/generated/toh-bg-wallpaper.jpg"), 640, 480)
    girl = clean_portrait(Image.open(ROOT / "art/source/cine/nous_girl.png"))
    girl = girl.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    girl = scale_to_height(girl, 390)
    x = 640 - girl.size[0] - 8
    y = 480 - girl.size[1] + 16
    canvas = paste_shadow(bg, girl, (x, y), blur=12, opacity=150)
    out = ROOT / "art/source/composites/toh-nous-girl.png"
    canvas.convert("RGB").save(out, "PNG")
    print("wrote", out)


def compose_header(bg_path: Path, portrait_name: str, stem: str, side: str, flip=False, band_ratio=0.28):
    bg = Image.open(bg_path)
    port = clean_portrait(Image.open(ROOT / "art/source/cine" / f"{portrait_name}.png"))
    if flip:
        port = port.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    strip = crop_band(bg, 1280, 80, top_ratio=band_ratio)
    p80 = scale_to_height(port, 86)
    xy = (8, 80 - p80.size[1] + 4) if side == "left" else (1280 - p80.size[0] - 8, 80 - p80.size[1] + 4)
    strip_c = paste_shadow(strip, p80, xy, blur=4, opacity=120)
    p_strip = ROOT / f"art/source/composites/{stem}.png"
    strip_c.convert("RGB").save(p_strip, "PNG")
    plate = crop_band(bg, 640, 160, top_ratio=band_ratio)
    p160 = scale_to_height(port, 168)
    xy2 = (4, 160 - p160.size[1] + 6) if side == "left" else (640 - p160.size[0] - 4, 160 - p160.size[1] + 6)
    plate_c = paste_shadow(plate, p160, xy2, blur=6, opacity=130)
    p_plate = ROOT / f"art/source/composites/{stem}-plate.png"
    plate_c.convert("RGB").save(p_plate, "PNG")
    print("wrote", p_strip, p_plate)


def main():
    compose_splash()
    compose_wallpaper()
    compose_header(ROOT / "art/source/generated/toh-bg-header-southpaw.jpg", "southpaw", "header-southpaw", "left", False, 0.42)
    compose_header(ROOT / "art/source/generated/toh-bg-header-dojo.jpg", "teknium", "header-dojo", "right", False, 0.30)
    compose_header(ROOT / "art/source/generated/toh-bg-header-offerings.jpg", "don_piedro", "header-offerings", "right", False, 0.22)
    compose_header(ROOT / "art/source/generated/toh-bg-boot-splash.jpg", "nous_girl", "header-threshold", "right", True, 0.18)


if __name__ == "__main__":
    main()
