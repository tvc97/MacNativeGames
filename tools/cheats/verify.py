#!/usr/bin/env python3
"""MacNativeGames: check that the local cheat patch (docs/cheats.md) is still wired in after an upstream merge.

    python3.14 tools/cheats/verify.py

The cheat implementation itself lives in new files (games/totk/runtime/cheats.c and cheats.h), so a merge never conflicts
there. What a merge can drop are the handful of hook lines in the files upstream owns. This checks each one and prints
the line to put back. Exit status: 0 when every hook is in place, 1 otherwise.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNTIME = 'games/totk/runtime'

# (file, what it is for, text that must be there, repair)
HOOKS = [
    (f'{RUNTIME}/cheats.h', 'the cheat header', 'void runtime_cheats(Module *main_module);',
     'restore games/totk/runtime/cheats.h'),
    (f'{RUNTIME}/cheats.c', 'the implementation', 'void runtime_cheats(Module *m) {',
     'restore games/totk/runtime/cheats.c'),
    ('docs/cheats.md', 'this feature\'s page', '# Cheats', 'restore docs/cheats.md'),
    (f'{RUNTIME}/loader.c', 'include', '#include "cheats.h"', '#include "cheats.h" after #include "runtime.h"'),
    (f'{RUNTIME}/loader.c', 'static cheats before sealing',
     'runtime_cheats(&modules[i]);',
     'add if(!strcmp(argv[2],"boot"))for(unsigned i=0;i<NM;i++)if(!strcmp(modules[i].name,"main"))runtime_cheats(&modules[i]);'
     ' right after the runtime_game_patches(...) loop in main()'),
    (f'{RUNTIME}/loader.c', 'data pages after sealing',
     'runtime_cheats_sealed(&modules[i]);',
     'add if(!strcmp(argv[2],"boot"))for(unsigned i=0;i<NM;i++)if(!strcmp(modules[i].name,"main"))runtime_cheats_sealed(&modules[i]);'
     ' right after the seal(...)/check_permissions(...) loop in main()'),
    (f'{RUNTIME}/input.c', 'include', '#include "cheats.h"', '#include "cheats.h" after #include "runtime.h"'),
    (f'{RUNTIME}/input.c', 'the probes still link',
     '__attribute__((weak)) void runtime_cheats_input(',
     'add the weak runtime_cheats_input definition above the pad_states(...) declaration'),
    (f'{RUNTIME}/input.c', 'button cheats on each controller read',
     'runtime_cheats_input(state.buttons,state.lx,state.ly,state.rx,state.ry);',
     'call it inside pad_states() before "*out=state"'),
    ('games/totk/app/launcher.m', 'the per-game cheats folder', 'TOTK_CHEATS_DIR',
     'setenv("TOTK_CHEATS_DIR", env_or("TOTK_CHEATS_DIR", [data stringByAppendingPathComponent:@"cheats"]).fileSystemRepresentation, 1);'
     ' beside the other setenv calls in the launcher'),
]

MAKEFILE = 'games/totk/Makefile'
DEPENDENCY = 'build/totk-native: Makefile runtime/playtime.h runtime/loader.c'


def main() -> int:
    bad = 0
    for name, what, needle, fix in HOOKS:
        path = ROOT / name
        if not path.is_file():
            print(f'MISSING {name}: no such file ({what})')
            print(f'        fix: {fix}')
            bad += 1
        elif needle in path.read_text(encoding='utf-8', errors='replace'):
            print(f'OK      {name}: {what}')
        else:
            print(f'MISSING {name}: {what}')
            print(f'        fix: {fix}')
            bad += 1

    makefile = ROOT / MAKEFILE
    if not makefile.is_file():
        print(f'MISSING {MAKEFILE}: no such file')
        print('Cheat patch incomplete.')
        return 1
    lines = makefile.read_text(encoding='utf-8', errors='replace').splitlines()
    links = [line for line in lines if line.lstrip().startswith('xcrun clang -std=c11') and 'runtime/loader.c' in line]
    if not links:
        print(f'MISSING {MAKEFILE}: no runtime link command found (the build was restructured)')
        bad += 1
    else:
        without = [line for line in links if 'runtime/cheats.c' not in line]
        if without:
            print(f'MISSING {MAKEFILE}: {len(without)} of {len(links)} runtime link commands lack runtime/cheats.c')
            print('        fix: put runtime/cheats.c next to runtime/loader.c in each (Tears of the Kingdom and Breath of the Wild)')
            bad += 1
        else:
            print(f'OK      {MAKEFILE}: runtime/cheats.c in all {len(links)} runtime link commands')

    dependency = next((line for line in lines if line.startswith(DEPENDENCY)), None)
    if dependency is None:
        print(f'MISSING {MAKEFILE}: the build/totk-native prerequisites changed (expected them to start with "{DEPENDENCY}")')
        bad += 1
    elif 'runtime/cheats.c runtime/cheats.h' not in dependency:
        print(f'MISSING {MAKEFILE}: the build/totk-native prerequisites lack runtime/cheats.c runtime/cheats.h')
        bad += 1
    else:
        print(f'OK      {MAKEFILE}: build/totk-native prerequisites include the cheat sources')

    print('\nCheat patch complete.' if not bad else f'\n{bad} hook(s) missing: docs/cheats.md lists them, and each line above is the repair.')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
