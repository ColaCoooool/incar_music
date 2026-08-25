"""Generate a test music library for IncarMusic testing.

Creates WAV files (sine waves) with metadata tags under ./test_music.
Run with the backend venv python (needs mutagen).
"""

import math
import struct
import wave
from pathlib import Path

from mutagen.id3 import ID3, TALB, TCON, TDRC, TIT2, TPE1, TRCK
from mutagen.wave import WAVE

BASE = Path(__file__).resolve().parent.parent / "test_music"

# (relative_dir, filename, title, artist, album, genre, year, track, duration_s)
SPECS = [
    ("周杰伦/依然范特西", "t1.wav", "夜的第七章", "周杰伦", "依然范特西", "流行", 2006, 1, 20),
    ("周杰伦/依然范特西", "t2.wav", "听妈妈的话", "周杰伦", "依然范特西", "流行", 2006, 2, 18),
    ("周杰伦/范特西", "t3.wav", "双截棍", "周杰伦", "范特西", "流行", 2001, 1, 15),
    ("Adele/25", "t4.wav", "Hello", "Adele", "25", "Pop", 2015, 1, 22),
    ("Adele/21", "t5.wav", "Rolling in the Deep", "Adele", "21", "Pop", 2011, 1, 19),
    ("noartist/notags", "t6.wav", "", "", "", "", 0, 0, 12),  # no tags at all
]

# Same album title used by two different artists -> tests album/artist scoping
SPECS.append(("李宗盛/精选", "t7.wav", "山丘", "李宗盛", "同名专辑", "民谣", 2013, 1, 16))
SPECS.append(("Adele/同名专辑", "t8.wav", "Make You Feel My Love", "Adele", "同名专辑", "Pop", 2008, 1, 21))


def make_wav(path: Path, duration_s: float, freq: float = 440.0):
    path.parent.mkdir(parents=True, exist_ok=True)
    rate = 44100
    n = int(rate * duration_s)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        frames = bytearray()
        for i in range(n):
            v = int(12000 * math.sin(2 * math.pi * freq * i / rate))
            frames += struct.pack("<h", v)
        w.writeframes(bytes(frames))


def main():
    for rel_dir, fname, title, artist, album, genre, year, track, dur in SPECS:
        fpath = BASE / rel_dir / fname
        make_wav(fpath, dur, freq=220 + hash(fname) % 400)
        # Tag with mutagen (WAV uses ID3 frames, not easy tags)
        audio = WAVE(str(fpath))
        audio.add_tags()
        if title:
            audio.tags.add(TIT2(encoding=3, text=[title]))
        if artist:
            audio.tags.add(TPE1(encoding=3, text=[artist]))
        if album:
            audio.tags.add(TALB(encoding=3, text=[album]))
        if genre:
            audio.tags.add(TCON(encoding=3, text=[genre]))
        if year:
            audio.tags.add(TDRC(encoding=3, text=[str(year)]))
        if track:
            audio.tags.add(TRCK(encoding=3, text=[str(track)]))
        audio.save()
        print(f"created {fpath.relative_to(BASE)} ({dur}s)")

    # Corrupt "mp3" (garbage) to test scanner error handling
    corrupt = BASE / "corrupt_dir" / "broken.mp3"
    corrupt.parent.mkdir(parents=True, exist_ok=True)
    corrupt.write_bytes(b"\x00\x01\x02 not really mp3 data " * 10)
    print(f"created {corrupt.relative_to(BASE)} (garbage mp3)")

    # Unsupported format file
    txt = BASE / "notes.txt"
    txt.write_text("just a text file, should be skipped")
    print(f"created {txt.relative_to(BASE)} (skipped)")

    print("done")


if __name__ == "__main__":
    main()
