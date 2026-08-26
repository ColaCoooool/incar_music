"""HLS streaming service.

Handles audio transcoding and adaptive bitrate streaming using FFmpeg.
"""

import asyncio
import json
import logging
import os
import shutil
from pathlib import Path
from typing import Optional

from core.config import settings

logger = logging.getLogger(__name__)


def is_ffmpeg_available() -> bool:
    """Check if FFmpeg is installed."""
    return shutil.which("ffmpeg") is not None


# Audio codecs browsers cannot decode natively in direct playback.
_BROWSER_UNSUPPORTED_CODECS = {
    "alac",  # Apple Lossless in .m4a
    "ape",  # Monkey's Audio
    "wmav1",
    "wmav2",
    "wmapro",
    "wmalossless",
}


def needs_browser_transcode(file_path: str) -> bool:
    """Return True when the file's codec cannot be decoded by browsers.

    Typical case: .m4a files encoded with ALAC (Apple Lossless), which Chrome /
    Edge / Firefox cannot play directly and must be transcoded to AAC first.
    """
    try:
        import mutagen

        audio = mutagen.File(file_path)
        if audio is None or audio.info is None:
            return False
        codec = (
            getattr(audio.info, "codec", None)
            or getattr(audio.info, "codec_name", None)
            or ""
        )
        return codec in _BROWSER_UNSUPPORTED_CODECS
    except Exception:
        return False


async def transcode_for_browser(file_path: str, song_id: int) -> Optional[str]:
    """Transcode a browser-unsupported file to AAC/m4a, cached by song id.

    Returns the cached file path, or None when ffmpeg is unavailable or the
    transcode fails. The cache is reused while the source file is unchanged.
    """
    if not is_ffmpeg_available():
        logger.error("ffmpeg not available; cannot transcode %s", file_path)
        return None

    cache_dir = settings.data_dir / "transcoded"
    cache_dir.mkdir(parents=True, exist_ok=True)
    out_path = cache_dir / f"song_{song_id}.m4a"

    try:
        src_mtime = Path(file_path).stat().st_mtime
    except OSError:
        return None

    if out_path.exists() and out_path.stat().st_mtime >= src_mtime:
        return str(out_path)

    tmp_path = cache_dir / f"song_{song_id}.tmp.m4a"
    cmd = [
        "ffmpeg",
        "-y",
        "-i", file_path,
        "-vn",
        "-c:a", "aac",
        "-b:a", "192k",
        "-ar", "44100",
        "-ac", "2",
        "-movflags", "+faststart",
        str(tmp_path),
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        logger.error(f"Browser transcode failed for {file_path}: {stderr.decode()}")
        tmp_path.unlink(missing_ok=True)
        return None

    tmp_path.replace(out_path)
    return str(out_path)


async def get_audio_info(file_path: str) -> dict:
    """Get audio file information using ffprobe."""
    if not is_ffmpeg_available():
        return {"error": "ffmpeg not available"}

    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        file_path,
    ]

    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()

    if proc.returncode != 0:
        return {"error": stderr.decode()}

    return json.loads(stdout.decode())


async def transcode_segment(
    input_path: str,
    output_path: str,
    bitrate: int = 192,
    start_time: float = 0,
    duration: float = 6,
) -> bool:
    """Transcode a single HLS segment."""
    if not is_ffmpeg_available():
        logger.error("ffmpeg not available for transcoding")
        return False

    output_path_obj = Path(output_path)
    output_path_obj.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "ffmpeg",
        "-y",
        "-i", input_path,
        "-ss", str(start_time),
        "-t", str(duration),
        "-b:a", f"{bitrate}k",
        "-ar", "44100",
        "-ac", "2",
        "-f", "adts",
        "-movflags", "+faststart",
        output_path,
    ]

    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    _, stderr = await proc.communicate()

    if proc.returncode != 0:
        logger.error(f"Transcode failed: {stderr.decode()}")
        return False

    return True


async def create_hls_stream(
    file_path: str,
    song_id: int,
    bitrate: int = 192,
) -> Optional[str]:
    """Create HLS stream for a song.

    Returns the path to the playlist file.
    """
    hls_dir = settings.hls_path / f"song_{song_id}" / f"br_{bitrate}"
    hls_dir.mkdir(parents=True, exist_ok=True)

    playlist_path = hls_dir / "playlist.m3u8"

    if playlist_path.exists():
        return str(playlist_path)

    # Get audio duration (ffprobe reports it as a string)
    info = await get_audio_info(file_path)
    duration_raw = info.get("format", {}).get("duration", 0)
    try:
        duration = float(duration_raw)
    except (TypeError, ValueError):
        duration = 0
    if not duration:
        return None

    # Calculate segments
    segment_duration = settings.HLS_SEGMENT_DURATION
    num_segments = int(duration / segment_duration) + 1

    # Generate segments in parallel (limited concurrency)
    semaphore = asyncio.Semaphore(4)

    async def create_segment(i: int):
        async with semaphore:
            start = i * segment_duration
            seg_path = str(hls_dir / f"segment_{i:04d}.aac")
            await transcode_segment(file_path, seg_path, bitrate, start, segment_duration)

    # Create segments
    tasks = [create_segment(i) for i in range(num_segments)]
    await asyncio.gather(*tasks)

    # Generate playlist
    with open(playlist_path, "w") as f:
        f.write("#EXTM3U\n")
        f.write("#EXT-X-VERSION:3\n")
        f.write(f"#EXT-X-TARGETDURATION:{segment_duration}\n")
        f.write(f"#EXT-X-MEDIA-SEQUENCE:0\n")
        f.write("\n")
        for i in range(num_segments):
            seg_duration = min(segment_duration, duration - i * segment_duration)
            f.write(f"#EXTINF:{seg_duration:.3f},\n")
            f.write(f"segment_{i:04d}.aac\n")

    return str(playlist_path)


async def copy_to_cache(file_path: str, song_id: int) -> Optional[str]:
    """Copy a song file to the cache directory for quick access."""
    cache_dir = settings.cache_path
    ext = Path(file_path).suffix
    cache_file = cache_dir / f"song_{song_id}{ext}"

    if cache_file.exists():
        return str(cache_file)

    try:
        shutil.copy2(file_path, cache_file)
        return str(cache_file)
    except Exception as e:
        logger.error(f"Cache copy failed for song {song_id}: {e}")
        return None


async def get_bitrate_for_network(available_bandwidth_kbps: int) -> int:
    """Select the best bitrate based on available bandwidth.

        Args:
            available_bandwidth_kbps: Estimated available bandwidth in kbps.

        Returns:
            Recommended bitrate in kbps.
        """
    if available_bandwidth_kbps >= 500:
        return 320
    elif available_bandwidth_kbps >= 256:
        return 192
    elif available_bandwidth_kbps >= 128:
        return 128
    else:
        return 64


async def cleanup_hls_segments(song_id: int, max_age_seconds: int = 3600):
    """Clean up old HLS segments to save disk space."""
    hls_dir = settings.hls_path / f"song_{song_id}"
    if not hls_dir.exists():
        return

    import time
    now = time.time()

    for br_dir in hls_dir.iterdir():
        if br_dir.is_dir():
            for seg_file in br_dir.iterdir():
                if seg_file.is_file():
                    age = now - seg_file.stat().st_mtime
                    if age > max_age_seconds:
                        seg_file.unlink()
