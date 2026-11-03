#pragma once
#include "runtime.h"

/* Atmosphère-format cheats for the main module, Mac (docs/cheats.md). The loader applies the static ones before the
   modules are sealed (loader.c) and makes the button ones' read-only data writable once they are (runtime_cheats_sealed);
   input.c calls runtime_cheats_input on every controller read, so a "hold" cheat acts while the button is down. Both
   Tears of the Kingdom and Breath of the Wild use this file: the glues are game-independent, the cheat file is named
   after the build ID of the main module that was loaded. On the iPhone / iPad the code is already sealed shared pages,
   so runtime_cheats does nothing there. */
void runtime_cheats(Module *main_module);   /* runtime/cheats.c: $TOTK_CHEATS_DIR/<build id>.txt, before sealing */
void runtime_cheats_sealed(Module *main_module);   /* after sealing: data pages that button cheats write become writable */
void runtime_cheats_input(uint64_t buttons, int lx, int ly, int rx, int ry);   /* every controller read: runs the button cheats */
