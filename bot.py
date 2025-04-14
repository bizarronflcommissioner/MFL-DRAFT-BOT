import discord
import os
import requests
import asyncio
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID"))
LEAGUE_ID = os.getenv("MFL_LEAGUE_ID")
YEAR = os.getenv("MFL_YEAR")

intents = discord.Intents.default()
client = discord.Client(intents=intents)

last_pick_count = 0

async def fetch_draft_results():
    url = f"https://api.myfantasyleague.com/{YEAR}/export?TYPE=draftResults&L={LEAGUE_ID}&JSON=1"
    res = requests.get(url)
    if not res.ok:
        print("Failed to fetch draft data.")
        return []

    data = res.json()
    try:
        picks = data["draftResults"]["draftUnit"]["pick"]
        return picks
    except KeyError:
        return []

async def check_for_new_picks():
    global last_pick_count
    await client.wait_until_ready()
    channel = client.get_channel(CHANNEL_ID)

    while not client.is_closed():
        picks = await fetch_draft_results()
        if len(picks) > last_pick_count:
            new_picks = picks[last_pick_count:]
            for pick in new_picks:
                message = f"**Round {pick['round']} Pick {pick['pick']}** — <@{pick['franchise']}> drafted **{pick['player']} ({pick['position']})**"
                await channel.send(message)
            last_pick_count = len(picks)
        await asyncio.sleep(60)  # Check every 60 seconds

@client.event
async def on_ready():
    print(f"{client.user} connected to Discord!")

client.loop.create_task(check_for_new_picks())
client.run(TOKEN)
