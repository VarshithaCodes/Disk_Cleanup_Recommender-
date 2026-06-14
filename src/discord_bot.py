"""
Discord Bot Module — Human Approval Gate
Sends cleanup recommendations to a Discord channel and waits for a
human to reply with !approve or !reject before any file is moved/deleted.

This module is OPTIONAL. The Streamlit app's built-in Approve/Reject
buttons (Option 1 from the design doc) work without Discord and are
the default for the MVP. This bot implements Option 2 for users who
want the Discord-based approval flow.

Usage:
    python -m src.discord_bot

Requires environment variables:
    DISCORD_BOT_TOKEN
    DISCORD_CHANNEL_ID
"""

import os
import json
import asyncio

import discord

from .scanner import scan_directory
from .classifier import classify_file
from .deleter import move_to_recycle
from .report_generator import generate_csv_report, generate_markdown_report

DISCORD_BOT_TOKEN = os.environ.get("DISCORD_BOT_TOKEN", "")
DISCORD_CHANNEL_ID = int(os.environ.get("DISCORD_CHANNEL_ID", "0"))
SCAN_PATH = os.environ.get("SCAN_PATH", "data/sample_disk")
RECYCLE_PATH = os.environ.get("RECYCLE_PATH", "deleted")

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)


async def ask_approval(channel, file_info, classification_result):
    """
    Post a recommendation message and wait for !approve / !reject
    from any user in the channel. Returns True (approve) or False (reject).
    """
    msg = (
        f"**Cleanup Recommendation**\n"
        f"File: `{file_info['path']}`\n"
        f"Size: {file_info['size_mb']} MB\n"
        f"Age: {file_info['age_days']} days\n"
        f"AI says: **{classification_result['classification']}**\n"
        f"Reason: {classification_result['reason']}\n\n"
        f"Reply `!approve` to move this file to recycle, or `!reject` to keep it."
    )
    await channel.send(msg)

    def check(m):
        return (
            m.channel.id == channel.id
            and m.content.strip().lower() in ("!approve", "!reject")
        )

    try:
        reply = await client.wait_for("message", check=check, timeout=120)
        return reply.content.strip().lower() == "!approve"
    except asyncio.TimeoutError:
        await channel.send(f"No response in time for `{file_info['path']}`. Keeping file (default = reject).")
        return False


async def run_cleanup_flow():
    channel = client.get_channel(DISCORD_CHANNEL_ID)
    if channel is None:
        print("ERROR: Could not find Discord channel. Check DISCORD_CHANNEL_ID.")
        return

    await channel.send(f"🔍 Scanning `{SCAN_PATH}` ...")
    files = scan_directory(SCAN_PATH)
    results = []

    for file_info in files:
        classification = classify_file(file_info)
        row = {
            "path": file_info["path"],
            "size_mb": file_info["size_mb"],
            "age_days": file_info["age_days"],
            "classification": classification["classification"],
            "reason": classification["reason"],
            "action": "NONE",
            "moved_to": "",
        }

        if classification["classification"] == "SAFE_DELETE":
            approved = await ask_approval(channel, file_info, classification)
            if approved:
                new_path = move_to_recycle(file_info["path"], RECYCLE_PATH, source_root=SCAN_PATH)
                row["action"] = "MOVED_TO_RECYCLE"
                row["moved_to"] = new_path
                await channel.send(f"✅ Moved `{file_info['path']}` to recycle folder.")
            else:
                await channel.send(f"❌ Kept `{file_info['path']}`.")
        elif classification["classification"] == "REVIEW":
            await channel.send(
                f"⚠️ `{file_info['path']}` flagged as REVIEW: {classification['reason']} (no action taken)"
            )
        # KEEP -> no message needed, but still included in report

        results.append(row)

    csv_path = generate_csv_report(results)
    md_path = generate_markdown_report(results)

    await channel.send(f"📄 Report generated: `{csv_path}` and `{md_path}`")
    print("Cleanup flow complete.")


@client.event
async def on_ready():
    print(f"Logged in as {client.user}")
    await run_cleanup_flow()
    await client.close()


if __name__ == "__main__":
    if not DISCORD_BOT_TOKEN or not DISCORD_CHANNEL_ID:
        print("Set DISCORD_BOT_TOKEN and DISCORD_CHANNEL_ID environment variables.")
    else:
        client.run(DISCORD_BOT_TOKEN)
