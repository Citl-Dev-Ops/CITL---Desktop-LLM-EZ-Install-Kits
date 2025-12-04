import argparse
import datetime as dt
import sys
from pathlib import Path
import wave

import sounddevice as sd
import numpy as np
import whisper
import requests

# ---- Paths / constants ----

DOCS_DIR = Path.home() / "Documents"
TRANSCRIPT_DIR_NAME = "CITL Transcripts"
OLLAMA_URL = "http://localhost:11434/api/generate"
LLM_MODEL = "mistral:7b-instruct"


# ---- Helpers ----

def choose_microphone() -> int:
    """List input devices and let the user choose one. Returns device index."""
    devices = sd.query_devices()
    input_devices = [
        (i, d) for i, d in enumerate(devices) if d.get("max_input_channels", 0) > 0
    ]

    if not input_devices:
        print("[ERROR] No input (microphone) devices detected.")
        sys.exit(1)

    print("\nAvailable input devices:\n")
    for idx, dev in input_devices:
        name = dev.get("name", f"Device {idx}")
        print(f"  [{idx}] {name}  (max_input_channels={dev.get('max_input_channels')})")

    while True:
        choice = input("\nEnter the device number to use for recording: ").strip()
        if not choice.isdigit():
            print("Please enter a numeric device index.")
            continue
        dev_idx = int(choice)
        if any(dev_idx == i for i, _ in input_devices):
            return dev_idx
        print("That device index is not in the list above; try again.")


def prepare_transcript_folder() -> Path:
    """Ask permission, then create/use Documents\CITL Transcripts."""
    target = DOCS_DIR / TRANSCRIPT_DIR_NAME
    print(f"\nPlanned transcript folder: {target}")
    ans = input("Create/use this folder for audio + transcripts? [Y/n]: ").strip().lower()
    if ans not in ("", "y", "yes"):
        print("User declined; aborting.")
        sys.exit(1)
    target.mkdir(parents=True, exist_ok=True)
    return target


def record_audio(device_index: int, duration_sec: float, samplerate: int = 16000) -> np.ndarray:
    """Record mono audio from selected device for duration_sec seconds."""
    channels = 1
    frames = int(duration_sec * samplerate)
    print(f"\nRecording {duration_sec:.1f} seconds from device {device_index} @ {samplerate} Hz...")
    sd.default.device = device_index
    sd.default.samplerate = samplerate
    sd.default.channels = channels

    audio = sd.rec(frames, samplerate=samplerate, channels=channels, dtype="int16")
    sd.wait()
    print("Recording complete.")
    return audio


def save_wav(audio: np.ndarray, path: Path, samplerate: int = 16000):
    """Save int16 mono numpy array to WAV."""
    path = path.resolve()
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(samplerate)
        wf.writeframes(audio.tobytes())
    print(f"Saved WAV to: {path}")


def transcribe_with_whisper(wav_path: Path, model_size: str = "base") -> str:
    """Run Whisper on the given WAV file and return transcript text."""
    print(f"\nLoading Whisper model '{model_size}' (this may take a bit the first time)...")
    model = whisper.load_model(model_size)
    print(f"Transcribing: {wav_path}")
    result = model.transcribe(str(wav_path), language="en")  # change language if needed
    text = result.get("text", "").strip()
    print("Transcription finished.")
    return text


def summarize_with_citl_llm(transcript: str) -> str:
    """Send transcript to local CITL LLM (mistral via Ollama) for summary."""
    system = (
        "You are CITL Assistant, a college learning and accessibility coach. "
        "You summarize lecture transcripts clearly and concisely for community college students. "
        "Use short paragraphs and bullet points, and highlight key terms."
    )

    prompt = (
        f"Transcript:\n{transcript}\n\n"
        "Task: Summarize this transcript for a student who missed part of the lecture. "
        "Focus on the main ideas, definitions, and any procedures or steps mentioned."
    )

    payload = {
        "model": LLM_MODEL,
        "system": system,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.2},
    }

    print("\nSending transcript to CITL LLM for summarization...")
    r = requests.post(OLLAMA_URL, json=payload, timeout=600)
    r.raise_for_status()
    data = r.json()
    summary = data.get("response", "").strip()
    print("LLM summarization complete.")
    return summary


# ---- Main CLI ----

def main():
    parser = argparse.ArgumentParser(
        description="Record from microphone, save to Documents\\CITL Transcripts, "
                    "transcribe with Whisper, and optionally summarize with CITL LLM."
    )
    parser.add_argument(
        "--minutes",
        type=float,
        default=10.0,
        help="Recording duration in minutes (default: 10).",
    )
    parser.add_argument(
        "--whisper-model",
        type=str,
        default="base",
        help="Whisper model size (tiny | base | small | medium | large). Default: base.",
    )
    parser.add_argument(
        "--no-summary",
        action="store_true",
        help="Skip LLM summarization step.",
    )

    args = parser.parse_args()

    # 1) Choose mic
    dev_idx = choose_microphone()

    # 2) Prepare transcript folder under Documents
    target_dir = prepare_transcript_folder()

    # 3) Build filenames
    ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    wav_path = target_dir / f"lecture_{ts}.wav"
    txt_path = target_dir / f"lecture_{ts}.txt"
    summary_path = target_dir / f"lecture_{ts}.summary.txt"

    # 4) Record audio
    duration_sec = args.minutes * 60.0
    audio = record_audio(dev_idx, duration_sec=duration_sec, samplerate=16000)

    # 5) Save WAV
    save_wav(audio, wav_path, samplerate=16000)

    # 6) Transcribe
    transcript = transcribe_with_whisper(wav_path, model_size=args.whisper_model)

    # 7) Save transcript text
    txt_path.write_text(transcript, encoding="utf-8")
    print(f"Saved transcript to: {txt_path}")

    # 8) Optional summary with CITL LLM
    if args.no-summary:
        print("\nSkipping LLM summarization (per --no-summary).")
        return

    ans = input("\nSummarize this transcript with CITL LLM (mistral via Ollama)? [Y/n]: ").strip().lower()
    if ans not in ("", "y", "yes"):
        print("User chose not to summarize.")
        return

    try:
        summary = summarize_with_citl_llm(transcript)
    except Exception as e:
        print(f"[ERROR] LLM summarization failed: {e}")
        return

    summary_path.write_text(summary, encoding="utf-8")
    print(f"Saved LLM summary to: {summary_path}")


if __name__ == "__main__":
    main()