#!/usr/bin/env python3
"""mklogo.py -- turn assets/peacock-logo.jpg into assets/logo.raw: 160x280 pixels, 32-bit 0x00RRGGBB little-endian (what kernel/splash.kc draws).
Near-white paper is snapped to pure white so the picture blends into the white splash background.  Usage: mklogo.py in.jpg out.raw"""
import sys
from PIL import Image
W, H = 160, 280
im = Image.open(sys.argv[1]).convert('RGB').resize((W, H), Image.LANCZOS)
out = bytearray()
for (r, g, b) in im.getdata():
    r, g, b = (min(255, c * 255 // 244) for c in (r, g, b))
    out += bytes((b, g, r, 0))
open(sys.argv[2], 'wb').write(out)
print('mklogo: %dx%d -> %s (%d bytes, %d sectors)' % (W, H, sys.argv[2], len(out), (len(out) + 511) // 512))
