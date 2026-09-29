"""NovelAI local image-generation backend.

HTTP service that accepts prompts, calls NovelAI's official image API
sequentially (human-like batch), and saves PNGs under outputs/.
"""

from __future__ import annotations

import base64
import io
import json
import os
import random
import time
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field

APP_DIR = Path(__file__).resolve().parent

NOVELAI_URL = "https://image.novelai.net/ai/generate-image"
NOVELAI_UPSCALE_URL = "https://image.novelai.net/ai/upscale"
DEFAULT_MODEL = "nai-diffusion-5-full"
DEFAULT_NEG = (
    "lowres, bad anatomy, bad hands, text, error, missing fingers, "
    "extra digit, fewer digits, cropped, worst quality, low quality, "
    "normal quality, jpeg artifacts, signature, watermark, username, blurry"
)
GAP_SECONDS = 6.0
UPSCALE_SUFFIX = "高清放大版"  # upscaled files are saved as {original_stem}{UPSCALE_SUFFIX}.png


app = FastAPI(title="NovelAI Local Backend", version="1.0.0")


def _load_dotenv() -> None:
    """Load KEY=VALUE lines from a local .env file (if present) without overriding real env vars."""
    env_file = APP_DIR / ".env"
    if not env_file.is_file():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if k and k not in os.environ:
            os.environ[k] = v


def _api_key() -> Optional[str]:
    key = os.environ.get("NOVELAI_API_KEY", "").strip()
    return key or None


_load_dotenv()
OUTPUTS_DIR = Path(os.environ.get("NOVELAI_OUTPUT_DIR", str(APP_DIR / "outputs"))).expanduser()
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)


def _require_key() -> str:
    key = _api_key()
    if not key:
        raise HTTPException(
            status_code=503,
            detail="NOVELAI_API_KEY is not set. Set the env var and restart the service.",
        )
    return key


class GenerateRequest(BaseModel):
    prompt: str
    negative_prompt: Optional[str] = None
    n: int = Field(default=1, ge=1, le=20)
    seed: Optional[int] = None
    width: int = 832
    height: int = 1216
    steps: int = 28
    scale: float = 5.0
    model: str = DEFAULT_MODEL
    label: Optional[str] = None


class BatchJob(BaseModel):
    prompt: str
    negative_prompt: Optional[str] = None
    n: int = Field(default=1, ge=1, le=20)
    seed: Optional[int] = None
    width: int = 832
    height: int = 1216
    steps: int = 28
    scale: float = 5.0
    model: str = DEFAULT_MODEL
    label: Optional[str] = None


class BatchRequest(BaseModel):
    jobs: list[BatchJob]


def _build_body(
    prompt: str,
    negative_prompt: str,
    seed: int,
    width: int,
    height: int,
    steps: int,
    scale: float,
    model: str,
) -> dict[str, Any]:
    return {
        "input": prompt,
        "model": model,
        "action": "generate",
        "parameters": {
            "params_version": 4,
            "width": width,
            "height": height,
            "scale": scale,
            "sampler": "k_euler_ancestral",
            "steps": steps,
            "seed": seed,
            "n_samples": 1,
            "ucPreset": 3,
            "qualityToggle": False,
            "sm": False,
            "sm_dyn": False,
            "dynamic_thresholding": False,
            "controlnet_strength": 1,
            "legacy": False,
            "add_original_image": False,
            "cfg_rescale": 0,
            "noise_schedule": "karras",
            "legacy_v3_extend": False,
            "uncond_scale": 1,
            "negative_prompt": negative_prompt,
            "prompt": prompt,
            "reference_image_multiple": [],
            "reference_information_extracted_multiple": [],
            "reference_strength_multiple": [],
            "extra_noise_seed": seed,
            "v4_prompt": {
                "use_coords": False,
                "use_order": False,
                "caption": {"base_caption": prompt, "char_captions": []},
            },
            "v4_negative_prompt": {
                "use_coords": False,
                "use_order": False,
                "caption": {"base_caption": negative_prompt, "char_captions": []},
            },
        },
    }


