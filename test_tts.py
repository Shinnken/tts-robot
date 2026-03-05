import subprocess
import os
import io
import wave
import shutil
from datetime import datetime
from piper.voice import PiperVoice
from get_model import ensure_language_model

# sox -t wav - -t wav - pitch -800 speed 0.9 reverb 50 75
SOX_CMD_1 = ["sox", "-t", "wav", "-", "-t", "wav", "-", "flanger", "10", "2", "reverb", "25", "50"] # High-Pitched Droid (Pitch & Overdrive)
SOX_CMD_2 = ["sox", "-t", "wav", "-", "-t", "wav", "-", "pitch", "-400", "speed", "0.9", "reverb", "50", "75"] # Deep Ominous Robot (Pitch & Reverb)

MODEL_PATH = ensure_language_model("pl")  # Ensure Polish model is downloaded


def synthesize_wav_bytes(voice: PiperVoice, text: str) -> bytes:
    """Generate WAV bytes for the provided text."""
    wav_buffer = io.BytesIO()
    with wave.open(wav_buffer, "wb") as wav_file:
        voice.synthesize_wav(text, wav_file)

    wav_buffer.seek(0)
    return wav_buffer.read()


def build_player_commands() -> list[list[str]]:
    """Build a list of available player commands in preferred order."""
    commands: list[list[str]] = []
    if shutil.which("aplay"):
        commands.append(["aplay"])
    if shutil.which("play"):
        commands.append(["play", "-q", "-t", "wav", "-"])
    if shutil.which("ffplay"):
        commands.append(["ffplay", "-autoexit", "-nodisp", "-loglevel", "error", "-i", "-"])
    return commands


def apply_sox_effects(wav_bytes: bytes, sox_cmd: list[str]) -> bytes:
    """Apply SoX effects and return transformed WAV bytes.

    If SoX fails, return the original bytes and continue with plain playback.
    """
    result = subprocess.run(
        sox_cmd,
        input=wav_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        stderr_text = result.stderr.decode("utf-8", errors="replace").strip()
        print(f"Warning: SoX effect processing failed ({result.returncode}).")
        if stderr_text:
            print(f"  SoX: {stderr_text}")
        print("Falling back to unprocessed audio.")
        return wav_bytes
    return result.stdout


def save_failed_playback_wav(wav_bytes: bytes) -> str:
    """Save audio bytes to disk when playback is not possible."""
    filename = f"tts-output-{datetime.now().strftime('%Y%m%d-%H%M%S')}.wav"
    with open(filename, "wb") as output_file:
        output_file.write(wav_bytes)
    return os.path.abspath(filename)


def play_wav_bytes(wav_bytes: bytes) -> bool:
    """Play WAV bytes and return True on success, False on failure."""
    processed_wav = apply_sox_effects(wav_bytes, SOX_CMD_1)
    errors: list[str] = []

    for command in build_player_commands():
        try:
            result = subprocess.run(
                command,
                input=processed_wav,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                check=False,
            )
        except FileNotFoundError:
            continue

        if result.returncode == 0:
            return True

        stderr_text = result.stderr.decode("utf-8", errors="replace").strip()
        errors.append(f"{' '.join(command)} -> exit {result.returncode}: {stderr_text}")

    print("Error: Playback failed with all available players.")
    for error_line in errors:
        print(f"  {error_line}")

    saved_path = save_failed_playback_wav(processed_wav)
    print(f"Saved generated audio to: {saved_path}")
    print("Try playing it manually to verify your system audio output.")
    return False


def main() -> None:
    print("Loading voice model...")
    voice = PiperVoice.load(MODEL_PATH)
    print("Model loaded. Type text to synthesize (or 'exit' to quit).")

    while True:
        try:
            user_input = input("> ")
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            break

        text = user_input.strip()
        if not text:
            continue

        if text.lower() in {"exit", "quit"}:
            print("Goodbye.")
            break

        print("Generating and playing audio...")
        wav_bytes = synthesize_wav_bytes(voice, text)
        if play_wav_bytes(wav_bytes):
            print("Playback finished. Type another line or 'exit'.")
        else:
            print("Playback failed. Type another line or 'exit'.")


if __name__ == "__main__":
    main()