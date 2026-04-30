#!/usr/bin/env python3
"""Generate a LeeScoop cover image through ComfyUI and save it under public/covers."""
from __future__ import annotations

import argparse
import json
import random
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

LEE_STYLE = "cel shaded, thick outlines, cute, cartoon, sharp silhouette, graphic shadows, true black, clean simple shapes, high contrast, bold readable design, polished mascot/logo illustration style, modern vector-like finish, tropical coastal energy, playful but clean, Florida-inspired color palette, using #07506F, #197894, #4FA7BC, #8BD2DE, #D94B32, #F28B42, #F7DE69, #F8F3E8, #063A52, #DDEEF1"
NEGATIVE = "nsfw, muddy colors, low contrast, thin outlines, bad anatomy, extra limbs, blurry, text, watermark, dull palette, overly realistic rendering"


def request_json(base: str, path: str, payload: dict | None = None, timeout: int = 30):
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        base.rstrip("/") + path,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST" if payload is not None else "GET",
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def build_workflow(prompt: str, negative: str, width: int, height: int, seed: int, prefix: str):
    return {
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": "perfectdeliberate_v90.safetensors"},
        },
        "2": {
            "class_type": "LoraLoader",
            "inputs": {
                "model": ["1", 0],
                "clip": ["1", 1],
                "lora_name": "Detail_Tweaker_Illustrious_BSY_V3.safetensors",
                "strength_model": 0.70,
                "strength_clip": 0.70,
            },
        },
        "3": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["2", 1]}},
        "4": {"class_type": "CLIPTextEncode", "inputs": {"text": negative, "clip": ["2", 1]}},
        "5": {
            "class_type": "EmptyLatentImage",
            "inputs": {"width": width, "height": height, "batch_size": 1},
        },
        "6": {
            "class_type": "KSampler",
            "inputs": {
                "model": ["2", 0],
                "positive": ["3", 0],
                "negative": ["4", 0],
                "latent_image": ["5", 0],
                "seed": seed,
                "steps": 30,
                "cfg": 8.0,
                "sampler_name": "dpmpp_sde",
                "scheduler": "karras",
                "denoise": 1.0,
            },
        },
        "7": {"class_type": "VAEDecode", "inputs": {"samples": ["6", 0], "vae": ["1", 2]}},
        "8": {"class_type": "SaveImage", "inputs": {"images": ["7", 0], "filename_prefix": prefix}},
    }


def find_saved_image(history: dict):
    outputs = (history or {}).get("outputs", {})
    for node in outputs.values():
        images = node.get("images") or []
        if images:
            return images[0]
    raise RuntimeError(f"No image outputs found in ComfyUI history: {history}")


def download_view(base: str, image_info: dict, out_path: Path):
    params = urllib.parse.urlencode(
        {
            "filename": image_info["filename"],
            "subfolder": image_info.get("subfolder", ""),
            "type": image_info.get("type", "output"),
        }
    )
    with urllib.request.urlopen(base.rstrip("/") + "/view?" + params, timeout=60) as response:
        out_path.write_bytes(response.read())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--subject", required=True, help="Short unique subject, without style block")
    parser.add_argument("--slug", required=True)
    parser.add_argument("--base", default="http://192.168.12.249:8000")
    parser.add_argument("--width", type=int, default=1216)
    parser.add_argument("--height", type=int, default=704)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--timeout", type=int, default=240)
    args = parser.parse_args()

    seed = args.seed or random.randint(1, 2**63 - 1)
    prompt = f"({args.subject}:1.3), {LEE_STYLE}"
    prefix = f"leescoop/{args.slug}"
    workflow = build_workflow(prompt, NEGATIVE, args.width, args.height, seed, prefix)
    client_id = f"leescoop-{args.slug}-{seed}"
    queued = request_json(args.base, "/prompt", {"prompt": workflow, "client_id": client_id}, timeout=30)
    prompt_id = queued["prompt_id"]

    deadline = time.time() + args.timeout
    while time.time() < deadline:
        history = request_json(args.base, f"/history/{prompt_id}", timeout=30)
        if prompt_id in history:
            image_info = find_saved_image(history[prompt_id])
            out_path = ROOT / "public" / "covers" / f"{args.slug}.png"
            out_path.parent.mkdir(parents=True, exist_ok=True)
            download_view(args.base, image_info, out_path)
            print(json.dumps({"ok": True, "path": str(out_path), "seed": seed, "prompt": prompt, "negative": NEGATIVE, "image_info": image_info}, indent=2))
            return
        time.sleep(2)
    raise TimeoutError(f"Timed out waiting for ComfyUI prompt {prompt_id}")


if __name__ == "__main__":
    main()
