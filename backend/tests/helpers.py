"""Shared test helpers: build a small tagged music library (WAV/FLAC/garbage)."""
import math
import struct
import wave
from pathlib import Path

from mutagen.id3 import TALB, TCON, TDRC, TIT2, TPE1, TRCK
from mutagen.wave import WAVE

# (relative_dir, filename, title, artist, album, genre, year, track, duration_s)
WAV_SPECS = [
    ("周杰伦/依然范特西", "t1.wav", "夜的第七章", "周杰伦", "依然范特西", "流行", 2006, 1, 6),
    ("周杰伦/依然范特西", "t2.wav", "听妈妈的话", "周杰伦", "依然范特西", "流行", 2006, 2, 5),
    ("Adele/21", "t3.wav", "Rolling in the Deep", "Adele", "21", "Pop", 2011, 1, 5),
    # Same album title for two different artists -> album scoping test
    ("李宗盛/同名专辑", "t4.wav", "山丘", "李宗盛", "同名专辑", "民谣", 2013, 1, 5),
    ("Adele/同名专辑", "t5.wav", "Make You Feel My Love", "Adele", "同名专辑", "Pop", 2008, 1, 5),
]


def _make_wav(path: Path, duration_s: float, freq: float = 440.0):
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


def _tag_wav(path: Path, title, artist, album, genre, year, track):
    audio = WAVE(str(path))
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


def build_test_library(base: Path) -> Path:
    """Create a test music library; returns the library root path."""
    base.mkdir(parents=True, exist_ok=True)
    for rel_dir, fname, title, artist, album, genre, year, track, dur in WAV_SPECS:
        fpath = base / rel_dir / fname
        _make_wav(fpath, dur, freq=220 + hash(fname) % 400)
        _tag_wav(fpath, title, artist, album, genre, year, track)
    # Garbage "mp3" that must be skipped by the scanner
    corrupt = base / "corrupt_dir" / "broken.mp3"
    corrupt.parent.mkdir(parents=True, exist_ok=True)
    corrupt.write_bytes(b"\x00\x01\x02 not really mp3 data " * 10)
    return base
