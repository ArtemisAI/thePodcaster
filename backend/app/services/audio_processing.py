"""Audio post-processing helpers using FFmpeg.

Implement high-level functions:

* `merge_tracks(intro: Path, main: Path, outro: Path) -> Path`
* `normalize_volume(input: Path) -> Path`
* `apply_pitch_shift(input: Path, semitones: float) -> Path`

Each should spawn an FFmpeg subprocess or use `ffmpeg-python` to build the
filter graph.  Ensure commands are safe from shell injection.
"""

# TODO: implement functions using ffmpeg-python with proper error handling
