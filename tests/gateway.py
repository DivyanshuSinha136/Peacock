#!/usr/bin/env python3
"""Fake QEMU user-mode gateway for the Peacock host tests.

Frames travel over two FIFOs (2-byte big-endian length + Ethernet frame):
  to_guest.fifo   gateway -> guest      from_guest.fifo   guest -> gateway
It answers ARP, DHCP, DNS (A records), ICMP echo and plays a few HTTP/1.0 servers on port 80 of any address.
"""
import os, struct, sys, time, select

GW_MAC = bytes.fromhex("525500000202")
GW_IP = bytes([10, 0, 2, 2]); DNS_IP = bytes([10, 0, 2, 3]); GUEST_IP = bytes([10, 0, 2, 15])
NAMES = {"example.test": bytes([93, 184, 216, 34]), "other.test": bytes([203, 0, 113, 7])}
MSS = 1000
log = open("gateway.log", "w")
def say(*a):
    print(*a, file=log); log.flush()

def csum(b):
    if len(b) & 1: b += b"\0"
    s = sum(struct.unpack("!%dH" % (len(b) // 2), b))
    while s >> 16: s = (s & 0xFFFF) + (s >> 16)
    return (~s) & 0xFFFF

def eth(dst, src, typ, payload): return dst + src + struct.pack("!H", typ) + payload
def ipv4(src, dst, proto, payload, ident=1):
    h = struct.pack("!BBHHHBBH4s4s", 0x45, 0, 20 + len(payload), ident, 0, 64, proto, 0, src, dst)
    h = h[:10] + struct.pack("!H", csum(h)) + h[12:]
    return h + payload
def udp(src, dst, sp, dp, data):
    u = struct.pack("!HHHH", sp, dp, 8 + len(data), 0) + data
    ph = src + dst + struct.pack("!BBH", 0, 17, len(u))
    c = csum(ph + u) or 0xFFFF
    return u[:6] + struct.pack("!H", c) + u[8:]
def tcp(src, dst, sp, dp, seq, ack, flags, data=b""):
    t = struct.pack("!HHIIBBHHH", sp, dp, seq & 0xFFFFFFFF, ack & 0xFFFFFFFF, 5 << 4, flags, 8192, 0, 0) + data
    ph = src + dst + struct.pack("!BBH", 0, 6, len(t))
    return t[:16] + struct.pack("!H", csum(ph + t)) + t[18:]

PAGES = {}
def page(host, path):
    if path == "/":
        return 200, "text/html", (b"<html><head><title>Example Test</title></head><body><h1>Hello from the fake web</h1>"
            b"<p>This page is served by <b>gateway.py</b> &amp; rendered by <i>Peacock</i>.</p>"
            b"<ul><li><a href=\"/about\">About page</a></li><li><a href=\"/big\">A big page</a></li><li><a href=\"http://other.test/\">Other host</a></li><li><a href=\"/redir\">A redirect</a></li></ul>"
            b"<h2>Table</h2><table border=1><tr><td>one</td><td>two</td></tr><tr><td>three</td><td>four</td></tr></table>"
            b"<blockquote>Quoted &mdash; text</blockquote><pre>code  block\n  indented</pre></body></html>"), {}
    if path == "/about": return 200, "text/html", b"<html><head><title>About</title></head><body><h1>About</h1><p>The about page.</p><a href=\"/\">Back</a></body></html>", {}
    if path == "/redir": return 302, "text/html", b"moved", {"Location": "/about"}
    if path == "/big":
        body = b"<html><head><title>Big</title></head><body><h1>Big page</h1>" + b"".join(
            b"<p>Paragraph %d: the quick brown fox jumps over the lazy dog, again and again.</p>" % i for i in range(60)) + b"<p>END-OF-BIG</p></body></html>"
        return 200, "text/html", body, {}
    if path == "/chunked":
        body = b"<h1>Chunked</h1><p>first chunk, second chunk</p>"
        return 200, "text/html", body, {"__chunked": "1"}
    if path == "/styled":
        return 200, "text/html", (b"<html><head><title>Styled</title></head><body bgcolor='#fff8e0'><h1 style='color:#c00000'>Red heading</h1>"
            b"<p>Plain <font color='blue'>blue words</font> and <s>struck</s> and <mark>marked</mark> text.</p>"
            b"<div style='text-align:center'>centered line</div><p><a href='#bottom'>jump down</a></p>"
            + b"".join(b"<p>filler %d lorem ipsum dolor sit amet</p>" % i for i in range(40)) +
            b"<h2 id='bottom'>Bottom anchor</h2><p>needle in the haystack, needle again</p></body></html>"), {}
    if path == "/file.bin": return 200, "application/octet-stream", bytes(range(256)) * 4, {"Content-Disposition": "attachment; filename=\"blob.bin\""}
    if path == "/gz": return 200, "text/html", b"\x1f\x8b\x08garbage", {"Content-Encoding": "gzip"}
    if path == "/text": return 200, "text/plain", b"plain text line 1\nline 2\n", {}
    if host == "other.test": return 200, "text/html", b"<html><head><title>Other</title></head><body><h1>Other host</h1></body></html>", {}
    return 404, "text/html", b"<html><body><h1>404</h1><p>No such page.</p></body></html>", {}

class Conn:
    def __init__(s, key, iss): s.key = key; s.snd = iss; s.rcv = 0; s.segs = []; s.base = iss; s.dropped = False; s.dst_seq0 = iss
conns = {}

def main():
    fo = os.open("to_guest.fifo", os.O_WRONLY)
    fi = os.open("from_guest.fifo", os.O_RDONLY)
    buf = b""
    def send(frame): os.write(fo, struct.pack("!H", len(frame)) + frame)
    def tosend(ip): return eth(guest_mac[0], GW_MAC, 0x0800, ip)
    guest_mac = [b"\x52\x54\x00\x12\x34\x56"]
    while True:
        r, _, _ = select.select([fi], [], [], 5)
        if not r: say("idle timeout"); return
        d = os.read(fi, 8192)
        if not d: say("guest closed"); return
        buf += d
        while len(buf) >= 2 and len(buf) >= 2 + struct.unpack("!H", buf[:2])[0]:
            n = struct.unpack("!H", buf[:2])[0]; f = buf[2:2 + n]; buf = buf[2 + n:]
            handle(f, send, tosend, guest_mac)

def handle(f, send, tosend, guest_mac):
    if len(f) < 14: return
    src = f[6:12]; et = struct.unpack("!H", f[12:14])[0]; p = f[14:]
    if et == 0x0806:
        op = struct.unpack("!H", p[6:8])[0]; tip = p[24:28]
        say("ARP op", op, "who-has", tip.hex())
        if op == 1 and tip in (GW_IP, DNS_IP):
            guest_mac[0] = src
            send(eth(src, GW_MAC, 0x0806, struct.pack("!HHBBH", 1, 0x0800, 6, 4, 2) + GW_MAC + tip + p[8:14] + p[14:18]))
        return
    if et != 0x0800: return
    ihl = (p[0] & 15) * 4; proto = p[9]; sip = p[12:16]; dip = p[16:20]; q = p[ihl:]
    guest_mac[0] = src
    if proto == 1 and q[0] == 8:
        say("ping to", ".".join(map(str, dip)))
        rep = b"\0" + q[1:2] + b"\0\0" + q[4:]
        rep = rep[:2] + struct.pack("!H", csum(rep)) + rep[4:]
        send(tosend(ipv4(dip, sip, 1, rep)))
    elif proto == 17:
        sp, dp = struct.unpack("!HH", q[:4]); data = q[8:]
        if dp == 67:
            xid = data[4:8]; chaddr = data[28:34]
            mt = None; o = 240
            while o < len(data) and data[o] != 255:
                if data[o] == 0: o += 1; continue
                if data[o] == 53: mt = data[o + 2]
                o += 2 + data[o + 1]
            say("DHCP type", mt)
            rt = 2 if mt == 1 else 5
            opts = bytes([53, 1, rt, 54, 4]) + GW_IP + bytes([1, 4, 255, 255, 255, 0, 3, 4]) + GW_IP + bytes([6, 4]) + DNS_IP + bytes([51, 4, 0, 1, 0, 0, 255])
            rep = bytes([2, 1, 6, 0]) + xid + bytes(8) + GUEST_IP + GW_IP + bytes(4) + chaddr + bytes(10) + bytes(192) + bytes([99, 130, 83, 99]) + opts
            send(eth(b"\xff" * 6, GW_MAC, 0x0800, ipv4(GW_IP, b"\xff\xff\xff\xff", 17, udp(GW_IP, b"\xff\xff\xff\xff", 67, 68, rep))))
        elif dp == 53:
            tid = data[:2]; i = 12; labels = []
            while data[i]: labels.append(data[i + 1:i + 1 + data[i]].decode()); i += 1 + data[i]
            qname = ".".join(labels); qend = i + 5
            say("DNS", qname)
            ans = NAMES.get(qname)
            if ans:
                rep = tid + b"\x81\x80\x00\x01\x00\x01\x00\x00\x00\x00" + data[12:qend] + b"\xc0\x0c\x00\x01\x00\x01\x00\x00\x00\x3c\x00\x04" + ans
            else:
                rep = tid + b"\x81\x83\x00\x01\x00\x00\x00\x00\x00\x00" + data[12:qend]
            send(tosend(ipv4(dip, sip, 17, udp(dip, sip, 53, sp, rep))))
    elif proto == 6:
        sp, dp, seq, ack = struct.unpack("!HHII", q[:12]); hl = (q[12] >> 4) * 4; fl = q[13]; data = q[hl:]
        key = (sip, sp, dip, dp)
        if fl & 2:
            c = Conn(key, 5000); c.rcv = seq + 1; conns[key] = c
            say("SYN to", ".".join(map(str, dip)), dp)
            send(tosend(ipv4(dip, sip, 6, tcp(dip, sip, dp, sp, c.snd, c.rcv, 0x12)))); c.snd += 1; c.base = c.snd
            return
        c = conns.get(key)
        if not c: return
        if data and not c.segs:
            c.rcv = seq + len(data)
            req = data.split(b"\r\n")
            line = req[0].decode(); host = ""
            for h in req[1:]:
                if h.lower().startswith(b"host:"): host = h[5:].strip().decode()
            path = line.split(" ")[1]
            say("HTTP", line, "host", host)
            code, ctype, body, extra = page(host.split(":")[0], path)
            hd = "HTTP/1.0 %d X\r\nContent-Type: %s\r\nServer: fake\r\n" % (code, ctype)
            for k, v in extra.items():
                if not k.startswith("__"): hd += "%s: %s\r\n" % (k, v)
            if extra.get("__chunked"):
                hd += "Transfer-Encoding: chunked\r\nConnection: close\r\n\r\n"
                half = len(body) // 2
                out = hd.encode() + b"%x\r\n" % half + body[:half] + b"\r\n" + b"%x\r\n" % (len(body) - half) + body[half:] + b"\r\n0\r\n\r\n"
            else:
                hd += "Content-Length: %d\r\nConnection: close\r\n\r\n" % len(body)
                out = hd.encode() + body
            c.segs = [out[i:i + MSS] for i in range(0, len(out), MSS)]
            c.out_len = len(out)
            send(tosend(ipv4(dip, sip, 6, tcp(dip, sip, dp, sp, c.snd, c.rcv, 0x10))))
            for i, s in enumerate(c.segs):
                if path == "/big" and i == 2 and not c.dropped: c.dropped = True; say("dropping segment 2"); continue
                send(tosend(ipv4(dip, sip, 6, tcp(dip, sip, dp, sp, c.base + i * MSS, c.rcv, 0x18, s))))
            end = c.base + c.out_len
            send(tosend(ipv4(dip, sip, 6, tcp(dip, sip, dp, sp, end, c.rcv, 0x11))))
        elif c.segs and (fl & 0x10):
            end = c.base + c.out_len
            if ack < end and (ack - c.base) % MSS == 0 and ack >= c.base:            # go-back-N on a duplicate ack
                i = (ack - c.base) // MSS
                say("retransmit from segment", i)
                for j in range(i, len(c.segs)):
                    send(tosend(ipv4(dip, sip, 6, tcp(dip, sip, dp, sp, c.base + j * MSS, c.rcv, 0x18, c.segs[j]))))
                send(tosend(ipv4(dip, sip, 6, tcp(dip, sip, dp, sp, end, c.rcv, 0x11))))
        if fl & 1: pass

main()
