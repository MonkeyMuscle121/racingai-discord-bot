import os
from datetime import datetime
import pytz
from dotenv import load_dotenv
import discord
from discord.ext import commands
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import asyncio
import logging
import re
# xAI SDK
from xai_sdk import AsyncClient
from xai_sdk.chat import user, system
from xai_sdk.tools import web_search, x_search

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
XAI_API_KEY = os.getenv("XAI_API_KEY")
CHANNEL_ID = int(os.getenv("CHANNEL_ID", 0))

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)
scheduler = AsyncIOScheduler(timezone="GMT")

def normalize_sport(sport: str) -> str:
    sport_lower = sport.lower().strip()
    if sport_lower in ["horse", "horses", "racing", "horse racing", "horseracing"]:
        return "horse_racing"
    return sport_lower

def clean_response(text: str) -> str:
    text = re.sub(r'\n{3,}', '\n\n', text.strip())
    lines = [line.strip() for line in text.split('\n')]
    return '\n'.join(lines)

# ====================== FERAL TIPS FUNCTION ======================
async def get_sports_tips(sport: str):
    try:
        normalized = normalize_sport(sport)
       
        client = AsyncClient(api_key=XAI_API_KEY, timeout=120)
       
        chat = client.chat.create(
            model="grok-4",
            tools=[web_search(), x_search()],
            temperature=0.95,
            max_turns=5,
        )
        
        date_today = datetime.now(pytz.timezone('Europe/London')).strftime('%A %d %B %Y')
       
        sport_display = "Horse Racing" if normalized == "horse_racing" else sport.replace("_", " ").title()
       
        prompt = f"""
Current date: {date_today}. Use BST times.

Go full feral. No mercy. No filter.

Return **exactly** the top 4 hot tips in this format:

**Top 4 {sport_display} Feral Tips...**

1. **Event** – Specific bet (exact horses/fighters/teams, odds if available, **precise BST time**)
   → Then one absolutely savage, disgusting, cheeky, unhinged one-liner.

Heavy swearing, roast mums, dads, nans, grandads, sisters, brothers, exes — the whole bloodline.
Dark humour encouraged. Be funny as fuck.
"""

        if normalized in ["all", "mixed", "general"]:
            prompt = prompt.replace("focusing mainly on **all**", 
                                  "UFC, boxing, darts, horse racing, and football")

        chat.append(system("""You are FERAL GROK — a completely unhinged, degenerate, pissed-up British gambling gremlin.
You have zero chill and zero filter. 
Roast their entire family tree in the most savage way possible. 
Swearing is mandatory. Dark, sexual, and disgusting banter is encouraged.
You sound like a drunk mate at 3am who's lost his giro on the horses but is still convinced he's got the next winner.
End with a sarcastic "entertainment only" disclaimer."""))

        chat.append(user(prompt))
        response = await chat.sample()
        
        cleaned = clean_response(response.content)
        return cleaned or "Even the feral gremlin is too hungover to speak today."

    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return f"❌ The feral AI is having a breakdown mate: {str(e)[:150]}"

# ====================== SLASH COMMAND ======================
@bot.tree.command(name="tips", description="Get hot tips - e.g. /tips football, /tips horse, /tips boxing")
async def hot_tips(interaction: discord.Interaction, sport: str = "all"):
    await interaction.response.defer(thinking=True)
   
    normalized = normalize_sport(sport)
    display_name = "All Sports" if normalized == "all" else ("Horse Racing" if normalized == "horse_racing" else sport.replace("_", " ").title())
   
    status_msg = await interaction.followup.send(
        "🔍 Analysing real-time data... **This can take approx 60 seconds** due to live searches.\n"
        "So stop ya whining 😂 and go and buy a monkey or some gainz while you wait — awesome shit like this don't come for free!"
    )
    
    analysis = await get_sports_tips(sport)
   
    embed = discord.Embed(
        title=f"🔥 Top 4 {display_name} FERAL Tips",
        description=f"📅 {datetime.now(pytz.timezone('GMT')).strftime('%A %d %B %Y %H:%M')} BST",
        color=0xff00ff
    )
   
    if len(analysis) > 1000:
        chunks = [analysis[i:i+1000] for i in range(0, len(analysis), 1000)]
        for chunk in chunks:
            embed.add_field(name="", value=chunk, inline=False)
    else:
        embed.add_field(name="Hot Tips", value=analysis or "No data at the moment.", inline=False)
   
    embed.set_footer(text="🔥 For entertainment only • Not real betting advice • Gamble responsibly • 18+ • Bet at your own risk")

    await interaction.followup.send(embed=embed)
   
    try:
        await status_msg.delete()
    except:
        pass
