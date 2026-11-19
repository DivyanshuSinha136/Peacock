#!/usr/bin/env python3
"""Generates the hand-made SVG art used by README.md (no external services)."""
import os
O='docs/img'
os.makedirs(O+'/icons',exist_ok=True); os.makedirs(O+'/badges',exist_ok=True)
def w(p,s): open(os.path.join(O,p),'w').write(s)
F='font-family="Segoe UI,Helvetica,Arial,sans-serif"'
M='font-family="Consolas,Menlo,DejaVu Sans Mono,monospace"'

# ---------- banner ----------
feathers=''
import math
for i in range(11):
    a=math.radians(-62+i*12.4)
    x2=1120+math.sin(a)*300; y2=330-math.cos(a)*300
    col=['#14b8a6','#06b6d4','#3b82f6','#8b5cf6','#d946ef'][i%5]
    feathers+=f'<path d="M1120 330 Q{(1120+x2)/2+math.cos(a)*30:.0f} {(330+y2)/2:.0f} {x2:.0f} {y2:.0f}" stroke="{col}" stroke-width="5" fill="none" opacity=".55" stroke-linecap="round"/>'
    feathers+=f'<ellipse cx="{x2:.0f}" cy="{y2:.0f}" rx="15" ry="22" transform="rotate({math.degrees(a):.0f} {x2:.0f} {y2:.0f})" fill="url(#eye)" stroke="#fbbf24" stroke-width="2"/><ellipse cx="{x2:.0f}" cy="{y2:.0f}" rx="5" ry="8" transform="rotate({math.degrees(a):.0f} {x2:.0f} {y2:.0f})" fill="#0f172a"/>'
w('banner.svg',f'''<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="340" viewBox="0 0 1280 340" role="img" aria-label="Peacock OS banner">
<defs>
<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#042f2e"/><stop offset=".55" stop-color="#1e1b4b"/><stop offset="1" stop-color="#3b0764"/></linearGradient>
<linearGradient id="tt" x1="0" x2="1"><stop offset="0" stop-color="#5eead4"/><stop offset=".5" stop-color="#93c5fd"/><stop offset="1" stop-color="#e879f9"/></linearGradient>
<radialGradient id="eye"><stop offset="0" stop-color="#22d3ee"/><stop offset=".6" stop-color="#2563eb"/><stop offset="1" stop-color="#7c3aed"/></radialGradient>
<pattern id="grid" width="32" height="32" patternUnits="userSpaceOnUse"><path d="M32 0H0V32" fill="none" stroke="#fff" stroke-opacity=".05"/></pattern>
<clipPath id="c"><rect width="1280" height="340" rx="18"/></clipPath>
</defs>
<g clip-path="url(#c)"><rect width="1280" height="340" fill="url(#bg)"/><rect width="1280" height="340" fill="url(#grid)"/>
{feathers}
<circle cx="1120" cy="330" r="46" fill="#0f766e" stroke="#5eead4" stroke-width="3"/></g>
<g transform="translate(70,70)">
<rect width="64" height="64" rx="14" fill="url(#tt)"/><path d="M32 14c-9 0-14 7-14 15 0 6 3 10 8 12l-4 11 10-8 10 8-4-11c5-2 8-6 8-12 0-8-5-15-14-15z" fill="#042f2e"/><circle cx="32" cy="27" r="5" fill="#fbbf24"/></g>
<text x="150" y="122" {F} font-size="68" font-weight="800" fill="url(#tt)">Peacock OS</text>
<text x="72" y="190" {F} font-size="26" fill="#e2e8f0">A bootable 64-bit glass-UI desktop operating system</text>
<text x="72" y="226" {F} font-size="26" fill="#e2e8f0">written <tspan font-weight="700" fill="#fbbf24">entirely in KingCobra</tspan> - bootloader to browser.</text>
<g {M} font-size="16" fill="#cbd5e1"><text x="72" y="282">v1.9  |  x86-64 BIOS  |  64-bit RGBA16 pipeline  |  USB  |  PCI  |  ACPI  |  TCP/IP  |  3D</text></g>
</svg>''')

# ---------- icons (64x64, rounded tile + glyph) ----------
def icon(name,c1,c2,glyph):
    w(f'icons/{name}.svg',f'''<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64" role="img" aria-label="{name}"><defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{c1}"/><stop offset="1" stop-color="{c2}"/></linearGradient></defs><rect width="64" height="64" rx="15" fill="url(#g)"/><g fill="none" stroke="#fff" stroke-width="3.6" stroke-linecap="round" stroke-linejoin="round">{glyph}</g></svg>''')