def _safe_label(label: Optional[str]) -> str:
    if not label:
        return "img"
    cleaned = "".join(c if c.isalnum() or c in "-_" else "_" for c in label.strip())
    return cleaned[:64] or "img"


def _call_novelai(key: str, body: dict[str, Any]) -> bytes:
    """POST to NovelAI; return zip bytes. Raises HTTPException on failure."""
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Accept": "application/zip",
    }
    try:
        with httpx.Client(timeout=120.0) as client:
            resp = client.post(NOVELAI_URL, headers=headers, json=body)
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail=f"NovelAI request failed: {exc}") from exc

    if resp.status_code == 401:
        raise HTTPException(status_code=401, detail="NovelAI auth failed (401). Check API key.")
    if resp.status_code == 429:
        # Docs forbid client retries on 429
        raise HTTPException(status_code=429, detail="NovelAI rate limited (429). Do not retry.")
    if resp.status_code >= 500:
        raise HTTPException(
            status_code=502,
            detail=f"NovelAI server error ({resp.status_code}): {resp.text[:200]}",
        )
    if resp.status_code not in (200, 201):
        raise HTTPException(
            status_code=502,
            detail=f"NovelAI error ({resp.status_code}): {resp.text[:200]}",
        )
    return resp.content


def _unpack_png(zip_bytes: bytes) -> bytes:
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        names = zf.namelist()
        # Prefer image_0.png; else first .png
        target = None
        for name in names:
            if name.endswith("image_0.png") or name == "image_0.png":
                target = name
                break
        if target is None:
            for name in names:
                if name.lower().endswith(".png"):
                    target = name
                    break
        if target is None:
            raise HTTPException(status_code=502, detail="No PNG found in NovelAI zip response")
        return zf.read(target)


def _write_sidecar(png_path: Path, meta: dict[str, Any]) -> Path:
    side = png_path.with_suffix(".json")
    side.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return side


def _unique_path(directory: Path, filename: str) -> Path:
    """If filename exists, append _2, _3, ... before suffix."""
    candidate = directory / filename
    if not candidate.exists():
        return candidate
    stem = Path(filename).stem
    suffix = Path(filename).suffix
    n = 2
    while True:
        candidate = directory / f"{stem}_{n}{suffix}"
        if not candidate.exists():
            return candidate
        n += 1


def _png_size(png_bytes: bytes) -> tuple[int, int]:
    from PIL import Image

    with Image.open(io.BytesIO(png_bytes)) as im:
        return im.size  # (w, h)


def _resolve_local_image(name_or_path: str) -> Path:
    """Find an image by absolute path, outputs filename, or numeric suffix index."""
    raw = name_or_path.strip()
    p = Path(raw)
    if p.is_file():
        return p.resolve()
    # basename in outputs
    cand = OUTPUTS_DIR / Path(raw).name
    if cand.is_file():
        return cand.resolve()
    # try with .png
    if not raw.lower().endswith(".png"):
        cand = OUTPUTS_DIR / f"{Path(raw).name}.png"
        if cand.is_file():
            return cand.resolve()
    # numeric suffix index: match *_N.png by largest mtime among matches
    if raw.isdigit() or (raw.startswith("_") and raw[1:].isdigit()):
        idx = raw.lstrip("_")
        matches = sorted(OUTPUTS_DIR.glob(f"*_{idx}.png"), key=lambda x: x.stat().st_mtime, reverse=True)
        if matches:
            return matches[0].resolve()
    raise HTTPException(status_code=404, detail=f"Image not found locally: {name_or_path}")


