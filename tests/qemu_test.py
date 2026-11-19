#!/usr/bin/env python3
"""qemu_test.py -- boot peacock.img headless in QEMU and check it:  python3 tests/qemu_test.py peacock.img
  1. the kernel log on COM1 must reach '[peacock] desktop ready' (and show the VBE mode it was given)
  2. a screendump taken through the QEMU monitor must be a real picture (several distinct colours, mostly not black)
  3. keys typed through the monitor ('help' + Enter into the Terminal window that opens at boot) must change the screen
Needs qemu-system-x86_64 on PATH.  Exit status 0 = all checks passed."""
import os, subprocess, sys, tempfile, time

def ppm_stats(path):
    with open(path, 'rb') as f: data = f.read()
    parts = data.split(b'\n', 3)
    w, h = map(int, parts[1].split()); px = parts[3]
    colours = set(px[i:i + 3] for i in range(0, len(px) - 2, 3 * 97))
    black = sum(1 for i in range(0, len(px) - 2, 3 * 97) if px[i:i + 3] == b'\x00\x00\x00')
    return w, h, len(colours), black / max(1, len(px) // (3 * 97)), px

def main():
    img = sys.argv[1] if len(sys.argv) > 1 else 'peacock.img'
    qemu = os.environ.get('QEMU', 'qemu-system-x86_64')
    tmp = tempfile.mkdtemp(prefix='peacock-test-')
    log = os.path.join(tmp, 'serial.log')
    p = subprocess.Popen([qemu, '-drive', 'format=raw,file=' + img, '-m', '128', '-vga', 'std', '-display', 'none',
                          '-serial', 'file:' + log, '-monitor', 'stdio', '-no-reboot'],
                         stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    fails = []
    def mon(cmd, wait=0.3):
        p.stdin.write(cmd + '\n'); p.stdin.flush(); time.sleep(wait)
    def check(name, ok):
        print(('ok   ' if ok else 'FAIL ') + name)
        if not ok: fails.append(name)
    try:
        ready = False
        for _ in range(100):
            time.sleep(0.2)
            if os.path.exists(log) and '[peacock] desktop ready' in open(log, errors='replace').read(): ready = True; break
        text = open(log, errors='replace').read() if os.path.exists(log) else ''
        check('kernel log reaches "desktop ready"', ready)
        check('boot stage handed over a VBE framebuffer', 'VBE mode' in text)
        print(text)
        time.sleep(1.5)
        a = os.path.join(tmp, 'a.ppm'); mon('screendump ' + a, 1.0)
        ok = os.path.exists(a)
        check('screendump written', ok)
        if ok:
            w, h, ncol, blackfrac, pxa = ppm_stats(a)
            check('screen is %dx%d with %d distinct sampled colours' % (w, h, ncol), ncol >= 20 and blackfrac < 0.6)
            for k in 'help':
                mon('sendkey ' + k, 0.15)
            mon('sendkey ret', 0.6)
            b = os.path.join(tmp, 'b.ppm'); mon('screendump ' + b, 1.0)
            if os.path.exists(b):
                pxb = ppm_stats(b)[4]
                check('typing into the Terminal changed the screen', pxa != pxb)
            else: check('second screendump', False)
        print('screenshots kept in', tmp)
    finally:
        try: mon('quit', 0.2)
        except Exception: pass
        p.kill()
    sys.exit(1 if fails else 0)

if __name__ == '__main__': main()
