#!/usr/bin/env python3
"""mkthemes.py -- build the Peacock themes from assets/themes/themeN.jpg (N = 1..9).

For every picture: a 640x400 wallpaper and a 96x60 thumbnail of it.  Colour pictures on white paper get a darkened, blurred copy of
themselves as backdrop with the paper made transparent; the black line-art pictures (8, 9; picture 9 is inverted first) sit on black with a
faint glow.  Output assets/themes.raw:
    THUMBS : 9 x 45 sectors  (96*60*4 bytes, 0x00RRGGBB little-endian, padded)
    WALLS  : 9 x 1500 sectors (640*400*3 bytes, R,G,B, padded)
Usage: mkthemes.py assets/themes assets/themes.raw [--preview sheet.png]"""
import sys, glob, colorsys
from PIL import Image, ImageFilter, ImageChops, ImageEnhance, ImageDraw, ImageStat
WW, WH, TW, TH = 640, 400, 96, 60
N = 9
DARK = {8, 9}
GLOW = {8: (217, 169, 59), 9: (242, 146, 43)}

def matte(src):
    """alpha of the picture: 0 on white paper, 1 on ink; edges feathered so full-bleed pictures do not show a hard rectangle"""
    a = Image.new('L', src.size); ap, sp = a.load(), src.load()
    for y in range(src.height):
        for x in range(src.width):
            ap[x, y] = max(0, min(255, int(((255 - min(sp[x, y])) - 6) * 3.2)))
    return a.filter(ImageFilter.GaussianBlur(0.8))

