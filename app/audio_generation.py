from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[1]
AUDIO_OUTPUT_DIR = ROOT_DIR / "data" / "audio"


class AudioGenerationError(Exception):
    pass


def _resolve_command(command_name: str, env_name: str) -> str:
    configured_command = os.getenv(env_name, command_name).strip()
    resolved_command = shutil.which(configured_command)
    if not resolved_command:
        raise AudioGenerationError(f"Missing executable for {env_name}: {configured_command}")
    return resolved_command


def _resolve_model_path() -> Path:
    model_path = os.getenv("PODCAST_PIPER_MODEL_PATH", "").strip()
    if not model_path:
        raise AudioGenerationError("Missing Piper model path: set PODCAST_PIPER_MODEL_PATH")
    resolved = Path(model_path)
    if not resolved.exists():
        raise AudioGenerationError(f"Piper model not found: {resolved}")
    return resolved


def generate_local_mp3(script_text: str, job_id: str) -> dict[str, Any]:
    if not script_text.strip():
        raise AudioGenerationError("Script text is empty")

    piper_command = _resolve_command("piper", "PODCAST_PIPER_COMMAND")
    ffmpeg_command = _resolve_command("ffmpeg", "PODCAST_FFMPEG_COMMAND")
    model_path = _resolve_model_path()

    AUDIO_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    wav_path = AUDIO_OUTPUT_DIR / f"{job_id}.wav"
    mp3_path = AUDIO_OUTPUT_DIR / f"{job_id}.mp3"
    if wav_path.exists():
        wav_path.unlink()
    if mp3_path.exists():
        mp3_path.unlink()

    try:
        subprocess.run(
            [piper_command, "--model", str(model_path), "--output_file", str(wav_path)],
            input=script_text,
            text=True,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            [ffmpeg_command, "-y", "-i", str(wav_path), "-codec:a", "libmp3lame", "-q:a", "4", str(mp3_path)],
            text=True,
            capture_output=True,
            check=True,
        )
    except FileNotFoundError as error:
        raise AudioGenerationError(str(error)) from error
    except subprocess.CalledProcessError as error:
        stderr = (error.stderr or "").strip()
        stdout = (error.stdout or "").strip()
        message = stderr or stdout or str(error)
        raise AudioGenerationError(message) from error
    finally:
        if wav_path.exists():
            try:
                wav_path.unlink()
            except OSError:
                pass

    if not mp3_path.exists():
        raise AudioGenerationError("MP3 output was not created")

    return {
        "audio_file_name": mp3_path.name,
        "audio_download_url": f"/api/generation-jobs/{job_id}/audio",
        "audio_format": "mp3",
        "audio_mode_used": "local",
    }
