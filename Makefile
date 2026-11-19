# Peacock build -- Author: Divyanshu Sinha (MIT License)
#
#   make            build peacock.img (needs only the KingCobra interpreter: no nasm, no C compiler)
#   make run        boot it in QEMU (window)          make run-serial   headless, kernel log on this terminal
#   make test       boot headless in QEMU, check the log + a screendump (needs qemu-system-x86_64 and python3)
#   make host-test  run the desktop as a Linux program and write PPM screenshots (needs only KingCobra)
#
# Place this folder in the KingCobra repository root (next to kcos/).  KINGCOBRA = the interpreter binary, KCC = kcc's entry file.
KINGCOBRA ?= ../kingcobra
KCC       ?= $(KINGCOBRA) ../kcc/src/main.kc
BUILD     := build
SRC       := $(wildcard kernel/*.kc) kernel/svgdata.kc kernel/fontdata.kc kernel/peacockicon.kc
QEMU      ?= qemu-system-x86_64
# BUNDLE=1 packs the KingCobra sources (BUNDLE_SRC, default: the repository root) into the image; `install` in the terminal unpacks them.
BUNDLE     ?= 1
BUNDLE_SRC ?= ..
QEMUFLAGS ?= -m 128 -vga std -nic user,model=rtl8139

all: peacock.img

$(BUILD)/boot.bin: boot/boot.kc boot/x86.kc
	@mkdir -p $(BUILD)
	$(KINGCOBRA) boot/boot.kc $@

$(BUILD)/kernel.bin: $(SRC)
	@mkdir -p $(BUILD)
	$(KCC) kernel/main.kc -o $@ --target kcos --base 0x200000 --stack 0x90000 $(if $(MAP),--map,)

ifeq ($(BUNDLE),1)
BUNDLE_DEP  := $(BUILD)/kingcobra.pkg
BUNDLE_ARGS := --bundle $(BUILD)/kingcobra.pkg
endif

$(BUILD)/kingcobra.pkg: FORCE
	@mkdir -p $(BUILD)
	$(KINGCOBRA) tools/mkbundle.kc $(BUNDLE_SRC) -o $@ --name kingcobra

FORCE:

peacock.img: $(BUILD)/boot.bin $(BUILD)/kernel.bin tools/mkimage.kc assets/logo.raw assets/themes.raw $(BUNDLE_DEP)
	$(KINGCOBRA) tools/mkimage.kc $(BUILD)/boot.bin $(BUILD)/kernel.bin -o $@ $(BUNDLE_ARGS) --logo assets/logo.raw --themes assets/themes.raw

run: peacock.img
	$(QEMU) -drive format=raw,file=peacock.img $(QEMUFLAGS)

run-serial: peacock.img
	$(QEMU) -drive format=raw,file=peacock.img $(QEMUFLAGS) -display none -serial stdio

boot-sim: peacock.img
	python3 tests/bootsim.py peacock.img

test: peacock.img
	python3 tests/qemu_test.py peacock.img

host-test: $(BUILD)/kingcobra.pkg
	@mkdir -p $(BUILD)
	$(KCC) tests/host/harness.kc -o $(BUILD)/harness
	cd $(BUILD) && ./harness

host-test-pkg: $(BUILD)/kingcobra.pkg
	@mkdir -p $(BUILD)
	$(KCC) tests/host/harness_pkg.kc -o $(BUILD)/harness_pkg
	cd $(BUILD) && ./harness_pkg

host-test-bld:
	@mkdir -p $(BUILD)
	$(KCC) tests/host/harness_bld.kc -o $(BUILD)/harness_bld
	cd $(BUILD) && ./harness_bld

host-test-hw:
	@mkdir -p $(BUILD)
	cp assets/logo.raw assets/themes.raw $(BUILD)/
	$(KCC) tests/host/harness_hw.kc -o $(BUILD)/harness_hw
	cd $(BUILD) && ./harness_hw

host-test-usb:
	@mkdir -p $(BUILD)
	cp assets/logo.raw assets/themes.raw $(BUILD)/
	$(KCC) tests/host/harness_usb.kc -o $(BUILD)/harness_usb
	cd $(BUILD) && ./harness_usb

host-test-net: $(BUILD)/kingcobra.pkg
	@mkdir -p $(BUILD)
	$(KCC) tests/host/harness_net.kc -o $(BUILD)/harness_net
	cd $(BUILD) && rm -f to_guest.fifo from_guest.fifo && mkfifo to_guest.fifo from_guest.fifo \
	  && (python3 ../tests/gateway.py &) && timeout 120 ./harness_net; rc=$$?; cat gateway.log; exit $$rc

boot-selftest:
	@mkdir -p $(BUILD)
	$(KINGCOBRA) tests/ref_kcos_boot.kc $(BUILD)/ref_kcos_boot.bin
	cmp $(BUILD)/ref_kcos_boot.bin tests/ref/kcos_boot.bin && echo "encoder reproduces the NASM-built KCOS boot stage byte for byte"

clean:
	rm -rf $(BUILD) peacock.img

.PHONY: FORCE host-test-3d host-test-threads host-test-files host-test-fs host-test-font host-test-svg host-test-clock host-test-apps host-test-ui host-test-theme host-test-notes host-test-usb host-test-hw host-test-splash host-test-bld host-test-net host-test-pkg all run run-serial boot-sim test host-test boot-selftest clean

kernel/fontdata.kc: $(wildcard assets/fonts/*.svg) tools/mkfonts.py
	python3 tools/mkfonts.py assets/fonts $@

kernel/peacockicon.kc: assets/peacock.jpg tools/mkpeacock.py
	python3 tools/mkpeacock.py assets/peacock.jpg $@

kernel/svgdata.kc: $(wildcard assets/icons/*.svg) tools/mksvg.py
	python3 tools/mksvg.py assets/icons $@

assets/themes.raw: $(wildcard assets/themes/*.jpg) tools/mkthemes.py
	python3 -W ignore tools/mkthemes.py assets/themes $@

assets/logo.raw: assets/peacock-logo.jpg tools/mklogo.py
	python3 tools/mklogo.py assets/peacock-logo.jpg $@

host-test-notes:
	@mkdir -p $(BUILD)
	cp assets/logo.raw assets/themes.raw $(BUILD)/
	$(KCC) tests/host/harness_notes.kc -o $(BUILD)/harness_notes
	cd $(BUILD) && ./harness_notes

host-test-theme:
	@mkdir -p $(BUILD)
	cp assets/logo.raw assets/themes.raw $(BUILD)/
	$(KCC) tests/host/harness_theme.kc -o $(BUILD)/harness_theme
	cd $(BUILD) && ./harness_theme

host-test-3d:
	@mkdir -p $(BUILD)
	$(KCC) tests/host/harness_3d.kc -o $(BUILD)/harness_3d
	$(BUILD)/harness_3d

host-test-files:
	@mkdir -p $(BUILD)
	cp assets/logo.raw assets/themes.raw $(BUILD)/
	$(KCC) tests/host/harness_files.kc -o $(BUILD)/harness_files
	cd $(BUILD) && ./harness_files

host-test-threads:
	@mkdir -p $(BUILD)
	cp assets/logo.raw assets/themes.raw $(BUILD)/
	$(KCC) tests/host/harness_threads.kc -o $(BUILD)/harness_threads
	cd $(BUILD) && ./harness_threads

host-test-fs:
	@mkdir -p $(BUILD)
	cp assets/logo.raw assets/themes.raw $(BUILD)/
	$(KCC) tests/host/harness_fs.kc -o $(BUILD)/harness_fs
	cd $(BUILD) && ./harness_fs

host-test-font:
	@mkdir -p $(BUILD)
	cp assets/logo.raw assets/themes.raw $(BUILD)/
	$(KCC) tests/host/harness_font.kc -o $(BUILD)/harness_font
	cd $(BUILD) && ./harness_font

host-test-svg:
	@mkdir -p $(BUILD)
	cp assets/logo.raw assets/themes.raw $(BUILD)/
	$(KCC) tests/host/harness_svg.kc -o $(BUILD)/harness_svg
	cd $(BUILD) && ./harness_svg

host-test-clock:
	@mkdir -p $(BUILD)
	cp assets/logo.raw assets/themes.raw $(BUILD)/
	$(KCC) tests/host/harness_clock.kc -o $(BUILD)/harness_clock
	cd $(BUILD) && ./harness_clock

host-test-apps:
	@mkdir -p $(BUILD)
	cp assets/logo.raw assets/themes.raw $(BUILD)/
	$(KCC) tests/host/harness_apps.kc -o $(BUILD)/harness_apps
	cd $(BUILD) && ./harness_apps

host-test-ui:
	@mkdir -p $(BUILD)
	cp assets/logo.raw assets/themes.raw $(BUILD)/
	$(KCC) tests/host/harness_ui.kc -o $(BUILD)/harness_ui
	cd $(BUILD) && ./harness_ui

host-test-splash:
	@mkdir -p $(BUILD)
	cp assets/logo.raw assets/themes.raw $(BUILD)/
	$(KCC) tests/host/harness_splash.kc -o $(BUILD)/harness_splash
	cd $(BUILD) && ./harness_splash
