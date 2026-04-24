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

SPORT_CONFIG = {
    "all": {"emoji": "🔥", "color": 0xff00ff, "name": "All Sports"},
    "football": {"emoji": "⚽", "color": 0x00ff88, "name": "Football"},
    "horse_racing": {"emoji": "🐎", "color": 0xffaa00, "name": "Horse Racing"},
    "ufc": {"emoji": "🥊", "color": 0xff0000, "name": "UFC"},
    "boxing": {"emoji": "🥊", "color": 0xff0000, "name": "Boxing"},
    "darts": {"emoji": "🎯", "color": 0x00aaff, "name": "Darts"},
    "bangers": {"emoji": "💣", "color": 0xffff00, "name": "Bangers"},
}

def normalize_sport(sport: str) -> str:
    sport_lower = sport.lower().strip()
    if sport_lower in ["horse", "horses", "racing", "horse racing", "horseracing"]:
        return "horse_racing"
    return sport_lower

def get_coloured_bar(percentage: int) -> str:
    """Creates a visual battery bar with blue to red gradient"""
    filled = max(1, int(percentage / 10))
    empty = 10 - filled
    
    if percentage >= 85:
        bar = "🟥" * filled + "⬛" * empty + " 🔥"
    elif percentage >= 70:
        bar = "🟧" * filled + "⬛" * empty
    elif percentage >= 55:
        bar = "🟨" * filled + "⬛" * empty
    elif percentage >= 35:
        bar = "🟦" * filled + "⬛" * empty
    else:
        bar = "🔵" * filled + "⬛" * empty
    
    return f"{bar} **{percentage}%**"

def clean_response(text: str) -> str:
    text = re.sub(r'\n{3,}', '\n\n', text.strip())
    return '\n'.join(line.strip() for line in text.split('\n'))

async def get_sports_tips(sport: str):
    try:
        client = AsyncClient(api_key=XAI_API_KEY, timeout=110)
        
        chat = client.chat.create(
            model="grok-4.20-reasoning",
            tools=[web_search(), x_search()],
            temperature=0.85,
            max_turns=6,
        )

        date_today = datetime.now(pytz.timezone('GMT')).strftime('%A %d %B %Y')

        if sport == "bangers":
            sport_display = "Bangers 🔥"
            extra = "Only high confidence bangers (80%+)."
        else:
            sport_display = "All Sports" if sport == "all" else ("Horse Racing" if sport == "horse_racing" else sport.replace("_", " ").title())
            extra = ""

        prompt = f"""
Current date: {date_today} BST. STRICT: Only next 48 hours.

Return exactly 4 tips in this format:

**1. Event** – Bet (odds) | **Date + Time BST** | Confidence: XX% [BAR]  
→ Savage funny bantery line.

Use a visual bar that fills according to the percentage.
"""

        chat.append(system("""You are a savage, cheeky Racing AI bot. 
Always show confidence as "Confidence: XX% [visual bar]". 
Use blue for low, orange for medium, red for high confidence."""))
        
        chat.append(user(prompt))

        response = await chat.sample()
        cleaned = clean_response(response.content)
        return cleaned or "No upcoming events in next 48 hours."

    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return f"❌ Error fetching tips: {str(e)[:200]}"

# ====================== SLASH COMMAND ======================
@bot.tree.command(name="tips", description="Get hot tips - e.g. /tips football, /tips horse, /tips bangers")
async def hot_tips(interaction: discord.Interaction, sport: str = "all"):
    await interaction.response.defer(thinking=True)
    
    normalized = normalize_sport(sport)
    config = SPORT_CONFIG.get(normalized, SPORT_CONFIG["all"])
    display_name = config["name"]
    
    status_msg = await interaction.followup.send(
        "🔍 Analysing real-time data... **This can take approx 60 seconds** due to live searches.\n"
        "So stop ya whining 😂 and go and buy a monkey or some gainz while you wait — awesome shit like this don't come for free!"
    )

    analysis = await get_sports_tips(normalized)
    
    embed = discord.Embed(
        title=f"{config['emoji']} Top 4 {display_name} Hot Tips",
        description=f"📅 {datetime.now(pytz.timezone('GMT')).strftime('%A %d %B %Y %H:%M')} BST",
        color=config['color']
    )
    
    embed.add_field(name="Hot Tips", value=analysis[:3900] or "No upcoming events in next 48 hours.", inline=False)
    
    embed.set_footer(text="🔥 For entertainment only • Not real betting advice • Gamble responsibly • 18+ • Bet at your own risk")
    
    await interaction.followup.send(embed=embed)
    
    try:
        await status_msg.delete()
    except:
        pass

@bot.event
async def on_ready():
    print(f"✅ {bot.user} is ONLINE!")
    try:
        await bot.tree.sync()
        print("✅ Slash commands synced")
    except Exception as e:
        print(f"Sync warning: {e}")
    scheduler.start()

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
