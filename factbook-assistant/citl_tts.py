import argparse
import sys

import pyttsx3


def main():
    parser = argparse.ArgumentParser(
        description="CITL text-to-speech helper (local, using pyttsx3)."
    )
    parser.add_argument(
        "text",
        nargs="*",
        help="Text to read aloud. If omitted, text is read from standard input.",
    )
    parser.add_argument(
        "--rate",
        type=int,
        default=180,
        help="Speech rate (words per minute, default: 180).",
    )
    parser.add_argument(
        "--volume",
        type=float,
        default=1.0,
        help="Volume (0.0 to 1.0, default: 1.0).",
    )

    args = parser.parse_args()

    if args.text:
        text = " ".join(args.text)
    else:
        # Read from stdin (e.g., piped from citl_multi_rag)
        text = sys.stdin.read()

    text = text.strip()
    if not text:
        print("[WARN] No text provided to TTS.")
        return

    engine = pyttsx3.init()
    engine.setProperty("rate", args.rate)
    engine.setProperty("volume", args.volume)

    # You could list/change voices here if you want:
    # voices = engine.getProperty("voices")
    # for i, v in enumerate(voices):
    #     print(i, v.name)
    # engine.setProperty("voice", voices[0].id)

    engine.say(text)
    engine.runAndWait()


if __name__ == "__main__":
    main()