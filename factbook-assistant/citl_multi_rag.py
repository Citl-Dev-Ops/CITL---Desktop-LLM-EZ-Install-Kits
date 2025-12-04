import argparse
import json
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import requests

# All files are in the Factbook-Assistant folder
CORPUS_FILES: Dict[str, Path] = {
    "factbook": Path("factbook_embeddings.json"),
    "law": Path("law_embeddings.json"),
    "nursing": Path("nursing_embeddings.json"),
    "dictionary": Path("dictionary_embeddings.json"),
}

EMBED_MODEL = "nomic-embed-text"
EMBED_URL = "http://localhost:11434/api/embed"
LLM_MODEL = "mistral:7b-instruct"
GEN_URL = "http://localhost:11434/api/generate"


def embed(text: str) -> np.ndarray:
    """
    Call Ollama /api/embed and return ONE normalized embedding vector.
    """
    r = requests.post(EMBED_URL, json={"model": EMBED_MODEL, "input": text})
    r.raise_for_status()
    out = r.json()

    vec = None
    if isinstance(out, dict):
        vec = out.get("embedding")
        if vec is None:
            embs = out.get("embeddings")
            if isinstance(embs, list) and embs:
                vec = embs[0]
    else:
        raise RuntimeError(f"Unexpected embed response type: {type(out)}: {out}")

    if vec is None:
        raise RuntimeError(f"Could not find 'embedding' in embed response: {out}")

    v = np.asarray(vec, dtype=np.float32)
    v /= (np.linalg.norm(v) + 1e-8)
    return v


def load_corpus(name: str) -> Tuple[np.ndarray, List[dict]]:
    """
    Load embeddings + chunks for the given corpus name.
    """
    path = CORPUS_FILES[name]
    if not path.exists():
        raise FileNotFoundError(f"Corpus file not found for '{name}': {path}")

    data = json.loads(path.read_text(encoding="utf-8"))
    emb = np.asarray(data["embeddings"], dtype=np.float32)
    chunks = data["chunks"]

    emb /= (np.linalg.norm(emb, axis=1, keepdims=True) + 1e-8)

    print(f"[INFO] Loaded {len(chunks)} chunks from {name} ({path})")
    return emb, chunks


def top_k(emb: np.ndarray, chunks: List[dict], qvec: np.ndarray, k: int) -> List[str]:
    """
    Return text for top-k most similar chunks.
    """
    sims = emb @ qvec
    if len(sims) == 0:
        return []
    k = min(k, len(sims))
    idx = np.argpartition(-sims, k - 1)[:k]
    idx = idx[np.argsort(-sims[idx])]
    return [chunks[int(i)]["text"] for i in idx]


def generate_answer(question: str, context: str) -> str:
    """
    Call Ollama /api/generate with Mistral and the provided context.
    """
    system_prompt = (
        "You are CITL Assistant, a college learning and accessibility coach.\n"
        "You MUST answer ONLY using facts contained in the context below.\n"
        "If the answer is not clearly present in the context, say you do not know.\n"
        "Keep answers concise and easy to read for community college students.\n"
        "Use short paragraphs or bullet points. Do not invent citations or sources.\n"
    )

    payload = {
        "model": LLM_MODEL,
        "system": system_prompt,
        "prompt": f"Context:\n{context}\n\nQuestion: {question}\nAnswer:",
        "stream": False,
        "options": {"temperature": 0.1},
    }

    r = requests.post(GEN_URL, json=payload, timeout=600)
    r.raise_for_status()
    data = r.json()
    answer = data.get("response", "")
    return answer.strip()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="CITL multi-corpus RAG over Factbook, Law, Nursing, Dictionary."
    )
    parser.add_argument(
        "--source",
        choices=["factbook", "law", "nursing", "dictionary", "all"],
        default="factbook",
        help="Which corpus to use (or 'all' to combine).",
    )
    parser.add_argument(
        "-k",
        "--topk",
        type=int,
        default=5,
        help="Number of chunks per corpus to retrieve.",
    )
    parser.add_argument(
        "--maxctx",
        type=int,
        default=4000,
        help="Maximum characters of context to send to the LLM.",
    )
    parser.add_argument("question", help="User question.")
    args = parser.parse_args()

    if args.source == "all":
        corpora = ["factbook", "law", "nursing", "dictionary"]
    else:
        corpora = [args.source]

    print(f"[INFO] Using corpora: {', '.join(corpora)}")

    qvec = embed(args.question)

    ctx_parts: List[str] = []

    for name in corpora:
        try:
            emb, chunks = load_corpus(name)
        except FileNotFoundError as e:
            print(f"[ERROR] {e}")
            continue

        hits = top_k(emb, chunks, qvec, args.topk)
        if not hits:
            continue

        header = f"Source: {name.upper()}"
        ctx_parts.append(header)
        ctx_parts.append("---")
        ctx_parts.append("\n---\n".join(hits))

    if not ctx_parts:
        print("I could not find any relevant context in the selected corpus/corpora.")
        return

    full_ctx = "\n\n".join(ctx_parts)
    full_ctx = full_ctx[: args.maxctx]

    answer = generate_answer(args.question, full_ctx)
    print(answer)


if __name__ == "__main__":
    main()