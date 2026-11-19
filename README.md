<div align="center">

<img src="docs/img/banner.svg" alt="Peacock OS" width="100%">

<br>

<img src="docs/img/badges/version.svg" alt="version 1.9"> <img src="docs/img/badges/arch.svg" alt="x86-64 BIOS"> <img src="docs/img/badges/lang.svg" alt="written in KingCobra"> <img src="docs/img/badges/license.svg" alt="MIT"> <img src="docs/img/badges/tests.svg" alt="host suites passing"> <img src="docs/img/badges/qemu.svg" alt="tested on QEMU only">

**A complete bootable desktop operating system - bootloader, kernel, drivers, network stack, file system, window manager and applications - written in one language: [KingCobra](../README.md).**

[Quick start](#quick-start) - [Features](#features) - [Architecture](#architecture) - [Terminal](#terminal-reference) - [Build and test](#build-and-test) - [Tested on](#tested-on) - [Limits](#honest-limits) - [Changelog](CHANGELOG.md)

<img src="docs/img/screenshots/desktop.png" alt="Peacock OS desktop" width="92%">

</div>

---

## Quick start

You need `qemu-system-x86_64` and the KingCobra toolchain (`../kingcobra`, `../kcc`).

```sh
make                 # builds peacock.img (17 MiB, bootable raw disk image)
make run             # boots it in QEMU
```

Or boot a prebuilt image directly:

```sh
qemu-system-x86_64 -m 128 -vga std \
  -nic user,model=rtl8139 \
  -usb -device usb-tablet -device usb-kbd \
  -drive file=peacock-1.9.img,format=raw
```

| Option | Why |
|---|---|
| `-m 128` | the kernel heap is 120 MiB (use `-m 256` for 2560x1440 and above - the 64-bit back buffer needs 8 bytes/pixel) |
| `-vga std` | Bochs/DISPI adapter: live resolution switching up to 4096x2400 |
| `-nic user,model=rtl8139` | the supported NIC; gives DHCP, DNS and TCP through QEMU's user network |
| `-usb -device usb-tablet -device usb-kbd` | UHCI controller with an absolute pointer and a keyboard |

Booting on bare metal (`dd if=peacock-1.9.img of=/dev/sdX`) is untested - see [Tested on](#tested-on).

## Features

<table>
<tr>
<td width="64"><img src="docs/img/icons/boot.svg" width="56" alt=""></td>
<td><b>Boots from nothing</b><br>Stage 1/2 bootloader written in KingCobra (<code>boot/x86.kc</code> is a tiny assembler; <code>make boot-selftest</code> proves it byte-identical to the NASM build). Hardened BIOS path: multiple A20 methods, E820/E801/88h memory-map fallbacks, checksummed handover block.</td>
</tr>
<tr>
<td><img src="docs/img/icons/render.svg" width="56" alt=""></td>
<td><b>64-bit rendering pipeline</b><br>RGBA16 back buffer (16 bits per channel), blending and glass blur in 16-bit, ordered-dither flush to the 24/32 bpp screen. Live resolution switching, 120 MiB heap.</td>
</tr>
<tr>
<td><img src="docs/img/icons/ui.svg" width="56" alt=""></td>
<td><b>Glass desktop</b><br>Seelen-style dock and top bar mixed with the Peacock look: translucent glass panels, damage-rectangle redraw, 9 themes, SVG icons, scalable fonts, an uncluttered desktop (Files, Browser, Terminal, Notes, Settings).</td>
</tr>
<tr>
<td><img src="docs/img/icons/apps.svg" width="56" alt=""></td>
<td><b>Applications</b><br>Terminal, Notes 2 editor, Paint, Calculator, System Info, Files, Calendar, Clock, Snake, Minesweeper, System Monitor, Web Browser, App Builder 2, 3D Studio, Settings - 14 in the launcher.</td>
</tr>
<tr>
<td><img src="docs/img/icons/fs.svg" width="56" alt=""></td>
<td><b>KCFS 2 file system</b><br>Crash-safe two-slot store with CRC32 on every block, atomic two-slot commit, <code>fsck</code>, attributes, background autosave thread.</td>
</tr>
<tr>
<td><img src="docs/img/icons/threads.svg" width="56" alt=""></td>
<td><b>Kernel threads</b><br>Cooperative scheduler with mutexes, semaphores and queues; <code>ps</code>, <code>kill</code>, <code>spawn</code> from the terminal.</td>
</tr>
<tr>
<td><img src="docs/img/icons/net.svg" width="56" alt=""></td>
<td><b>Network and browser</b><br>RTL8139 driver, ARP, IPv4, ICMP, UDP, DHCP, DNS, TCP and HTTP. Browser with tabs, bookmarks, find-in-page and an HTML renderer. <code>wget</code>, <code>ping</code>, <code>nslookup</code> in the terminal.</td>
</tr>
<tr>
<td><img src="docs/img/icons/usb.svg" width="56" alt=""></td>
<td><b>USB (UHCI)</b><br>Polled driver: HID boot keyboard and mouse, absolute tablet, bulk-only mass storage (read-only), hot-plug scan. No hubs yet.</td>
</tr>
<tr>
<td><img src="docs/img/icons/pci.svg" width="56" alt=""></td>
<td><b>PCI, ACPI and hardware control</b><br>Config-space enumeration through bridges, BAR sizing, capability walking (PM, MSI, MSI-X, PCIe), device naming and driver binding. ACPI table parser, S5 power-off, reset register, CPUID report, memory map.</td>
</tr>
<tr>
<td><img src="docs/img/icons/3d.svg" width="56" alt=""></td>
<td><b>3D and executables</b><br>Software 3D rasteriser with 3D Studio; App Builder 2 compiles designs into <code>.pea</code> executables - a native binary format with a loader, <code>peadump</code> and a command-line compiler <code>peac</code>.</td>
</tr>
<tr>
<td><img src="docs/img/icons/tests.svg" width="56" alt=""></td>
<td><b>Tested without hardware</b><br>17 host-side suites run the real kernel code against simulated disks, PCI buses, UHCI controllers and NICs, plus a boot simulator.</td>
</tr>
</table>

## Screenshots

<table>
<tr>
<td width="50%"><img src="docs/img/screenshots/settings-devices.png" alt="Settings - Devices"><br><sub><b>Settings - Devices:</b> PCI functions, bound drivers, ACPI, CPU</sub></td>
<td width="50%"><img src="docs/img/screenshots/settings-usb.png" alt="Settings - USB"><br><sub><b>Settings - USB:</b> controller, ports and attached devices</sub></td>
</tr>
<tr>
<td><img src="docs/img/screenshots/settings-network.png" alt="Settings - Network"><br><sub><b>Settings - Network:</b> NIC, DHCP lease, DNS</sub></td>
<td><img src="docs/img/screenshots/settings-appearance.png" alt="Settings - Appearance"><br><sub><b>Settings - Appearance:</b> themes, depth, fonts</sub></td>
</tr>
</table>

<sub>Screenshots are produced by the host UI test harness (`make host-test-ui`, `host-test-usb`) rendering the real compositor, not by a QEMU capture.</sub>

## Gallery

<table>
<tr>
<td width="50%"><img src="docs/img/screenshots/terminal-glass.png" alt="Terminal on glass"><br><sub><b>Terminal</b> over a glass backdrop, with <code>neofetch</code>-style info and live theme toast</sub></td>
<td width="50%"><img src="docs/img/screenshots/browser.png" alt="Web browser"><br><sub><b>Browser</b> - tabs, bookmarks, find-in-page, HTML renderer</sub></td>
</tr>
<tr>
<td><img src="docs/img/screenshots/3d-studio.png" alt="3D Studio"><br><sub><b>3D Studio</b> - software rasteriser, solid/wire styles</sub></td>
<td><img src="docs/img/screenshots/app-builder.png" alt="App Builder"><br><sub><b>App Builder 2</b> - design a window, run it, save as <code>.pea</code></sub></td>
</tr>
<tr>
<td><img src="docs/img/screenshots/files.png" alt="Files"><br><sub><b>Files</b> - KCFS 2 file manager</sub></td>
<td><img src="docs/img/screenshots/launcher.png" alt="Launcher"><br><sub><b>Launcher</b> - searchable app menu from the dock</sub></td>
</tr>
<tr>
<td><img src="docs/img/screenshots/themes.png" alt="Themes"><br><sub><b>Themes</b> - nine wallpapers, button depth, resolution</sub></td>
<td><img src="docs/img/screenshots/theme-om.png" alt="1920x1080 with a dark theme"><br><sub><b>1920x1080</b> with the Om Glow theme</sub></td>
</tr>
<tr>
<td><img src="docs/img/screenshots/notes.png" alt="Notes"><br><sub><b>Notes 2</b> - find/replace, selection, undo</sub></td>
<td><img src="docs/img/screenshots/system-monitor.png" alt="System monitor"><br><sub><b>System Monitor</b> - kernel threads and heap</sub></td>
</tr>
<tr>
<td><img src="docs/img/screenshots/calendar-clock.png" alt="Calendar and Clock"><br><sub><b>Calendar and Clock</b> over the lotus-mandala theme</sub></td>
<td><img src="docs/img/screenshots/fonts.png" alt="Fonts"><br><sub><b>Fonts</b> - Inter, Poppins, DejaVu, Liberation, bitmap</sub></td>
</tr>
<tr>
<td><img src="docs/img/screenshots/snake.png" alt="Snake"><br><sub><b>Snake</b> and <b>Minesweeper</b> included</sub></td>
<td><img src="docs/img/screenshots/calculator.png" alt="Calculator"><br><sub><b>Calculator</b></sub></td>
</tr>
</table>

<sub>All screenshots are rendered by the host test harnesses from the real compositor code (1280x800 unless noted), not captured from QEMU.</sub>

## The peacock

<table><tr>
<td width="260"><img src="docs/img/peacock-art.png" alt="Peacock and lotus artwork" width="260"></td>
<td>The peacock-and-lotus artwork is the OS identity: it is the boot logo, the launcher / dock button and the default wallpaper theme. Full-size originals live in <code>assets/peacock.jpg</code> and <code>assets/peacock-logo.jpg</code> (copies in <code>docs/img/</code>).</td>
</tr></table>

## Architecture

<img src="docs/img/architecture.svg" alt="Layered architecture" width="100%">

### Boot and disk layout

<img src="docs/img/boot-flow.svg" alt="Boot flow" width="100%">

| Region | Location | Content |
|---|---|---|
| Stage 1 | LBA 0 | 512-byte MBR, loads stage 2 |
| Stage 2 | LBA 1-4 | A20, memory map, long-mode switch, loads kernel |
| Kernel | LBA 5 -> `0x200000` | 2108 sectors in this build |
| Store | `(5 + kernel + 1023) & ~1023` | KCFS 2 slots A/B, logo (+7168), bundle (+7680), themes (bundle+8192) |
| Handover | `0x500` | `'PEAC'` block: memory map, boot drive, checksum |

### Rendering pipeline

<img src="docs/img/render-pipeline.svg" alt="64-bit render pipeline" width="100%">

Each pixel in the back buffer is `A<<48 | R<<32 | G<<16 | B`, with 8-bit colours widened by `c * 257`. The flush stage applies a 4x4 Bayer dither and writes 24/32 bpp to the linear framebuffer, so the *internal* pipeline is 64 bpp while the *output* is limited by the display hardware. Cost: about 1.4x slower compositing than the old 32-bit buffer.

## Terminal reference

```text
files     ls [-la] cd pwd cat mkdir touch rm [-r] cp [-r] mv echo [> file] stat attr fsck sync
text      head tail wc grep [-nir] find [-name x] tree du df edit <file>
network   ifconfig dhcp ping nslookup wget <url> [file]  browse [url]
system    ver uname date uptime mem cpu neofetch  ps kill <id>  spawn counter|spin|hog [n]
hardware  lspci [-v]  lscpu  lsmem  acpi  usb  usb read <sector>
programs  name | ./name.pea   peac <src> [out]   peadump <prog>   run <name>
apps      open <terminal|notes|paint|calc|files|cal|clock|snake|mines|monitor|web|settings|usb|network|builder|3d>
power     reboot  poweroff
install   install [-l] [folder]    unpack the KingCobra sources (default /usr/src)
keys      Up/Down history - Tab complete - PgUp/PgDn scroll - Ctrl+L clear - Ctrl+U kill
```

## Build and test

```sh
make                       # kernel + bootloader + image
make run                   # boot in QEMU            make run-serial   # headless, serial console
make boot-selftest         # KingCobra bootloader == NASM bootloader, byte for byte
make host-test             # all host suites
make boot-sim              # simulated BIOS boot of the real image
make test                  # headless QEMU boot + screendump check (needs QEMU)
```

| Suite | Covers |
|---|---|
| `host-test-fs`, `-files` | KCFS 2, crash recovery, file manager |
| `host-test-threads` | scheduler, mutex, semaphore, queues |
| `host-test-net` | ARP/IP/DHCP/DNS/TCP/HTTP against a simulated NIC |
| `host-test-usb` | UHCI enumeration, HID, mass storage, hot-plug (~60 checks) |
| `host-test-hw` | PCI enumeration, BARs, capabilities, ACPI, S5, CPUID |
| `host-test-ui`, `-theme`, `-font`, `-svg`, `-splash`, `-clock` | compositor, Settings, themes, fonts, icons |
| `host-test-apps`, `-notes`, `-bld`, `-pkg`, `-3d` | applications, editor, App Builder, `.pea` packaging, 3D |

## Repository layout

```text
boot/       stage 1 + stage 2 in KingCobra, with an x86 instruction emitter
kernel/     the OS: main, gfx, ui, apps, settings, browser, builder, kcfs, fs, net, nic,
            pci, hwctl, usb, usbhw, threads, studio3d, notepad, svg, fonts, theme, ...
tools/      asset generators (SVG -> kernel data, fonts, themes, README art)
assets/     fonts, glyphs, icons, themes, logo
tests/      host harnesses (tests/host), boot simulator, QEMU test
docs/img/   README banner, icons, badges, diagrams, screenshots
CHANGELOG.md   full per-release notes, 0.5 to 1.9
```

About 17,000 lines of KingCobra in `kernel/`. The README art is generated by `tools/mkreadme.py`.

## Tested on

| Environment | Status |
|---|---|
| QEMU on a laptop | Tested |
| QEMU on Android | Tested |
| Real hardware (bare metal) | **Not tested** |
| Host harnesses and boot simulator | Pass (see above) |

Peacock OS has been tested on **QEMU only**.

## Honest limits

- **QEMU only.** The author has run it on QEMU (laptop and Android); it has never been booted on real hardware, so real PCI/ACPI/USB/NIC behaviour is unverified. The automated suites are host harnesses (real kernel code against simulated hardware) plus a boot simulator, not a QEMU run in CI.
- Screen output is 24/32 bpp; the 64-bit pipeline is internal.
- USB: UHCI only (no OHCI/EHCI/xHCI), no hubs, mass storage is read-only.
- Network: RTL8139 only; no TLS, so `https://` sites do not load; the browser has no CSS, JavaScript or images.
- BIOS boot only (no UEFI); single CPU, cooperative threads.
- Pointer and keyboard fall back to PS/2 when no USB device is present.

## License and credits

MIT License - see [LICENSE](../LICENSE). Created by **Divyanshu Sinha**. See also [CONTRIBUTING](../CONTRIBUTING.md), [CODE_OF_CONDUCT](../CODE_OF_CONDUCT.md) and [SECURITY](../SECURITY.md) in the parent repository.
