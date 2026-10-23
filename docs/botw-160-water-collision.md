# Breath of the Wild 1.6.0: water without collision after a save loads (open)

This fork's record of an open bug, 2026-10-23. Mac, BotW 1.6.0 with both DLC packs, the 120 Hz display, uncapped and
at a 30 fps cap. Evidence (logs and screenshots) is in
`~/Library/Application Support/MacNativeGames/BotW/tests/2026-10-23-water`; it is not copied into the repository.

## Symptom

After the game starts and a save loads, some field water near the load point has no collision: Link walks on the river
bed under water that is drawn, and in one run swam on the grass by Riverside Stable (north-east of the Great Plateau)
while the channel under the stable's bridge was empty. Once the water at one spot was wrong after loading the save
again, and once Link drowned where there is no deep water. Teleporting away and back fixed it in most runs, but not in
all. The frame rate does not change it.

## Ruled out

Each with one launch and the same save at Riverside Stable:

| Switch | Result |
|---|---|
| `TOTK_ROMFS_CACHE=0` (RomFS block cache off) | still wrong |
| `TOTK_SLINK_REALTIME=0` (sound-link rate fix off) | still wrong |
| `flag writeback 0` during the run | still wrong (no recovery once wrong) |
| `TOTK_LAZY_CLEAR=0 TOTK_CB_EXTENT=0 TOTK_FINISH_PRESENTS=1` (the nxnative renderer changes off) | still wrong |
| `TOTK_RENDER_RES=900` (the 1600x900 render size as shipped) | water under the bridge right; nearby water still without collision after loading, in both of two runs |
| `TOTK_REALTIME=0` at a 30 fps cap (the shipped frame step and physics substeps) | still wrong |
| `TOTK_EXCL_ACQUIRE=0` (shipped exclusive loads) | first run crashed in the job queue (the known reason for the patch), second run still wrong |
| `TOTK_ASYNC_SHADERS=0 TOTK_OCCL_SKIP=0` (no skipped draws while shaders are prepared) | still wrong |
| `TOTK_WB_STAGE=0 TOTK_WB_BATCH=0` (write-back staging and batching off) | still wrong, and the ground collision was also off early in the run |

A patch that kept the display-mode routine's second scale (`1280 / render width`, `[[[gfx+0x158]]+0x36b8]+0x588`
`+0xc54`) at the shipped 0.8 under the 1080p render was tried and dropped: the value was already 0.8 at the next launch
(`TOTK_SCALE_LOG`, a temporary diagnostic) and the bug was still there.

## Lead

The game renders 256x256 R16 targets (NVN format 0x6) on the GPU and has them written back to the CPU: about 600 in a
4,000-frame run (`DM_NVN_TILELOG=256x256`). Their size and format fit terrain or water height tiles that the CPU turns
into collision, and the bad ground collision with staging off points the same way. At the save load (frame 815 of
that run) the game created twelve of them in one frame, and five times it created a second texture over memory whose
GPU rendering was not written back yet (`first upload from the pool bytes` after `GPU render` of another serial at the
same address); that second texture was finalised before the recorded commands that name it ran (`not followed: no
live texture at its storage`). The same order also shows up on frames where the water was right (5 to 16 times per 100
frames all through the run), so it is not proven to be the cause. Next step: dump the R16 tiles written back at the
load and after a teleport at the same spot and compare them. The code involved (`botw_tex_follow`, the write-back
staging) is upstream's, so upstream most likely shows the same bug.

## Diagnostic switch

`TOTK_WB_STAGE=0` (BotW, `nvn_mtl.m`): write-backs read the texture back as before the staging and nothing is copied
into stage buffers at the end of a submission. Off by default (staging stays on).
