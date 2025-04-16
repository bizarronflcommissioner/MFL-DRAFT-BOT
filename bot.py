import discord
import asyncio
import aiohttp
import xml.etree.ElementTree as ET
from datetime import datetime
from dotenv import load_dotenv
import os

load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
LEAGUE_ID = os.getenv("LEAGUE_ID")
SEASON_YEAR = 2025
DRAFT_CHANNEL_ID = 1359911725327056922
CHECK_INTERVAL = 30  # seconds

intents = discord.Intents.default()
client = discord.Client(intents=intents)

franchise_names = {}
announced_picks = set()
draft_started = False
last_announced_pick = -1

async def load_franchises():
    url = f"https://www43.myfantasyleague.com/{SEASON_YEAR}/export?TYPE=league&L={LEAGUE_ID}&JSON=1"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            data = await resp.json()
            for f in data["league"]["franchises"]["franchise"]:
                franchise_names[f["id"]] = f["name"]
    print(f"Loaded {len(franchise_names)} franchises.")

async def fetch_draft_data():
    url = f"https://www43.myfantasyleague.com/{SEASON_YEAR}/export?TYPE=draftResults&L={LEAGUE_ID}&JSON=1"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            return await resp.json()

async def monitor_draft():
    global draft_started, last_announced_pick
    await load_franchises()
    await client.wait_until_ready()
    channel = client.get_channel(DRAFT_CHANNEL_ID)

    if not channel:
        print("❌ Draft channel not found.")
        return

    while not client.is_closed():
        data = await fetch_draft_data()
        draft_unit = data.get("draftResults", {}).get("draftUnit", [{}])[0]
        picks = draft_unit.get("draftPick", [])
        total_picks = int(draft_unit.get("totalRounds", 0)) * int(draft_unit.get("picksPerRound", 0))

        if picks and not draft_started:
            draft_started = True
            await channel.send("📢 **The Draft Has Officially Started!**")

        next_pick_number = len(picks) + 1

        if next_pick_number <= total_picks and next_pick_number != last_announced_pick:
            next_franchise_id = draft_unit.get("franchise", [{}])[0].get("id")
            if not next_franchise_id:
                next_franchise_id = draft_unit.get("franchise", [{}])[0]
            team_name = franchise_names.get(next_franchise_id, f"Franchise {next_franchise_id}")
            await channel.send(f"⏰ **On the Clock (Pick #{next_pick_number}):** {team_name}")
            last_announced_pick = next_pick_number

        await asyncio.sleep(CHECK_INTERVAL)

@client.event
async def on_ready():
    print(f"✅ Logged in as {client.user}")
    client.loop.create_task(monitor_draft())

client.run(DISCORD_TOKEN)