def _generate_one(
    key: str,
    prompt: str,
    negative_prompt: str,
    seed: int,
    width: int,
    height: int,
    steps: int,
    scale: float,
    model: str,
    label: Optional[str],
    index: int,
) -> dict[str, Any]:
    body = _build_body(prompt, negative_prompt, seed, width, height, steps, scale, model)
    zip_bytes = _call_novelai(key, body)
    png = _unpack_png(zip_bytes)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    fname = f"{ts}_{_safe_label(label)}_{index}.png"
    path = _unique_path(OUTPUTS_DIR, fname)
    path.write_bytes(png)
    meta = {
        "path": str(path.resolve()),
        "filename": path.name,
        "seed": seed,
        "index": index,
        "label": label,
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "width": width,
        "height": height,
        "steps": steps,
        "cfg_scale": scale,
        "model": model,
        "created_at": ts,
    }
    _write_sidecar(path, meta)
    return {"path": str(path.resolve()), "seed": seed, "index": index, "filename": path.name}


def _run_generate(req: GenerateRequest | BatchJob) -> dict[str, Any]:
    key = _require_key()
    neg = req.negative_prompt if req.negative_prompt is not None else DEFAULT_NEG
    images: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    n = getattr(req, "n", 1) or 1

    for i in range(n):
        if i > 0:
            time.sleep(GAP_SECONDS)
        seed = req.seed if req.seed is not None else random.randint(0, 2**32 - 1)
        # If caller gave a fixed seed and n>1, still vary for subsequent images
        if req.seed is not None and i > 0:
            seed = random.randint(0, 2**32 - 1)
        try:
            result = _generate_one(
                key=key,
                prompt=req.prompt,
                negative_prompt=neg,
                seed=seed,
                width=req.width,
                height=req.height,
                steps=req.steps,
                scale=req.scale,
                model=req.model,
                label=req.label,
                index=i,
            )
            images.append(result)
        except HTTPException as exc:
            errors.append({"index": i, "status": exc.status_code, "detail": exc.detail})
            # Stop on 401/429; optional continue for 5xx — we stop cleanly for auth/rate
            if exc.status_code in (401, 429, 503):
                break
            # For other errors (502 from 5xx), continue to next if any remain
            continue
        except Exception as exc:  # noqa: BLE001
            errors.append({"index": i, "status": 500, "detail": str(exc)})
            break

    return {"ok": len(errors) == 0, "images": images, "errors": errors}


@app.get("/health")
def health() -> dict[str, Any]:
    return {"ok": True, "has_api_key": _api_key() is not None}


@app.post("/generate")
def generate(req: GenerateRequest) -> dict[str, Any]:
    if not req.prompt or not req.prompt.strip():
        raise HTTPException(status_code=400, detail="prompt is required")
    return _run_generate(req)


@app.post("/generate/batch")
def generate_batch(req: BatchRequest) -> dict[str, Any]:
    if not req.jobs:
        raise HTTPException(status_code=400, detail="jobs list is empty")
    key = _require_key()  # fail fast
    del key  # unused beyond check
    all_images: list[dict[str, Any]] = []
    all_errors: list[dict[str, Any]] = []
    global_index = 0

    for job_idx, job in enumerate(req.jobs):
        if not job.prompt or not job.prompt.strip():
            all_errors.append(
                {"job": job_idx, "index": 0, "status": 400, "detail": "prompt is required"}
            )
            continue
        if global_index > 0:
            time.sleep(GAP_SECONDS)

        # Run this job's n images sequentially; reuse _run_generate but we need
        # to manage the inter-job gap ourselves and flatten results.
        # For first image of job when global_index>0 we already slept.
        # Inside _run_generate there are gaps between n images — that's fine.
        # But _run_generate also sleeps before image 1 of n when i>0 only.
        # Problem: if we call _run_generate for each job, we'd double-sleep
        # between jobs if we also sleep above. So for job 0 we don't sleep
        # before; for later jobs we sleep once before the whole job.
        # Inside job, gaps between its own images are handled by _run_generate.
        # When job_idx>0 we already slept before calling — but _run_generate
        # starts immediately with image 0, which is correct.

        # Offset indices so batch return has unique index fields across jobs
        result = _run_generate(job)
        for img in result["images"]:
            img = dict(img)
            img["index"] = global_index
            img["job"] = job_idx
            all_images.append(img)
            global_index += 1
        for err in result["errors"]:
            err = dict(err)
            err["job"] = job_idx
            all_errors.append(err)
            # Stop entire batch on 401/429
            if err.get("status") in (401, 429, 503):
                return {"ok": False, "images": all_images, "errors": all_errors}
        # After a multi-image job, next job needs a gap — handled by sleep at loop top
        # using global_index > 0. If job produced 0 images due to error that continued,
        # still count that we attempted something: bump so next job still gaps.
        if not result["images"] and result["errors"]:
            global_index += 1  # ensure next iteration sleeps

    return {"ok": len(all_errors) == 0, "images": all_images, "errors": all_errors}


