#!/usr/bin/env python3
"""bootsim.py -- a tiny x86 emulator that runs the Peacock boot stage (build/boot.bin + kernel.bin) against a fake BIOS.

It executes exactly the instruction subset boot/boot.kc emits (16-bit real mode -> 32-bit protected mode -> long mode) and checks
the hand-over contract: kernel loaded at 0x200000 by ATA PIO, E820 map and VBE info at 0x500..0x7FF, page tables built, CR0/CR3/CR4/EFER set,
final jump to the kernel in 64-bit mode.  It is NOT a substitute for QEMU (no paging/segmentation semantics, no timing) -- it catches
logic and encoding mistakes in the boot code.  Usage: bootsim.py peacock.img [--no-lfb-first]"""
import os, struct, sys

class Halt(Exception): pass
FAILS = []

MEM_BYTES = 80 << 20       # enough for a 64 MiB kernel at 0x200000
KBASE = 0x200000
KSEC_OFF = 2556            # u32 kernel sector count at the end of stage 2
KCSUM_OFF = 2552           # u32 kernel checksum just before it
def csum(b):
    b = b + bytes((-len(b)) % 4)
    return sum(struct.unpack('<%dI' % (len(b) // 4), b)) & 0xFFFFFFFF
def check_a20(c):
    ok = c.a20 and c.mode == 64
    print(('  ok   ' if ok else '  FAIL ') + 'A20 enabled and the kernel was reached')
    if not ok: FAILS.append('a20')

class CPU:
    def __init__(s, img, vbe_modes, opt=None):
        opt = opt or {}
        s.mem = bytearray(MEM_BYTES)
        s.img = img
        s.r = [0] * 8          # ax cx dx bx sp bp si di (full 32-bit values)
        s.seg = [0] * 6
        s.ip = 0x7C00; s.mode = 16; s.zf = s.cf = 0
        s.cr = {0: 0, 3: 0, 4: 0}; s.efer = 0; s.gdtr = None
        s.vbe = vbe_modes; s.vbe_set = None
        s.e820 = [(0, 0x9F000, 1), (0x9F000, 0x1000, 2), (0x100000, 0x7F00000, 1), (0xFEC00000, 0x1000, 2)]
        s.e820_ix = 0; s.steps = 0; s.log = []
        s.ata = {}; s.ata_lba = 0; s.ata_left = 0; s.ata_cmds = 0; s.ata_err = False
        s.mem[0x7C00:0x7C00 + 512] = img[:512]
        s.out = []; s.segpfx = False
        s.lm = opt.get('lm', True); s.sse2 = opt.get('sse2', True)           # CPUID feature bits
        s.a20 = False; s.a20_methods = opt.get('a20', {'bios', 'fast', 'kbc'}); s.kbc_cmd = 0
        s.no_e820 = opt.get('no_e820', False); s.e801 = opt.get('e801', (0x3C00, 0x1F00)); s.ext88 = opt.get('ext88', None)
        s.disk_fail = opt.get('disk_fail', 0); s.edd = opt.get('edd', True); s.disk_err = opt.get('disk_err', 0x20)
        if 'e820' in opt: s.e820 = opt['e820']
    # ---- memory helpers
    def rd(s, a, n): return int.from_bytes(s.mem[a:a + n], 'little')
    def wr(s, a, n, v): s.mem[a:a + n] = (v & ((1 << (8 * n)) - 1)).to_bytes(n, 'little')
    def fetch(s, n):
        v = s.rd(s.ip, n); s.ip += n; return v
    def sfetch(s, n):
        v = s.fetch(n); return v - (1 << (8 * n)) if v >> (8 * n - 1) else v
    def reg(s, i, sz):
        if sz == 8: return (s.r[i & 3] >> (8 if i >= 4 else 0)) & 0xFF
        return s.r[i] & ((1 << sz) - 1)
    def setreg(s, i, sz, v):
        if sz == 8:
            j = i & 3
            if i >= 4: s.r[j] = (s.r[j] & ~0xFF00) | ((v & 0xFF) << 8)
            else: s.r[j] = (s.r[j] & ~0xFF) | (v & 0xFF)
        elif sz == 16: s.r[i] = (s.r[i] & ~0xFFFF) | (v & 0xFFFF)
        else: s.r[i] = v & 0xFFFFFFFF
    def lin(s, ea):
        if not s.segpfx: return ea
        a = s.seg[0] * 16 + ea
        return a if s.a20 else a & 0xFFFFF
    def modrm(s, asz):
        mod, reg, rm, ea = s._modrm(asz)
        if ea is not None: ea = s.lin(ea)
        return mod, reg, rm, ea
    def _modrm(s, asz):
        m = s.fetch(1); mod, reg, rm = m >> 6, (m >> 3) & 7, m & 7
        if mod == 3: return mod, reg, rm, None
        if asz == 16:
            if mod == 0 and rm == 6: return mod, reg, rm, s.fetch(2)
            base = {4: 6, 5: 7, 7: 3}[rm]
            d = s.sfetch(1) if mod == 1 else 0
            return mod, reg, rm, (s.r[base] + d) & 0xFFFF
        if mod == 0 and rm == 5: return mod, reg, rm, s.fetch(4)
        d = s.sfetch(1) if mod == 1 else 0
        return mod, reg, rm, (s.r[rm] + d) & 0xFFFFFFFF
    def flags(s, res, sz, cf=None):
        s.zf = int((res & ((1 << sz) - 1)) == 0)
        if cf is not None: s.cf = cf
    def alu(s, op, a, b, sz):
        m = (1 << sz) - 1
        if op == 0: r = a + b; s.flags(r, sz, int(r > m)); return r & m
        if op == 1: r = a | b; s.flags(r, sz, 0); return r
        if op == 4: r = a & b; s.flags(r, sz, 0); return r
        if op == 5: r = a - b; s.flags(r, sz, int(a < b)); return r & m
        if op == 6: r = a ^ b; s.flags(r, sz, 0); return r
        if op == 7: r = a - b; s.flags(r, sz, int(a < b)); return None
        raise Exception('alu op %d' % op)
    def int_(s, n):
        ax = s.r[0] & 0xFFFF; ah = ax >> 8
        if n == 0x10:
            if ah == 0x0E: s.out.append(chr(ax & 0xFF)); return
            if ax == 0x4F01:
                mode = s.r[1] & 0xFFFF; di = s.r[7] & 0xFFFF
                s.mem[di:di + 256] = bytes(256)
                if mode in s.vbe:
                    attr, bpp, w, h, pitch, fb = s.vbe[mode]
                    s.wr(di, 2, attr); s.wr(di + 0x10, 2, pitch); s.wr(di + 0x12, 2, w); s.wr(di + 0x14, 2, h)
                    s.mem[di + 0x19] = bpp; s.wr(di + 0x28, 4, fb)
                    s.r[0] = 0x4F
                else: s.r[0] = 0x014F
            elif ax == 0x4F02:
                mode = s.r[3] & 0x3FFF
                if mode in s.vbe and (s.r[3] & 0x4000): s.vbe_set = mode; s.r[0] = 0x4F
                else: s.r[0] = 0x014F
            return
        if n == 0x13:
            if ah == 0x41: s.r[3] = 0xAA55 if s.edd else 0; s.cf = 0 if s.edd else 1; return
            if ah == 0x00: s.cf = 0; return
            assert ah == 0x42
            if s.disk_fail > 0:
                s.disk_fail -= 1; s.cf = 1; s.r[0] = (s.disk_err << 8) | (s.r[0] & 0xFF); return
            si = s.r[6] & 0xFFFF; cnt = s.rd(si + 2, 2); off = s.rd(si + 4, 2); sg = s.rd(si + 6, 2); lba = s.rd(si + 8, 8)
            dst = sg * 16 + off
            s.mem[dst:dst + cnt * 512] = s.img[lba * 512:(lba + cnt) * 512].ljust(cnt * 512, b'\0')
            s.cf = 0; return
        if n == 0x15:
            if (s.r[0] & 0xFFFF) == 0x2401:
                if 'bios' in s.a20_methods: s.a20 = True
                s.cf = 0; s.r[0] &= 0xFFFF00FF; return
            if (s.r[0] & 0xFFFF) == 0xE801:
                if s.e801 is None: s.cf = 1; return
                s.r[1] = s.e801[0]; s.r[2] = s.e801[1]; s.r[0] = s.e801[0]; s.r[3] = s.e801[1]; s.cf = 0; return
            if ah == 0x88:
                if s.ext88 is None: s.cf = 1; return
                s.r[0] = s.ext88; s.cf = 0; return
            assert s.r[0] == 0xE820 and s.r[2] == 0x534D4150
            if s.no_e820: s.cf = 1; return
            di = s.r[7] & 0xFFFF
            b, l, t = s.e820[s.e820_ix]
            s.wr(di, 8, b); s.wr(di + 8, 8, l); s.wr(di + 16, 4, t)
            s.e820_ix += 1; s.r[0] = 0x534D4150; s.r[1] = 24
            s.r[3] = 0 if s.e820_ix == len(s.e820) else s.e820_ix
            s.cf = 0; return
        raise Exception('int %02x' % n)
    def step(s):
        s.steps += 1
        if s.steps > 60_000_000: raise Exception('step limit')
        start = s.ip
        op66 = False; s.segpfx = False
        while s.mem[s.ip] in (0x66, 0x26):
            if s.mem[s.ip] == 0x66: op66 = True
            else: s.segpfx = True
            s.ip += 1
        dflt = 16 if s.mode == 16 else 32
        osz = (32 if dflt == 16 else 16) if op66 else dflt
        asz = 16 if s.mode == 16 else 32
        op = s.fetch(1)
        if op == 0x0F: return s.step0f(osz, asz)
        if op == 0xFA or op == 0xFB or op == 0xFC: return
        if op == 0xF4: raise Halt('hlt at %x' % start)
        if 0xB0 <= op <= 0xB7: s.setreg(op - 0xB0, 8, s.fetch(1)); return
        if 0xB8 <= op <= 0xBF: s.setreg(op - 0xB8, osz, s.fetch(osz // 8)); return
        if op in (0x88, 0x89, 0x8A, 0x8B):
            sz = 8 if op in (0x88, 0x8A) else osz
            mod, reg, rm, ea = s.modrm(asz)
            if op in (0x88, 0x89):
                v = s.reg(reg, sz)
                if ea is None: s.setreg(rm, sz, v)
                else: s.wr(ea, sz // 8, v)
            else:
                s.setreg(reg, sz, s.reg(rm, sz) if ea is None else s.rd(ea, sz // 8))
            return
        if op == 0x8E:
            mod, reg, rm, ea = s.modrm(asz); s.seg[reg] = s.r[rm] & 0xFFFF; return
        if op in (0xA0, 0xA1, 0xA3, 0xA2):
            a = s.lin(s.fetch(asz // 8)); sz = 8 if op in (0xA0, 0xA2) else osz
            if op in (0xA0, 0xA1): s.setreg(0, sz, s.rd(a, sz // 8))
            else: s.wr(a, sz // 8, s.reg(0, sz))
            return
        if op in (0xC6, 0xC7):
            sz = 8 if op == 0xC6 else osz
            mod, reg, rm, ea = s.modrm(asz); s.wr(ea, sz // 8, s.fetch(sz // 8)); return
        if op == 0xE8:
            d = s.sfetch(2 if s.mode == 16 else 4); s.push(s.ip, 2); s.ip += d; return
        if op == 0xC3: s.ip = s.pop(2); return
        if op == 0xEA:
            off = s.fetch(osz // 8); sel = s.fetch(2)
            s.seg[1] = sel; s.ip = off
            if sel == 0x08: s.mode = 32
            elif sel == 0x18: s.mode = 64
            else: s.mode = 16
            s.log.append('far jmp %02x:%x mode=%d' % (sel, off, s.mode))
            return
        if op == 0xCD: s.int_(s.fetch(1)); return
        if 0x70 <= op <= 0x7F:
            d = s.sfetch(1); cc = op & 15
            t = {2: s.cf, 3: not s.cf, 4: s.zf, 5: not s.zf, 6: s.cf or s.zf, 7: not (s.cf or s.zf)}[cc]
            if t: s.ip += d
            return
        if op == 0xE9: d = s.sfetch(osz // 8); s.ip += d; return
        if op == 0xEB: d = s.sfetch(1); s.ip += d; return
        if op == 0xE3: d = s.sfetch(1); (s.ip.__add__) ; 
        if op == 0xE3:
            if (s.r[1] & 0xFFFF) == 0: s.ip += d
            return
        if op == 0xAC: s.setreg(0, 8, s.mem[s.r[6] & 0xFFFF]); s.r[6] = (s.r[6] + 1) & 0xFFFF; return
        if op == 0xAD: s.setreg(0, 16, s.rd(s.r[6] & 0xFFFF, 2)); s.r[6] = (s.r[6] + 2) & 0xFFFF; return
        if op in (0x84, 0x85):
            sz = 8 if op == 0x84 else osz
            mod, reg, rm, ea = s.modrm(asz); s.alu(4, s.reg(reg, sz), s.reg(rm, sz), sz); return
        if op == 0x03:
            mod, reg, rm, ea = s.modrm(asz); v = s.rd(ea, osz // 8) if ea is not None else s.reg(rm, osz)
            r = s.alu(0, s.reg(reg, osz), v, osz); s.setreg(reg, osz, r); return
        if op == 0xC0:
            mod, reg, rm, ea = s.modrm(asz); n = s.fetch(1); assert reg == 5 and ea is None
            s.setreg(rm, 8, s.reg(rm, 8) >> n); return
        if op in (0x31, 0x29, 0x01, 0x09, 0x21, 0x39):
            sz = osz; mod, reg, rm, ea = s.modrm(asz); o = {0x01: 0, 0x09: 1, 0x21: 4, 0x29: 5, 0x31: 6, 0x39: 7}[op]
            a = s.reg(rm, sz) if ea is None else s.rd(ea, sz // 8)
            r = s.alu(o, a, s.reg(reg, sz), sz)
            if r is not None:
                if ea is None: s.setreg(rm, sz, r)
                else: s.wr(ea, sz // 8, r)
            return
        if op in (0x83, 0x81, 0x80):
            sz = 8 if op == 0x80 else osz
            mod, reg, rm, ea = s.modrm(asz)
            imm = s.sfetch(1) if op == 0x83 else s.fetch(sz // 8)
            imm &= (1 << sz) - 1
            a = s.reg(rm, sz) if ea is None else s.rd(ea, sz // 8)
            r = s.alu(reg, a, imm, sz)
            if r is not None:
                if ea is None: s.setreg(rm, sz, r)
                else: s.wr(ea, sz // 8, r)
            return
        if op in (0x05, 0x0D, 0x25, 0x3D, 0x04, 0x0C, 0x24, 0x3C):
            sz = 8 if op in (0x04, 0x0C, 0x24, 0x3C) else osz
            o = {0x05: 0, 0x0D: 1, 0x25: 4, 0x3D: 7, 0x04: 0, 0x0C: 1, 0x24: 4, 0x3C: 7}[op]
            r = s.alu(o, s.reg(0, sz), s.fetch(sz // 8), sz)
            if r is not None: s.setreg(0, sz, r)
            return
        if op == 0xC1:
            mod, reg, rm, ea = s.modrm(asz); n = s.fetch(1); assert reg in (4, 5) and ea is None
            v = s.reg(rm, osz)
            s.setreg(rm, osz, (v << n) if reg == 4 else (v >> n)); return
        if 0x40 <= op <= 0x47:
            i = op - 0x40; r = (s.reg(i, osz) + 1); s.flags(r, osz); s.setreg(i, osz, r); return
        if 0x50 <= op <= 0x57: s.push(s.reg(op - 0x50, osz), osz // 8); return
        if 0x58 <= op <= 0x5F: s.setreg(op - 0x58, osz, s.pop(osz // 8)); return
        if op == 0xE4: p = s.fetch(1); s.setreg(0, 8, 0); return    # in al, imm8: port 0x92 / 0x64 read as 0
        if op == 0xEC:                                      # in al, dx  (ATA status)
            port = s.r[2] & 0xFFFF
            assert port == 0x1F7, 'in from port %x' % port
            s.setreg(0, 8, 0x58 if s.ata_left > 0 else 0x50); return
        if op == 0xEE:                                      # out dx, al  (ATA registers / command)
            port = s.r[2] & 0xFFFF; v = s.r[0] & 0xFF
            assert 0x1F2 <= port <= 0x1F7, 'out to port %x' % port
            if port == 0x1F7:
                assert v == 0x20, 'ATA command %x' % v
                assert s.ata.get(0x1F6, 0) & 0xE0 == 0xE0, 'LBA bit not set'
                cnt = s.ata.get(0x1F2, 0) or 256
                s.ata_lba = (s.ata.get(0x1F6, 0) & 0x0F) << 24 | s.ata.get(0x1F5, 0) << 16 | s.ata.get(0x1F4, 0) << 8 | s.ata.get(0x1F3, 0)
                s.ata_left = cnt; s.ata_cmds += 1
            else: s.ata[port] = v
            return
        if op == 0xE6:
            p = s.fetch(1); v = s.r[0] & 0xFF
            if p == 0x92 and (v & 2) and 'fast' in s.a20_methods: s.a20 = True
            if p == 0x64: s.kbc_cmd = v
            if p == 0x60 and s.kbc_cmd == 0xD1 and v == 0xDF and 'kbc' in s.a20_methods: s.a20 = True
            return
        if op == 0xF3:
            nx = s.fetch(1)
            if nx == 0x6D:                                  # rep insd from the ATA data port
                assert (s.r[2] & 0xFFFF) == 0x1F0 and s.r[1] == 128 and s.ata_left > 0, 'bad rep insd'
                d = s.r[7]; o = s.ata_lba * 512
                s.mem[d:d + 512] = s.img[o:o + 512].ljust(512, b'\0')
                s.r[7] = (d + 512) & 0xFFFFFFFF; s.r[1] = 0; s.ata_lba += 1; s.ata_left -= 1; return
            assert nx == 0xAB
            n = s.r[1]; d = s.r[7]
            for _ in range(n): s.wr(d, 4, s.r[0]); d += 4
            s.r[7] = d & 0xFFFFFFFF; s.r[1] = 0; return
        if op == 0xFF:
            mod, reg, rm, ea = s.modrm(asz); assert reg == 4 and ea is None
            s.ip = s.r[rm]; s.log.append('jmp reg -> %x mode=%d' % (s.ip, s.mode)); raise Halt('entered kernel at %x' % s.ip)
        raise Exception('unimplemented opcode %02x at %x' % (op, start))
    def step0f(s, osz, asz):
        op = s.fetch(1)
        if op == 0x01:
            mod, reg, rm, ea = s.modrm(asz); assert reg == 2
            s.gdtr = (s.rd(ea, 2), s.rd(ea + 2, 4)); return
        if op == 0x20 or op == 0x22:
            m = s.fetch(1); cr = (m >> 3) & 7; r = m & 7
            if op == 0x20: s.r[r] = s.cr[cr]
            else:
                s.cr[cr] = s.r[r]
            return
        if op in (0xB6, 0xB7):
            mod, reg, rm, ea = s.modrm(asz); n = 1 if op == 0xB6 else 2
            v = (s.reg(rm, 8 * n) if ea is None else s.rd(ea, n)); s.setreg(reg, osz, v); return
        if op == 0xA2:
            a = s.r[0]
            if a == 0x80000000: s.r[0] = 0x80000008 if s.lm else 0x0D
            elif a == 0x80000001: s.r[2] = (1 << 29) | (1 << 11) if s.lm else 0
            elif a == 1: s.r[2] = (1 << 26 | 1 << 25 | 1) if s.sse2 else 1
            else: raise Exception('cpuid %x' % a)
            return
        if op == 0x32: assert s.r[1] == 0xC0000080; s.r[0] = s.efer & 0xFFFFFFFF; s.r[2] = 0; return
        if op == 0x30: s.efer = s.r[0]; return
        raise Exception('unimplemented 0f %02x' % op)
    def push(s, v, n): s.r[4] = (s.r[4] - n) & (0xFFFF if s.mode == 16 else 0xFFFFFFFF); s.wr(s.r[4], n, v)
    def pop(s, n): v = s.rd(s.r[4], n); s.r[4] = (s.r[4] + n) & (0xFFFF if s.mode == 16 else 0xFFFFFFFF); return v

def run(img_path, vbe, label, expect=None, **opt):
    """run the boot stage; expect=None: it must reach the kernel.  expect=(text, mode): it must halt in `mode` bits showing `text`
    (BIOS teletype output, or the VGA text buffer for 32-bit failures) and never enter the kernel."""
    img = open(img_path, 'rb').read() if isinstance(img_path, str) else img_path
    c = CPU(img, vbe, opt)
    c.r[2] = 0x80; c.r[4] = 0x7C00           # DL = boot drive 0x80
    try:
        while True: c.step()
    except Halt as h: msg = str(h)
    if expect is not None:
        text, bits = expect
        shown = ''.join(c.out) + bytes(c.mem[0xB8000:0xB8000 + 16:2]).decode('latin1')
        good = msg.startswith('hlt at') and c.mode == bits and (c.cr[0] & 1) == (1 if bits == 32 else 0) and text in shown
        print(('  ok   ' if good else '  FAIL ') + '%s -> halts with "%s", never enters the kernel' % (label, text))
        if not good: FAILS.append(label); print('       got:', msg, repr(shown[-80:]))
        return c
    m = c.mem; ok = True
    def check(name, cond):
        nonlocal ok
        print(('  ok   ' if cond else '  FAIL ') + name); ok &= bool(cond)
        if not cond: FAILS.append(name)
    print('== %s: %s (%d steps)' % (label, msg, c.steps))
    ksec = struct.unpack_from('<I', img, KSEC_OFF)[0]
    check('stopped by the jump into the kernel in 64-bit mode', msg == 'entered kernel at %x' % KBASE and c.mode == 64)
    check('boot info magic PEAC', c.rd(0x500, 4) == 0x43414550)
    check('boot drive stored', c.rd(0x508, 4) == 0x80)
    check('kernel sector count stored (%d)' % ksec, c.rd(0x50C, 4) == ksec and ksec > 0)
    check('E820 entries: %d' % c.rd(0x504, 4), c.rd(0x504, 4) == (len(c.e820) if not c.no_e820 else c.rd(0x504, 4)))
    check('kernel image loaded at 0x200000 byte for byte (ATA PIO, %d commands)' % c.ata_cmds, bytes(m[KBASE:KBASE + ksec * 512]) == img[2560:2560 + ksec * 512])
    check('CR3 = PML4 at 0x1000, CR4 has PAE|OSFXSR|OSXMMEXCPT', c.cr[3] == 0x1000 and (c.cr[4] & 0x620) == 0x620)
    check('EFER.LME set, CR0 has PE|PG|MP|NE and EM clear', (c.efer & 0x100) and (c.cr[0] & 0x80000023) == 0x80000023 and not (c.cr[0] & 4))
    check('chunked load: %d commands of <=128 sectors' % c.ata_cmds, c.ata_cmds == (ksec + 127) // 128)
    check('PML4[0] -> PDPT, PDPT[0..3] -> PDs', c.rd(0x1000, 4) == 0x2003 and all(c.rd(0x2000 + 8 * i, 4) == (0x3000 + 0x1000 * i) | 3 for i in range(4)))
    pd_ok = all(c.rd(0x3000 + 8 * i, 4) == ((i * 0x200000) | 0x83 | (0x18 if i >= 1536 else 0)) for i in range(2048))
    check('2048 PD entries identity-map 4 GiB (>=3 GiB uncached)', pd_ok)
    check('GDT loaded with 4 entries', c.gdtr is not None and c.gdtr[0] == 31)
    return c

if __name__ == '__main__':
    img = sys.argv[1]
    A = 0x9B  # supported | graphics | LFB ...
    fb = 0xFD000000
    good = {0x141: (0x99 | 0x82, 32, 800, 600, 3200, fb)}
    c = run(img, good, 'mode 0x141 (800x600x32) available')
    vi = 0x700
    print('  VBE mode', hex(c.rd(0x6F0, 4)), 'w', c.rd(vi + 0x12, 2), 'h', c.rd(vi + 0x14, 2), 'bpp', c.mem[vi + 0x19], 'pitch', c.rd(vi + 0x10, 2), 'fb', hex(c.rd(vi + 0x28, 4)))
    assert c.rd(0x6F0, 4) == 0x141 and c.rd(vi + 0x28, 4) == fb
    c = run(img, {0x141: (0x01, 32, 800, 600, 3200, fb), 0x115: (0x99 | 0x82, 24, 800, 600, 2400, fb)}, '0x141 lacks LFB -> falls back to 0x115 (24 bpp)')
    assert c.rd(0x6F0, 4) == 0x115 and c.mem[vi + 0x19] == 24
    print('  VBE mode', hex(c.rd(0x6F0, 4)))
    # a maximum-size (64 MiB) kernel: patch a synthetic image and make sure all of it arrives intact above 2 MiB
    # a large kernel: patch a synthetic image (with the checksum a real mkimage would store) and make sure all of it arrives intact above 2 MiB
    big = bytearray(open(img, 'rb').read()[:2560]); n = (12 << 20) // 512
    body = bytes((i * 131 + 7) & 0xFF for i in range(512)) * n
    big[KSEC_OFF:KSEC_OFF + 4] = struct.pack('<I', n)
    big[KCSUM_OFF:KCSUM_OFF + 4] = struct.pack('<I', csum(body))
    big += body
    c = run(bytes(big), good, '12 MiB kernel (%d sectors, synthetic)' % n)
    wide = (0x99 | 0x82, 32, 1280, 800, 5120, fb)
    c = run(img, {0x141: (0x99 | 0x82, 32, 800, 600, 3200, fb), 0x144: (0x99 | 0x82, 32, 1024, 768, 4096, fb), 0x14A: wide}, 'high resolution: 1280x800 preferred over 1024x768 and 800x600')
    assert c.rd(0x6F0, 4) == 0x14A and c.rd(0x700 + 0x12, 2) == 1280
    c = run(img, {0x14A: (0x99 | 0x82, 32, 1920, 1080, 7680, fb), 0x144: (0x99 | 0x82, 32, 1024, 768, 4096, fb)}, 'full-HD mode (1920x1080) now accepted and preferred')
    assert c.rd(0x6F0, 4) == 0x14A and c.rd(0x700 + 0x12, 2) == 1920
    c = run(img, {0x14A: (0x99 | 0x82, 32, 2560, 1440, 10240, fb), 0x144: (0x99 | 0x82, 32, 1024, 768, 4096, fb)}, 'too-wide mode (2560x1440) skipped at boot -> 1024x768')
    assert c.rd(0x6F0, 4) == 0x144 and c.rd(0x700 + 0x12, 2) == 1024
    c = run(img, {0x144: (0x99 | 0x82, 16, 1024, 768, 2048, fb), 0x143: (0x99 | 0x82, 32, 800, 600, 3200, fb)}, 'only 16 bpp at 1024x768 -> second pass takes 800x600x32')
    assert c.rd(0x6F0, 4) == 0x143
    c = run(img, {0x141: (0x99 | 0x82, 32, 640, 400, 2560, fb), 0x143: (0x99 | 0x82, 32, 800, 600, 3200, fb)}, 'QEMU-style: 0x141 is 640x400 -> must be skipped')
    assert c.rd(0x6F0, 4) == 0x143 and c.rd(0x700 + 0x12, 2) == 800
    run(img, {0x141: (0x99 | 0x82, 32, 640, 400, 2560, fb)}, 'only 640x400 offered', expect=('no VBE', 16))
    run(img, {}, 'no VBE mode at all', expect=('no VBE', 16))
    print('-- hardening scenarios')
    c = run(img, good, 'A20 off at power-on, BIOS INT 15h enables it', a20={'bios'}); check_a20(c)
    c = run(img, good, 'A20: BIOS cannot, fast gate (port 0x92) works', a20={'fast'}); check_a20(c)
    c = run(img, good, 'A20: only the keyboard controller works', a20={'kbc'}); check_a20(c)
    run(img, good, 'A20 impossible', expect=('A20', 16), a20=set())
    run(img, good, 'CPU without long mode', expect=('64-bit', 16), lm=False)
    run(img, good, 'CPU without SSE2', expect=('SSE2', 16), sse2=False)
    c = run(img, good, 'no E820: map built from E801 (1 MiB + 16 MiB regions)', no_e820=True, e801=(0x3C00, 0x1F00), e820=[])
    assert c.rd(0x504, 4) == 2 and c.rd(0x510 + 8, 4) == 0x3C00 * 1024 and c.rd(0x510 + 24, 4) == 0x1000000 and c.rd(0x510 + 32, 4) == 0x1F00 * 65536
    c = run(img, good, 'no E820, no E801: INT 15h AH=88h', no_e820=True, e801=None, ext88=0x7000, e820=[])
    assert c.rd(0x504, 4) == 1 and c.rd(0x510 + 8, 4) == 0x7000 * 1024
    c = run(img, good, 'no memory services at all: assume 15 MiB', no_e820=True, e801=None, e820=[])
    assert c.rd(0x504, 4) == 1 and c.rd(0x510 + 8, 4) == 0x3C00 * 1024
    c = run(img, good, 'disk read fails twice, third try works (retry + controller reset)', disk_fail=2)
    run(img, good, 'disk read keeps failing: stage 1 prints the BIOS error code', expect=('disk error 20', 16), disk_fail=99)
    run(img, good, 'BIOS without INT 13h extensions', expect=('LBA', 16), edd=False)
    bad = bytearray(open(img, 'rb').read()); bad[2548:2552] = b'\0\0\0\0'
    run(bytes(bad), good, 'stage 2 signature missing', expect=('bad boot stage 2', 16))
    bad = bytearray(open(img, 'rb').read()); bad[2560 + 100000] ^= 0x40
    run(bytes(bad), good, 'one flipped bit in the kernel image', expect=('CRC!', 32))
    print('\nbootsim:', 'ALL CHECKS PASSED' if not FAILS else 'FAILED: %s' % FAILS)
    sys.exit(1 if FAILS else 0)
