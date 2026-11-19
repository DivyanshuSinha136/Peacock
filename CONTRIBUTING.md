# Contributing to Peacock OS

Thanks for helping. Peacock OS is a bootable x86-64 desktop operating system written entirely in [KingCobra](https://github.com/DivyanshuSinha136/kingcobra) - bootloader, kernel, drivers, file system, network stack, window manager and applications. It has no third-party runtime dependencies, and we'd like to keep it that way.

## Ways to contribute

- **Report a bug** - open an [issue](https://github.com/DivyanshuSinha136/Peacock/issues/new). Include the Peacock version (`ver` in the Terminal, or Settings > System), how you booted it (QEMU command line, host OS, or real hardware), and what you expected versus what happened.
- **Test on more environments** - the project has so far been run on **QEMU only** (laptop and Android hosts). Reports from other QEMU versions, other emulators (VirtualBox, VMware, Bochs) and real BIOS hardware are the most valuable contribution you can make. Please include the output of `lspci`, `lscpu` and `acpi`.
- **Propose a feature or driver** - open an issue first so the design can be discussed before code is written.
- **Improve docs and screenshots** - fixes to `README.md`, `CHANGELOG.md` and `docs/` are always welcome.
- **Security issues** - do **not** open a public issue; see [SECURITY.md](SECURITY.md).

## Getting set up

You need the KingCobra toolchain (`kingcobra` and the `kcc` compiler sources), `make`, `python3` with Pillow (asset tools), and, to run the OS, `qemu-system-x86_64`. Peacock is expected to sit next to the KingCobra checkout:

```text
kingcobra/
  kcc/            compiler for the kcos target
  kingcobra       interpreter binary
  peacock/        <- this project
```

```sh
cd peacock
make                      # builds peacock.img (bootable raw image)
make run                  # boots it in QEMU
make host-test            # runs every host-side test suite (no QEMU needed)
make boot-selftest        # KingCobra bootloader must equal the NASM build, byte for byte
make boot-sim             # simulated BIOS boot of the real image
make test                 # headless QEMU boot + screendump check (needs QEMU)
```

Run a single area while you work, for example `make host-test-usb` or `make host-test-ui`. See the *Build and test* section of the README for what each suite covers.

## Project layout

| Path | What lives there |
|---|---|
| `boot/` | Stage 1 + stage 2 bootloader in KingCobra, with an x86 instruction emitter |
| `kernel/` | The OS: graphics, UI, apps, KCFS 2, threads, network, PCI, ACPI, USB, ... |
| `tools/` | Generators for kernel data (SVG icons, fonts, themes) and README art |
| `assets/` | Fonts, glyphs, icons, themes, logo and artwork |
| `tests/host/` | Host harnesses that run kernel code against simulated hardware |
| `tests/` | Boot simulator and QEMU test |
| `docs/img/` | README banner, icons, badges, diagrams and screenshots |

## Making a change

1. **Open or find an issue** for anything bigger than a small fix.
2. **Branch** from `main`: `git checkout -b fix/short-description`.
3. **Keep it focused.** One logical change per pull request.
4. **Add tests.** A bug fix needs a regression test in the matching `tests/host/harness_*.kc`; a new driver needs a simulated device so it can be tested without hardware.
5. **Run `make host-test` and `make boot-sim`** and make sure both pass before you push. If you changed the bootloader, also run `make boot-selftest`.
6. **Update docs.** User-visible changes need a README/CHANGELOG entry.
7. **State how you verified it.** Say whether the change was exercised only in host harnesses, or also in QEMU or on hardware. Hardware code (PCI, ACPI, USB, NIC, boot) that has only met a simulator should say so.
8. **Open a pull request.**

## Coding guidelines

- **KingCobra only** for the OS itself. Python in `tools/` is for build-time asset generation, never at run time.
- 4-space indentation; keep functions small and name them by subsystem (`usb_*`, `pci_*`, `set_*`).
- **Function names are global across `kernel/*.kc`.** A duplicate name produces a misleading compiler error (`no field 'implicit'`). Check with:
  ```sh
  cat kernel/*.kc | grep -o "^fn [A-Za-z_0-9]*" | sort | uniq -d
  ```
- Locals cannot shadow globals from other files, and words such as `from` are reserved - pick another name.
- Very large string literals (about 18 KB and up) can crash `kcc`; put big data in generated tables instead.
- Hardware access goes through the HAL (`kernel/hw.kc`, `kernel/pci.kc`, `kernel/usbhw.kc`), so the host harnesses can substitute simulators from `tests/host/`. Do not issue port or MMIO accesses directly from driver logic.
- The kernel is single-CPU with cooperative threads: never busy-wait without yielding or polling the UI loop.
- Never trust data from disk, network or devices: bounds-check lengths and keep checksums (KCFS 2 uses CRC32; the boot handover block is checksummed).
- Mind memory: the heap is 120 MiB and the back buffer costs 8 bytes per pixel.
- Regenerate generated files with the tools instead of editing them by hand (`tools/mksvg.py` -> `kernel/svgdata.kc`, `tools/mkreadme.py` -> `docs/img/`).

## Commit messages

Short imperative summary (about 72 characters), then an optional body explaining *why*:

```text
usb: ignore stale port-change bits after hot-unplug

The scan re-enumerated a port that had already been cleared...
```

Prefix with the area (`boot:`, `usb:`, `pci:`, `ui:`, `fs:`, `net:`, `docs:`, `tests:`) where it helps.

## Review

Pull requests are reviewed by the maintainer. Expect questions about edge cases, robustness against bad hardware responses, and test coverage.

## License

By contributing you agree that your contributions are licensed under the [MIT License](LICENSE).

Please also follow the [Code of Conduct](CODE_OF_CONDUCT.md).
