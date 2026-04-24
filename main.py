import os
from datetime import datetime
import pytz
from dotenv import load_dotenv
import discord
from discord.ext import commands
from discord.ui import Button, View, Select
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

def clean_response(text: str) -> str:
    text = re.sub(r'\n{3,}', '\n\n', text.strip())
    return '\n'.join(line.strip() for line in text.split('\n'))

async def get_sports_tips(sport: str):
    try:
        client = AsyncClient(api_key=XAI_API_KEY, timeout=110)
        chat = client.chat.create(model="grok-4.20-reasoning", tools=[web_search(), x_search()], temperature=0.85, max_turns=6)

        date_today = datetime.now(pytz.timezone('GMT')).strftime('%A %d %B %Y')

        extra = "Only high confidence bangers (80%+)." if sport == "bangers" else ""

        prompt = f"""
Current date: {date_today} BST. STRICT: Only next 48 hours.

Return 4 tips in this exact format:

**1. Event** – Bet (odds) | **Date + Time BST** | **Confidence: XX%** ███████░░  
→ Savage funny bantery line (family jokes & swearing welcome)
"""

        chat.append(system("You are the savage, funniest Racing AI bot. Always include date+time and confidence bar. Heavy banter allowed."))
        chat.append(user(prompt))

        response = await chat.sample()
        return clean_response(response.content)

    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return "❌ Couldn't fetch tips right now."

# ====================== INTERACTIVE VIEW ======================
class TipsView(View):
    def __init__(self):
        super().__init__(timeout=300)  # 5 minutes

    @discord.ui.button(label="Refresh", style=discord.ButtonStyle.green, emoji="🔄")
    async def refresh(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer()
        # Re-run the same command
        await hot_tips.callback(interaction, "all")  # You can improve this later

    @discord.ui.button(label="Bangers", style=discord.ButtonStyle.blurple, emoji="💣")
    async def bangers(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer()
        await hot_tips.callback(interaction, "bangers")

    @discord.ui.button(label="Horse", style=discord.ButtonStyle.gray, emoji="🐎")
    async def horse(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer()
        await hot_tips.callback(interaction, "horse")

    @discord.ui.button(label="Football", style=discord.ButtonStyle.gray, emoji="⚽")
    async def football(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer()
        await hot_tips.callback(interaction, "football")

# ====================== MAIN COMMAND ======================
@bot.tree.command(name="tips", description="Get the best hot tips")
async def hot_tips(interaction: discord.Interaction, sport: str = "all"):
    await interaction.response.defer(thinking=True)

    config = SPORT_CONFIG.get(sport, SPORT_CONFIG["all"])
    
    status_msg = await interaction.followup.send(
        "🔍 Analysing real-time data... **This can take approx 60 seconds** due to live searches.\n"
        "So stop ya whining 😂 and go and buy a monkey or some gainz while you wait — awesome shit like this don't come for free!"
    )

    analysis = await get_sports_tips(sport)

    embed = discord.Embed(
        title=f"{config['emoji']} Top 4 {config['name']} Hot Tips",
        description=f"📅 {datetime.now(pytz.timezone('GMT')).strftime('%A %d %B %Y %H:%M')} BST",
        color=config['color']
    )
    
    embed.add_field(name="Hot Tips", value=analysis[:3900] or "No upcoming events.", inline=False)
    embed.set_footer(text="🔥 For entertainment only • Not real betting advice • Gamble responsibly • 18+")

    view = TipsView()
    await interaction.followup.send(embed=embed, view=view)

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

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
