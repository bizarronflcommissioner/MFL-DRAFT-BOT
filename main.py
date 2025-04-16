import discord
import asyncio
import aiohttp
import xml.etree.ElementTree as ET
from datetime import datetime
from dotenv import load_dotenv
import os

load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
LEAGUE_ID = int(os.getenv("LEAGUE_ID", 61663))
DRAFT_CHANNEL_ID = int(os.getenv("DRAFT_CHANNEL_ID", 1359911725327056922))
SEASON_YEAR = 2025
CHECK_INTERVAL = 300  # Check every 5 minutes

print("DISCORD_TOKEN LOADED:", DISCORD_TOKEN[:5] if DISCORD_TOKEN else "None")

intents = discord.Intents.default()
client = discord.Client(intents=intents)
posted_picks = set()
franchise_names = {}

async def load_franchises():
    url = f"https://www43.myfantasyleague.com/{SEASON_YEAR}/export?TYPE=league&L={LEAGUE_ID}&JSON=1"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            data = await resp.json()
            for f in data["league"]["franchises"]["franchise"]:
                franchise_names[f["id"]] = f["name"]
    print(f"Loaded {len(franchise_names)} franchises.")

async def fetch_draft():
    url = f"https://www43.myfantasyleague.com/{SEASON_YEAR}/export?TYPE=draftResults&L={LEAGUE_ID}&JSON=1"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                print(f"Failed to fetch draft: HTTP {resp.status}")
                return [], None
            data = await resp.json()
            try:
                draft_unit = data.get("draftResults", {}).get("draftUnit", [])
                picks = draft_unit[0].get("draftPick", [])
                start_time = draft_unit[0].get("startTime")
                return picks, start_time
            except (IndexError, AttributeError) as e:
                print(f"Error parsing draft JSON: {e}")
                return [], None

async def draft_check_loop():
    await client.wait_until_ready()
    channel = client.get_channel(DRAFT_CHANNEL_ID)
    if channel is None:
        print("❌ ERROR: Cannot find draft channel.")
        return

    await load_franchises()
    draft_announced = False

    while not client.is_closed():
        print("Checking draft status...")
        picks, start_time = await fetch_draft()

        if not picks:
            print("No draft picks found.")
            await asyncio.sleep(CHECK_INTERVAL)
            continue

        if not draft_announced and start_time:
            readable_time = datetime.fromtimestamp(int(start_time)).strftime('%b %d, %Y %I:%M %p')
            await channel.send(f"🏈 **The draft has started!** First pick scheduled for {readable_time}.\n{'-' * 40}")
            draft_announced = True

        for i, pick in enumerate(picks):
            print(f"Pick #{i + 1}: {pick}")
            pick_id = pick["timestamp"]
            if pick_id in posted_picks:
                continue

            posted_picks.add(pick_id)
            franchise = pick["franchise"]
            player_name = pick.get("playerName", f"Player #{pick.get('player')}")
            round_num = pick["round"]
            pick_num = pick["pick"]

            message = f"🏈 **Draft Pick:** {franchise_names.get(franchise, f'Franchise {franchise}')} selected {player_name} (Round {round_num}, Pick {pick_num})"

            if i + 1 < len(picks):
                on_clock = picks[i + 1]["franchise"]
                message += f"\n🕒 On the clock: {franchise_names.get(on_clock, f'Franchise {on_clock}')}"
            if i + 2 < len(picks):
                on_deck = picks[i + 2]["franchise"]
                message += f"\n📋 On deck: {franchise_names.get(on_deck, f'Franchise {on_deck}')}"

            await channel.send(message + "\n" + "-" * 40)

        await asyncio.sleep(CHECK_INTERVAL)

@client.event
async def on_ready():
    print(f"✅ Logged in as {client.user}")
    client.loop.create_task(draft_check_loop())

client.run(DISCORD_TOKEN)
