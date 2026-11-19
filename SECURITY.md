# Security policy

## Supported versions

Security fixes go into the **latest release** and `main`.

| Version | Supported |
|---|---|
| Latest release (1.9.x) | Yes |
| Older releases | No - please upgrade |

## Reporting a vulnerability

**Please do not open a public issue for security problems.**

Report privately by either:

1. Using GitHub's **[Report a vulnerability](https://github.com/DivyanshuSinha136/Peacock/security/advisories/new)** form, or
2. Emailing **divyanshu.sinha631@gmail.com** with the subject `Peacock OS security`.

Please include the Peacock version (`ver`), how you ran it (QEMU command line or hardware), a minimal reproduction, and what you
think the impact is.

You can expect an acknowledgement within about a week, and updates as the issue is investigated. Fixes are released with a
changelog note, and reporters are credited unless they prefer otherwise.

## What counts as a vulnerability

In scope, for example:

- Memory-safety or bounds bugs in code that parses untrusted input: the TCP/IP stack, DHCP, DNS, HTTP and the HTML renderer, the USB descriptor and mass-storage paths, the KCFS 2 and `.pea` loaders.
- Ways a crafted disk image, USB device, network packet or web page can crash the kernel, corrupt memory, or run attacker-chosen code.
- Flaws in integrity checks (KCFS 2 CRC32 recovery, boot handover checksum) that let corrupt data be accepted silently.

## Things to know before reporting

Peacock OS is a hobby / research operating system. By design it currently has:

- a **single address space and no user/kernel privilege separation** - `.pea` programs and apps run with kernel privileges;
- **no user accounts or file permissions** beyond simple attributes;
- **no TLS** (traffic is plain HTTP), so network contents are not confidential or authenticated;
- **no hardening features** such as ASLR or stack protection.

These are known design limits rather than vulnerabilities, so reports that only point them out are out of scope. Do not rely on Peacock OS to isolate untrusted programs or protect sensitive data.

Also note that the project has so far been tested on **QEMU only**; behaviour on real hardware is unverified.