icon('boot','#0d9488','#0f766e','<path d="M32 12v20"/><path d="M20 22a17 17 0 1 0 24 0"/>')
icon('ui','#2563eb','#7c3aed','<rect x="12" y="14" width="40" height="30" rx="4"/><path d="M12 22h40M24 52h16M32 44v8"/>')
icon('render','#7c3aed','#c026d3','<rect x="14" y="14" width="22" height="22" rx="3"/><rect x="26" y="26" width="22" height="22" rx="3" fill="#fff" fill-opacity=".25"/>')
icon('fs','#d97706','#b45309','<ellipse cx="32" cy="18" rx="16" ry="6"/><path d="M16 18v26c0 3 7 6 16 6s16-3 16-6V18M16 31c0 3 7 6 16 6s16-3 16-6"/>')
icon('net','#0891b2','#2563eb','<circle cx="32" cy="32" r="19"/><path d="M13 32h38M32 13c-9 10-9 28 0 38M32 13c9 10 9 28 0 38"/>')
icon('usb','#16a34a','#0d9488','<path d="M32 50V16M32 16l-5 6h10zM32 38l-10-8v-5M32 32l10-6v-4"/><circle cx="22" cy="22" r="3"/><rect x="39" y="17" width="6" height="5"/>')
icon('pci','#dc2626','#ea580c','<rect x="14" y="20" width="36" height="22" rx="3"/><path d="M20 42v8M28 42v8M36 42v8M44 42v8M22 28h8v6h-8z"/>')
icon('threads','#4f46e5','#2563eb','<path d="M14 20h36M14 32h36M14 44h36"/><circle cx="24" cy="20" r="3" fill="#fff"/><circle cx="40" cy="32" r="3" fill="#fff"/><circle cx="28" cy="44" r="3" fill="#fff"/>')
icon('3d','#db2777','#7c3aed','<path d="M32 12l18 10v20L32 52 14 42V22z"/><path d="M14 22l18 10 18-10M32 32v20"/>')
icon('apps','#0ea5e9','#6366f1','<rect x="14" y="14" width="14" height="14" rx="3"/><rect x="36" y="14" width="14" height="14" rx="3"/><rect x="14" y="36" width="14" height="14" rx="3"/><rect x="36" y="36" width="14" height="14" rx="3"/>')
icon('tests','#059669','#65a30d','<path d="M16 33l11 11 21-23"/>')
icon('lang','#b45309','#be123c','<path d="M24 18l-12 14 12 14M40 18l12 14-12 14M35 14l-6 36"/>')

# ---------- badges ----------
def badge(name,l,r,col):
    lw=len(l)*7+16; rw=len(r)*7+16; t=lw+rw
    w(f'badges/{name}.svg',f'''<svg xmlns="http://www.w3.org/2000/svg" width="{t}" height="22" role="img" aria-label="{l}: {r}"><linearGradient id="s" x2="0" y2="100%"><stop offset="0" stop-color="#fff" stop-opacity=".18"/><stop offset="1" stop-opacity=".12"/></linearGradient><clipPath id="r"><rect width="{t}" height="22" rx="4"/></clipPath><g clip-path="url(#r)"><rect width="{lw}" height="22" fill="#334155"/><rect x="{lw}" width="{rw}" height="22" fill="{col}"/><rect width="{t}" height="22" fill="url(#s)"/></g><g fill="#fff" text-anchor="middle" {F} font-size="11"><text x="{lw/2}" y="15">{l}</text><text x="{lw+rw/2}" y="15" font-weight="700">{r}</text></g></svg>''')
badge('version','version','1.9','#0d9488')
badge('arch','arch','x86-64 BIOS','#2563eb')
badge('lang','written in','KingCobra','#b45309')
badge('license','license','MIT','#16a34a')
badge('tests','host suites','17 passing','#059669')
badge('qemu','tested on','QEMU only','#d97706')

# ---------- diagrams ----------
def box(x,y,wd,h,t,sub,c):
    return f'<rect x="{x}" y="{y}" width="{wd}" height="{h}" rx="10" fill="{c}" fill-opacity=".16" stroke="{c}" stroke-width="2"/><text x="{x+wd/2}" y="{y+h/2-(2 if sub else -5)}" text-anchor="middle" {F} font-size="15" font-weight="700" fill="#0f172a">{t}</text>'+(f'<text x="{x+wd/2}" y="{y+h/2+15}" text-anchor="middle" {F} font-size="11.5" fill="#334155">{sub}</text>' if sub else '')