def build_dark(path, n):
    src = Image.open(path).convert('RGB')
    if n == 9: src = ImageChops.invert(src)
    fh = int(WH * 0.96); fw = int(src.width * fh / src.height)
    if fw > WW * 0.9: fw = int(WW * 0.9); fh = int(src.height * fw / src.width)
    fg = src.resize((fw, fh), Image.LANCZOS)
    a = fg.convert('L').point(lambda v: max(0, min(255, int((v - 8) * 3.0))))
    edge = Image.new('L', fg.size, 0); ImageDraw.Draw(edge).rectangle((6, 6, fw - 7, fh - 7), fill=255)
    a = ImageChops.multiply(a, edge.filter(ImageFilter.GaussianBlur(5)))
    gr, gg, gb = GLOW[n]
    bg = Image.new('RGB', (WW, WH)); bp = bg.load()
    for y in range(WH):
        for x in range(WW):
            dx, dy = (x - WW / 2) / (WW / 2), (y - WH / 2) / (WH / 2)
            t = max(0.0, 1.0 - (dx * dx * 0.9 + dy * dy)) ** 1.6 * 0.16
            bp[x, y] = (int(4 + gr * t), int(4 + gg * t), int(6 + gb * t))
    out = bg.copy()
    out.paste(fg, ((WW - fw) // 2, (WH - fh) // 2), a)
    return out, fg, a

def build(path, n=0):
    if n in DARK: return build_dark(path, n)
    src = Image.open(path).convert('RGB')
    # ---- foreground size: a little under the full height
    fh = int(WH * 0.92); fw = int(src.width * fh / src.height)
    if fw > WW * 0.92: fw = int(WW * 0.92); fh = int(src.height * fw / src.width)
    fg = src.resize((fw, fh), Image.LANCZOS)
    a = matte(fg)
    edge = Image.new('L', fg.size, 0); ImageDraw.Draw(edge).rectangle((6, 6, fw - 7, fh - 7), fill=255)
    a = ImageChops.multiply(a, edge.filter(ImageFilter.GaussianBlur(5)))
    # ---- backdrop: colour of the ink only (normalised blur), spread over the whole screen, then darkened
    big = Image.new('RGB', (WW, WH), (0, 0, 0)); abig = Image.new('L', (WW, WH), 0)
    sc = max(WW / src.width, WH / src.height)
    cov = src.resize((int(src.width * sc) + 1, int(src.height * sc) + 1), Image.LANCZOS)
    l, t = (cov.width - WW) // 2, (cov.height - WH) // 2
    cov = cov.crop((l, t, l + WW, t + WH)); ca = matte(cov)
    wc = ImageChops.multiply(cov, Image.merge('RGB', (ca, ca, ca)))
    num = wc.filter(ImageFilter.GaussianBlur(34)); den = ca.filter(ImageFilter.GaussianBlur(34))
    nump, denp, bgi = num.load(), den.load(), Image.new('RGB', (WW, WH)); bp = bgi.load()
    for y in range(WH):
        for x in range(WW):
            d = denp[x, y] / 255
            r, g, b = nump[x, y]
            if d < 0.02: bp[x, y] = (0, 0, 0)
            else:
                bp[x, y] = (min(255, int(r / d)), min(255, int(g / d)), min(255, int(b / d)))
    # colour where there was ink, otherwise fade to the overall average ink colour
    avg = ImageStat.Stat(wc, mask=ca.point(lambda v: 255 if v > 40 else 0)).mean
    avg = tuple(int(c) for c in avg) if all(avg) else (60, 70, 90)
    base = Image.new('RGB', (WW, WH), avg)
    wmask = den.point(lambda v: min(255, v * 3))
    bgc = Image.composite(bgi, base, wmask)
    bgc = ImageEnhance.Color(bgc).enhance(1.35).filter(ImageFilter.GaussianBlur(14))
    px = list(bgc.getdata()); lum = sum(sum(p) / 3 for p in px) / len(px)
    k = min(0.62, 0.30 * 255 / max(lum, 40))
    bg = bgc.point(lambda v: min(255, int(v * k)))
    vig = Image.new('L', (WW, WH)); vp = vig.load()
    for y in range(WH):
        for x in range(WW):
            dx, dy = (x - WW / 2) / (WW / 2), (y - WH / 2) / (WH / 2)
            vp[x, y] = int(max(0, min(255, 255 - 60 * (dx * dx + dy * dy))))
    bg = ImageChops.multiply(bg, Image.merge('RGB', (vig, vig, vig)))
    out = bg.copy()
    out.paste(fg, ((WW - fw) // 2, (WH - fh) // 2), a)
    return out, fg, a

def accent(img):
    """a saturated, reasonably bright colour from the picture, plus a dark tint for the taskbar"""
    best = None
    pix = list(img.resize((40, 30)).getdata())
    cand = []
    for (r, g, b) in pix:
        h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
        if s > 0.45 and v > 0.45: cand.append((s * v, (r, g, b)))
    cand.sort(reverse=True)
    top = [c for _, c in cand[:max(8, len(cand) // 6)]] or [(31, 111, 235)]
    n = len(top)
    return tuple(sum(c[i] for c in top) // n for i in range(3))

if __name__ == '__main__':
    d, outp = sys.argv[1], sys.argv[2]
    thumbs, walls, sheet, acc = bytearray(), bytearray(), [], []
    for i in range(1, N + 1):
        w, fg, a = build('%s/theme%d.jpg' % (d, i), i)
        t = w.resize((TW, TH), Image.LANCZOS)
        tb = bytearray()
        for (r, g, b) in t.getdata(): tb += bytes((b, g, r, 0))
        thumbs += tb + bytes(45 * 512 - len(tb))
        raw = w.tobytes()
        walls += raw + bytes(1500 * 512 - len(raw))
        sheet.append(w)
        ac = accent(fg)
        acc.append(ac); print('theme%d accent #%02X%02X%02X' % ((i,) + ac))
    open(outp, 'wb').write(bytes(thumbs) + bytes(walls))
    print('mkthemes: %s: thumbs %d sectors + walls %d sectors' % (outp, len(thumbs) // 512, len(walls) // 512))
    if '--preview' in sys.argv:
        cw = Image.new('RGB', (WW * 3, WH * 3))
        for i, w in enumerate(sheet): cw.paste(w, ((i % 3) * WW, (i // 3) * WH))
        cw.save(sys.argv[sys.argv.index('--preview') + 1])
