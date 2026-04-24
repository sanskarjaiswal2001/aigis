#!/usr/bin/env python3
"""
Aigis Demo Script
-----------------
Automated demo for OBS recording. Plays TTS narration, types commands with a
typewriter effect, and automates browser navigation via Playwright — fully hands-free.

Usage:
    cd /path/to/Aigis
    uv run python demo/demo.py              # full demo
    uv run python demo/demo.py --dry-run    # print steps only, no audio/exec/browser
    uv run python demo/demo.py --dry-audio  # audio + browser, CLI commands skipped

One-time browser setup:
    uv run playwright install chromium
"""

import asyncio
import os
import subprocess
import sys
import time
import shutil
import urllib.request
from pathlib import Path

# Suppress sentence-transformers / HuggingFace noise (progress bars, load
# reports, unauthenticated-token warnings) in all child processes.
os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
os.environ.setdefault("HF_HUB_DISABLE_IMPLICIT_TOKEN", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

# ---------------------------------------------------------------------------
# Tuning constants
# ---------------------------------------------------------------------------
TYPEWRITER_DELAY  = 0.04   # seconds per character
CMD_PRE_PAUSE     = 0.6    # pause before typing starts
CMD_POST_PAUSE    = 2.0    # pause after command output settles
SERVER_PORT       = 8080
SERVER_URL        = f"http://localhost:{SERVER_PORT}"

TTS_VOICE         = "en-US-AvaMultilingualNeural"
TTS_RATE          = "+0%"
MPV_BIN           = "/usr/bin/mpv"

# ---------------------------------------------------------------------------
# ANSI helpers
# ---------------------------------------------------------------------------
RESET  = "\033[0m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
CYAN   = "\033[36m"
GREEN  = "\033[32m"
YELLOW = "\033[33m"

def _print(text: str, style: str = "") -> None:
    print(f"{style}{text}{RESET}", flush=True)

def banner(text: str) -> None:
    w = 60
    _print("\n" + "─" * w, CYAN)
    _print(f"  {text}", BOLD + CYAN)
    _print("─" * w + "\n", CYAN)

def scene_label(label: str) -> None:
    _print(f"\n{'━' * 60}", YELLOW)
    _print(f"  {label}", BOLD + YELLOW)
    _print(f"{'━' * 60}\n", YELLOW)

def step_label(text: str) -> None:
    _print(f"  {DIM}▸ {text}{RESET}", "")

def transcript(text: str) -> None:
    _print(f"\n  {DIM}{text}{RESET}\n", "")

# ---------------------------------------------------------------------------
# TTS
# ---------------------------------------------------------------------------
def _tts_text(text: str) -> str:
    return text.replace("Aigis", "ages")

async def _generate_tts(text: str, output_path: Path) -> None:
    import edge_tts
    communicate = edge_tts.Communicate(_tts_text(text), TTS_VOICE, rate=TTS_RATE)
    await communicate.save(str(output_path))

async def pregenerate_all(narrations: list[str], cache_dir: Path) -> dict[int, Path]:
    import edge_tts  # noqa: F401
    cache_dir.mkdir(parents=True, exist_ok=True)
    entries: dict[int, tuple[Path, asyncio.coroutines]] = {}
    for i, text in enumerate(narrations):
        out = cache_dir / f"tts_{i:03d}.mp3"
        entries[i] = (out, _generate_tts(text, out))
    _print(f"  Pre-generating {len(entries)} TTS audio files...", DIM)
    await asyncio.gather(*(coro for _, coro in entries.values()))
    _print("  Done.\n", DIM)
    return {i: path for i, (path, _) in entries.items()}

async def play_async(path: Path, no_audio: bool) -> None:
    """Non-blocking audio playback — awaitable so it can run alongside Playwright."""
    if no_audio or not path.exists():
        return
    proc = await asyncio.create_subprocess_exec(
        MPV_BIN, "--really-quiet", "--no-video", str(path),
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
    )
    await proc.wait()

def play_sync(path: Path, no_audio: bool) -> None:
    """Blocking audio playback for sequential CLI scene."""
    if no_audio or not path.exists():
        return
    subprocess.run([MPV_BIN, "--really-quiet", "--no-video", str(path)], check=False)

# ---------------------------------------------------------------------------
# CLI typewriter
# ---------------------------------------------------------------------------
def typewrite_and_run(cmd: str, no_exec: bool) -> None:
    time.sleep(CMD_PRE_PAUSE)
    sys.stdout.write(f"{GREEN}$ {RESET}")
    sys.stdout.flush()
    for ch in cmd:
        sys.stdout.write(ch)
        sys.stdout.flush()
        time.sleep(TYPEWRITER_DELAY)
    sys.stdout.write("\n")
    sys.stdout.flush()
    if not no_exec:
        subprocess.run(cmd, shell=True, check=False, stderr=subprocess.DEVNULL)
    time.sleep(CMD_POST_PAUSE)

# ---------------------------------------------------------------------------
# Server lifecycle
# ---------------------------------------------------------------------------
async def start_server() -> asyncio.subprocess.Process:
    return await asyncio.create_subprocess_exec(
        "uv", "run", "aigis", "serve",
        "--host", "127.0.0.1", "--port", str(SERVER_PORT),
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
    )

async def wait_for_server(timeout_s: int = 40) -> bool:
    _print("  Waiting for server...", DIM)
    for _ in range(timeout_s * 4):
        try:
            urllib.request.urlopen(f"{SERVER_URL}/api/runs", timeout=1)
            _print("  Server ready.\n", DIM)
            return True
        except Exception:
            await asyncio.sleep(0.25)
    return False

# ---------------------------------------------------------------------------
# Narration text
# ---------------------------------------------------------------------------
NARRATIONS = [
    # Scene 1 — CLI (indices 0–3)
    "Aigis can ingest any markdown, plain text, or PDF runbook into its knowledge base — grounding AI suggestions in your own operational docs.",
    "As you can see, we have six runbooks covering the most common infrastructure failure modes: backups, disk, load, containers, network, and general Linux troubleshooting.",
    "Aigis chunks each document, embeds it locally using a sentence-transformer model, and caches the embeddings. It only re-ingests files that have changed — so subsequent runs are instant.",
    "Those runbooks are now embedded. When Aigis detects an issue at runtime, it semantically searches this knowledge base and injects the most relevant excerpts directly into the AI prompt.",

    # Scene 2 — Web UI (indices 4–12)
    "The Aigis web dashboard gives teams a real-time view of infrastructure health — showing run history, live severity, and AI-generated analysis all in one place.",
    "The run history table shows every scan with its overall severity. Let's open the most recent run to see what Aigis found.",
    "Each run report shows the full check breakdown — which domains passed, which failed, and the AI explanation of what went wrong and why.",
    "Aigis also surfaces suggested remediation actions: the exact script to run, the parameters it needs, and the risk level — ready for operator approval.",
    "Let's trigger a live scan now and watch Aigis collect signals in real time.",
    "Within seconds, Aigis has collected from all five domains, evaluated results against configured thresholds, and produced a fresh structured report.",
    "The audit log records every action taken — who approved it, when, and the full output — giving teams complete accountability without slowing them down.",
    "The Settings page has six sections. Target switches between local and any configured SSH host. LLM Analysis lets you toggle AI reasoning and choose the Claude model. Collectors enables or disables each data source and configures options like the restic repo path and disk mount points. Rules and Thresholds dial in the warn and critical levels for disk usage and CPU load. Scheduled Runs shows the systemd timer commands for fully automated scanning. And Advanced controls auto-fix confidence, run history depth, and the knowledge base.",
    "That's Aigis: deterministic checks as the safety net, AI reasoning as the analyst, and human approval as the final gate — built for teams that can't afford surprises.",
]

# ---------------------------------------------------------------------------
# Scene 1 — CLI
# ---------------------------------------------------------------------------
def scene1_cli(audio_files: dict[int, Path], no_audio: bool, no_exec: bool) -> None:
    transcript(NARRATIONS[0])
    play_sync(audio_files.get(0, Path()), no_audio)
    time.sleep(0.3)

    typewrite_and_run("ls knowledge_base/", no_exec)

    transcript(NARRATIONS[1])
    play_sync(audio_files.get(1, Path()), no_audio)

    typewrite_and_run("aigis --ingest knowledge_base/", no_exec)

    transcript(NARRATIONS[2])
    play_sync(audio_files.get(2, Path()), no_audio)
    time.sleep(0.5)

    transcript(NARRATIONS[3])
    play_sync(audio_files.get(3, Path()), no_audio)

# ---------------------------------------------------------------------------
# Scene 2 — Browser (Playwright)
# ---------------------------------------------------------------------------
async def scene2_browser(audio_files: dict[int, Path], no_audio: bool) -> None:
    server_proc = None
    try:
        server_proc = await start_server()
        if not await wait_for_server():
            _print("  ERROR: server did not start in time.", BOLD + YELLOW)
            return

        from playwright.async_api import async_playwright

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(
                headless=False,
                args=["--disable-infobars"],
            )
            ctx = await browser.new_context(viewport=None)
            page = await ctx.new_page()

            # --- Dashboard ---
            await page.goto(SERVER_URL)
            await page.wait_for_load_state("load")
            await asyncio.sleep(1.5)

            transcript(NARRATIONS[4])
            await play_async(audio_files.get(4, Path()), no_audio)
            await asyncio.sleep(2.0)

            # --- Runs list ---
            await page.get_by_role("link", name="Runs").click()
            await page.wait_for_load_state("load")
            await asyncio.sleep(1.0)

            transcript(NARRATIONS[5])
            await play_async(audio_files.get(5, Path()), no_audio)
            await asyncio.sleep(1.0)

            # --- Run detail: click arrow on first row ---
            await page.locator("tbody tr").first.get_by_role("link").click()
            await page.wait_for_load_state("load")
            await asyncio.sleep(1.0)

            transcript(NARRATIONS[6])
            await play_async(audio_files.get(6, Path()), no_audio)
            await asyncio.sleep(1.0)

            # Scroll to suggested actions
            await page.evaluate("window.scrollTo({top: document.body.scrollHeight, behavior: 'smooth'})")
            await asyncio.sleep(1.0)

            transcript(NARRATIONS[7])
            await play_async(audio_files.get(7, Path()), no_audio)
            await asyncio.sleep(1.0)

            # --- Back to dashboard ---
            await page.get_by_role("link", name="Dashboard").click()
            await page.wait_for_load_state("load")
            await asyncio.sleep(1.0)

            # Scroll back to top
            await page.evaluate("window.scrollTo({top: 0, behavior: 'smooth'})")
            await asyncio.sleep(0.5)

            transcript(NARRATIONS[8])
            await play_async(audio_files.get(8, Path()), no_audio)
            await asyncio.sleep(0.5)

            # Ensure scan runs locally (avoid SSH timeout on homelab target)
            original_target = await page.evaluate(
                "fetch('/api/settings').then(r=>r.json()).then(d=>d.target)"
            )
            if original_target != "local":
                await page.evaluate(
                    "fetch('/api/settings',{method:'PATCH',"
                    "headers:{'Content-Type':'application/json'},"
                    "body:JSON.stringify({target:'local'})}).then(r=>r.json())"
                )
                await asyncio.sleep(0.5)

            # --- Run Scan ---
            await page.get_by_role("button", name="Run Scan").click()

            # Wait for scan to finish — close button only appears when done=true
            # (works for both "Scan complete" and "Exit N" outcomes)
            close_btn = page.locator("div.fixed").get_by_role("button")
            await close_btn.wait_for(timeout=120_000)
            await asyncio.sleep(1.0)

            transcript(NARRATIONS[9])
            await play_async(audio_files.get(9, Path()), no_audio)
            await asyncio.sleep(1.0)

            # Close the scan modal
            await close_btn.click()
            await asyncio.sleep(1.5)

            # Restore original target
            if original_target != "local":
                await page.evaluate(
                    f"fetch('/api/settings',{{method:'PATCH',"
                    f"headers:{{'Content-Type':'application/json'}},"
                    f"body:JSON.stringify({{target:'{original_target}'}})}})"
                )

            # --- Audit Log ---
            await page.get_by_role("link", name="Audit Log").click()
            await page.wait_for_load_state("load")
            await asyncio.sleep(1.0)

            transcript(NARRATIONS[10])
            await play_async(audio_files.get(10, Path()), no_audio)
            await asyncio.sleep(1.5)

            # --- Settings ---
            await page.get_by_role("link", name="Settings").click()
            await page.wait_for_load_state("load")
            await asyncio.sleep(1.5)

            transcript(NARRATIONS[11])

            await play_async(audio_files.get(11, Path()), no_audio)
            await asyncio.sleep(1.0)

            # --- Outro ---
            transcript(NARRATIONS[12])
            await play_async(audio_files.get(12, Path()), no_audio)
            await asyncio.sleep(2.0)

            await browser.close()

    finally:
        if server_proc and server_proc.returncode is None:
            server_proc.terminate()
            try:
                await asyncio.wait_for(server_proc.wait(), timeout=5)
            except asyncio.TimeoutError:
                server_proc.kill()

async def scene2_dry_run() -> None:
    """Print-only version of scene 2 for --dry-run mode."""
    for i in range(4, len(NARRATIONS)):
        _print(f"\n  {DIM}{NARRATIONS[i]}{RESET}\n", "")

# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------
async def run_demo(dry_run: bool, dry_audio: bool) -> None:
    no_audio = dry_run
    no_exec  = dry_run or dry_audio

    if not no_audio:
        try:
            import edge_tts  # noqa: F401
        except ImportError:
            _print("edge-tts not installed. Run: uv pip install edge-tts[demo]", BOLD + YELLOW)
            sys.exit(1)

    cache_dir = Path("demo/.tts_cache")
    audio_files: dict[int, Path] = {}
    if not no_audio:
        audio_files = await pregenerate_all(NARRATIONS, cache_dir)

    # Scene 1 runs synchronously (sequential CLI steps)
    scene1_cli(audio_files, no_audio, no_exec)

    # Scene 2
    if dry_run:
        await scene2_dry_run()
    else:
        await scene2_browser(audio_files, no_audio)

    banner("Demo complete.")

    if not no_audio and cache_dir.exists():
        shutil.rmtree(cache_dir)


def main() -> None:
    dry_run   = "--dry-run"   in sys.argv
    dry_audio = "--dry-audio" in sys.argv
    if dry_run:
        _print("\n[DRY RUN — no audio, no commands, no browser]\n", BOLD + YELLOW)
    elif dry_audio:
        _print("\n[DRY AUDIO — audio + browser, CLI commands skipped]\n", BOLD + YELLOW)
    asyncio.run(run_demo(dry_run, dry_audio))


if __name__ == "__main__":
    main()