class UpscaleRequest(BaseModel):
    """Locate a local PNG and re-upload to NovelAI /ai/upscale."""

    model_config = ConfigDict(extra="forbid")
    filename: str  # outputs filename, absolute path, or numeric suffix like "0"
    output_name: Optional[str] = None  # default: {stem}{UPSCALE_SUFFIX}.png
    model: str = DEFAULT_MODEL


def _call_upscale(key: str, image_b64: str, model: str) -> bytes:
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Accept": "application/zip",
    }
    body = {"image": image_b64, "model": model}
    try:
        with httpx.Client(timeout=180.0) as client:
            resp = client.post(NOVELAI_UPSCALE_URL, headers=headers, json=body)
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail=f"NovelAI upscale failed: {exc}") from exc

    if resp.status_code == 401:
        raise HTTPException(status_code=401, detail="NovelAI auth failed (401). Check API key.")
    if resp.status_code == 429:
        raise HTTPException(status_code=429, detail="NovelAI rate limited (429). Do not retry.")
    if resp.status_code not in (200, 201):
        raise HTTPException(
            status_code=502,
            detail=f"NovelAI upscale error ({resp.status_code}): {resp.text[:300]}",
        )
    # Response may be zip or raw png
    content_type = (resp.headers.get("content-type") or "").lower()
    data = resp.content
    if data[:2] == b"PK" or "zip" in content_type or "octet" in content_type:
        try:
            return _unpack_png(data)
        except HTTPException:
            return data
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return data
    # try zip anyway
    try:
        return _unpack_png(data)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Unrecognized upscale response: {exc}") from exc


@app.post("/upscale")
def upscale(req: UpscaleRequest) -> dict[str, Any]:
    key = _require_key()
    src = _resolve_local_image(req.filename)
    stem = src.stem
    # strip a prior suffix if re-upscaling
    if stem.endswith(UPSCALE_SUFFIX):
        stem = stem[: -len(UPSCALE_SUFFIX)].rstrip("_")
    out_name = req.output_name or f"{stem}{UPSCALE_SUFFIX}.png"
    if Path(out_name).name != out_name or out_name in (".", ".."):
        raise HTTPException(status_code=400, detail="output_name must be a filename, not a path")
    if not out_name.lower().endswith(".png"):
        out_name += ".png"

    png_bytes = src.read_bytes()
    width, height = _png_size(png_bytes)
    # NovelAI expects raw base64 without data: URL prefix
    b64 = base64.b64encode(png_bytes).decode("ascii")
    out_png = _call_upscale(key, b64, req.model)
    result_width, result_height = _png_size(out_png)

    out_path = _unique_path(OUTPUTS_DIR, out_name)
    out_path.write_bytes(out_png)
    meta = {
        "source": str(src.resolve()),
        "path": str(out_path.resolve()),
        "filename": out_path.name,
        "model": req.model,
        "source_width": width,
        "source_height": height,
        "result_width": result_width,
        "result_height": result_height,
        "created_at": datetime.now().strftime("%Y%m%d_%H%M%S"),
    }
    _write_sidecar(out_path, meta)
    return {"ok": True, "source": str(src.resolve()), "image": meta}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=os.environ.get("NOVELAI_HOST", "127.0.0.1"),
        port=int(os.environ.get("NOVELAI_PORT", "8787")),
    )