def arrow(x1,y1,x2,y2):
    return f'<path d="M{x1} {y1}L{x2} {y2}" stroke="#475569" stroke-width="2" marker-end="url(#a)"/>'
defs='<defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0L10 5L0 10z" fill="#475569"/></marker></defs>'
# architecture
L=[('Applications','Files - Browser - Terminal - Notes - Settings - App Builder - 3D Studio - Paint - ...','#7c3aed'),
('Desktop shell','windows - dock - top bar - launcher - glass panels - themes - damage rects','#2563eb'),
('Graphics','64-bit RGBA16 back buffer - fonts - SVG - 3D rasteriser - dithered flush','#0891b2'),
('Services','KCFS 2 store - threads - TCP/IP + DHCP + DNS - HTTP/HTML - .pea loader','#059669'),
('Drivers and buses','PCI - ACPI - USB UHCI (HID, mass storage) - RTL8139 - ATA - PS/2 - VBE/DISPI - serial','#d97706'),
('Boot','stage 1 (MBR) - stage 2 (A20, E820, protected to long mode) - kernel at 2 MiB','#dc2626')]
s=''
for i,(t,sub,c) in enumerate(L):
    y=20+i*70; s+=box(40,y,820,56,t,sub,c)
w('architecture.svg',f'<svg xmlns="http://www.w3.org/2000/svg" width="900" height="{20+6*70}" viewBox="0 0 900 {20+6*70}" role="img" aria-label="Peacock OS layered architecture"><rect width="900" height="{20+6*70}" rx="14" fill="#f8fafc"/>{defs}{s}</svg>')
# boot flow
steps=[('BIOS','loads LBA 0','#64748b'),('Stage 1','512 B MBR','#dc2626'),('Stage 2','A20 / E820 / long mode','#ea580c'),('Kernel','LBA 5 -> 0x200000','#d97706'),('Hardware','PCI - ACPI - USB - NIC','#059669'),('Desktop','mount KCFS 2, UI loop','#7c3aed')]
s=''
for i,(t,sub,c) in enumerate(steps):
    x=20+i*165; s+=box(x,40,140,64,t,sub,c)
    if i<5: s+=arrow(x+140,72,x+165,72)
dk=[('stage1','1 sec','#dc2626',1),('stage2','4 sec','#ea580c',4),('kernel','~2108 sec','#d97706',14),('KCFS 2 store','slots A/B + logo + bundle + themes','#7c3aed',20)]
s+=f'<text x="20" y="150" {F} font-size="13" font-weight="700" fill="#0f172a">Disk image (17 MiB)</text>'
xs=[20,60,120,520]; ws=[38,58,398,440]
for (t,sub,c,_),x,wd in zip(dk,xs,ws):
    s+=f'<rect x="{x}" y="160" width="{wd}" height="40" fill="{c}" fill-opacity=".2" stroke="{c}" stroke-width="2"/><text x="{x+wd/2}" y="185" text-anchor="middle" {F} font-size="11" fill="#0f172a">{t if wd<100 else t+" - "+sub}</text>'
w('boot-flow.svg',f'<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="230" viewBox="0 0 1000 230" role="img" aria-label="Boot flow and disk layout"><rect width="1000" height="230" rx="14" fill="#f8fafc"/>{defs}{s}</svg>')
# pipeline
P=[('Apps / widgets','draw 8-bit colours','#7c3aed'),('Back buffer','*u64  A:R:G:B 16 bit each','#2563eb'),('Glass + blend','mixp / mixpp in 16-bit','#0891b2'),('Damage rects','only dirty areas','#059669'),('flush','Bayer dither to 24/32 bpp','#d97706'),('VBE/DISPI LFB','up to 4096x2400','#dc2626')]
s=''
for i,(t,sub,c) in enumerate(P):
    x=20+i*165; s+=box(x,40,140,70,t,sub,c)
    if i<5: s+=arrow(x+140,75,x+165,75)
s+=f'<text x="20" y="150" {F} font-size="12.5" fill="#334155">Blending and glass blur keep 16 bits per channel, so gradients and translucent layers do not band.</text><text x="20" y="172" {F} font-size="12.5" fill="#334155">Pixels that are exactly representable in 8 bits skip dithering (fast path). Output depth is limited by the display hardware.</text>'
w('render-pipeline.svg',f'<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="200" viewBox="0 0 1000 200" role="img" aria-label="64-bit rendering pipeline"><rect width="1000" height="200" rx="14" fill="#f8fafc"/>{defs}{s}</svg>')
