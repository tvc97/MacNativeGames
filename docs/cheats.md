# Cheats

The Mac app can apply Atmosphère-format cheat codes (the `[Name]` + hex-line files cheat databases publish) to the game's main module when it starts: **Tears of the Kingdom** (1.0.0, 1.2.1, 1.4.3) and **Breath of the Wild** (1.6.0, 1.9.0). Nothing here is tied to one game: the file is named after the build ID of the main module the runtime loaded, so the same mechanism serves both.

Implementation: [runtime/cheats.c](../games/totk/runtime/cheats.c), wired in by [runtime/cheats.h](../games/totk/runtime/cheats.h) (loader, input) and the launcher. This is a local patch on top of upstream — [below](#keeping-this-on-top-of-upstream) says how to keep it through an upstream merge.

iPhone and iPad builds are not affected: their code is already sealed shared pages before the game starts, so the runtime does nothing there.

## Where the file goes

```
~/Library/Application Support/MacNativeGames/TOTK/cheats/<build id>.txt     Tears of the Kingdom
~/Library/Application Support/MacNativeGames/BotW/cheats/<build id>.txt     Breath of the Wild
```

`<build id>` is the first 16 hex digits of the main module's build ID — the same name cheat databases use:

| Game | Version | File name |
|---|---|---|
| Tears of the Kingdom | 1.4.3 | `277178B7DBA1B6D4.txt` |
| Tears of the Kingdom | 1.0.0 | `082CE09B06E33A12.txt` |
| Breath of the Wild | 1.9.0 | `CD57B23FA4BBAD65.txt` |
| Breath of the Wild | 1.6.0 | that version's own build ID in your cheat database |

The runtime reads the build ID from the loaded image and only opens the file with that name. Codes filed under another build ID are never loaded. Codes for another version pasted into the right file can't be detected, and will usually crash the game.

Start the game once with no file and the log says what it looked for (`[cheats] none (<path> not found)`), which is the name to use.

Edit the file, then start the game again. No rebuild is needed. Set `TOTK_CHEATS=0` to start without cheats, or `TOTK_CHEATS_DIR=<dir>` to use another folder (both games).

## File format

```
[Inf. Stamina]
040A0000 009F1DC4 1E204041

#[Quickfire Bow]
040A0000 01D2FE5C 291FA268

// a comment
```

- **Sections:** `[Name]` or `{Name}` starts a section. Every section is applied, except one whose header starts with `#`, as in `#[Name]`. A `#` header switches off its whole section until the next header.
- **Comments:** any other line starting with `#` or `//` is a comment.
- **Codes:** lines of 8-digit hex words.

## What works

- **Static writes (opcode `0`) to the main module (memory type `0`):** the `04…` and `08…` lines that make up most cheats. They are written once at startup, after the port's own patches and before the code is locked read-only, and they stay on for the whole session.
- **Writes into the data segment** are also made once, so the game may overwrite them later.
- **Hold-a-button cheats** (`8kkkkkkk` … `21000000` else … `20000000` end). The runtime runs them every time the game reads the controller, as Atmosphère's cheat VM does. Their writes may target:
  - data or read-only data, such as a speed constant. These are written directly; a read-only page is made writable after the code is locked.
  - code, but only when every value written is a `MOVZ`/`MOVN` of one register, e.g. "Movement Speed (Hold B)" writing `mov w8, #1.0f` / `#2.0f`. At startup that instruction is replaced by a branch to a 3-instruction stub that loads the register from a slot on the main module's private data page; each controller read updates the slot. The code itself never changes while it is sealed.
- **Key masks** use the console's button bits: A `1`, B `2`, X `4`, Y `8`, L3 `10`, R3 `20`, L `40`, R `80`, ZL `100`, ZR `200`, + `400`, − `800`, and the D-pad `1000`–`8000`. Stick directions (left stick `10000`–`80000`, right stick `100000`–`800000`) count when the stick is more than half way. Add masks together for combinations.
- **Folder markers** are ignored: sections holding only `20000000` / `20000001`, which cheat managers use for groups.

## What doesn't

- **Register, pointer and loop opcodes** (`3`, `4`–`7`, `9`, `A`, `C`…). These include "Moon Jump" and cheats that follow a pointer chain into the heap. A section that uses any of them is skipped as a whole.
- **Button cheats that change arbitrary code**, for example an `fmul`, as in "Time RW/FF" or the mission-timer cheat. Code can't change while it is sealed, so these are skipped.
- **Turning a static cheat on or off while playing.** Edit the file and restart the game.

## What the runtime checks

A section is skipped, and nothing from it is written, when:

- a write falls outside the game's own image;
- a write would overwrite an instruction this port rewrote (a branch into the port's patch area);
- a line isn't 8-digit hex words.

The game still starts either way.

The format carries no "original instruction", so a code for a different game version can't be caught beyond the file name. Turn the app's debug log on to see what happened:

```sh
defaults write org.macnativegames.totk TOTK_DEBUG_LOG -bool true     # Breath of the Wild: org.macnativegames.botw
```

`~/Library/Logs/MacNativeGames/totk.log` (or `botw.log`) then lists each write as `[cheats] [Name] main+0x… (text): 4 bytes 0x<old> -> 0x<new>`, then a summary line with the number of sections applied, armed (switched by buttons), skipped and disabled. Without the debug log these lines go nowhere, as every other runtime message does. Check it after the first start with a new code.

## Cheats and mods

Upstream's own way to change game behaviour is a mod: `build_app.py --mod <folder>` merges `exefs/main.pchtxt`, `*.ips` or `*.ips32` into the code at build time, and `TOTK_PCHTXT=<file>` applies a `.pchtxt` at launch ([mods.md](mods.md)). Those are static patches. A cheat folder is the way to get the Atmosphère `[Name]`-per-entry layout, whole cheat-database files and button-controlled entries.

## Keeping this on top of upstream

Everything lives in new files, so an upstream merge only has to re-add the hook lines. `python3.14 tools/cheats/verify.py` checks the whole patch and prints exactly what is missing; run it after `git merge upstream/main`.

| File | What it holds |
|---|---|
| `games/totk/runtime/cheats.c`, `cheats.h` | the whole implementation (new files, never in conflict) |
| `games/totk/runtime/loader.c` | `#include "cheats.h"`, and `runtime_cheats(&modules[i])` before the `seal(...)` loop, `runtime_cheats_sealed(&modules[i])` after it (both inside `if(!strcmp(argv[2],"boot"))`) |
| `games/totk/runtime/input.c` | `#include "cheats.h"`, the weak `runtime_cheats_input` (so the input probes still link), and the call in `pad_states` |
| `games/totk/app/launcher.m` | the `TOTK_CHEATS_DIR` default (`<data>/cheats`) |
| `games/totk/Makefile` | `runtime/cheats.c` in the runtime link commands (Tears of the Kingdom and Breath of the Wild) and in the `build/totk-native` prerequisites |
| `docs/cheats.md`, `tools/cheats/verify.py` | this page and the checker |

If upstream moves the patch/private-page layout, `cheats.c` says where it expects it (`private_page`, `VENEER_AREA`, `SLOT_AREA`); the runtime's `seal()` and `map_module()` (`m->size = page_up(file_size) + 0x4000` for `main`) define it, and both are checked at load: a cheat that finds no room is skipped, not applied blindly.
