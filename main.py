
import os
from datetime import datetime
import pytz
from dotenv import load_dotenv
import discord
from discord.ext import commands
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import logging
import asyncio

# xAI SDK
from xai_sdk import AsyncClient
from xai_sdk.chat import user, system

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
XAI_API_KEY = os.getenv("XAI_API_KEY")
CHANNEL_ID = int(os.getenv("CHANNEL_ID", 0))

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)
scheduler = AsyncIOScheduler(timezone="Europe/London")

LOADING_MESSAGES = [
    "🔍 Finding proper punts... hold tight you melt 😂",
    "🔍 Digging for value bets...",
    "🔍 Loading smart tips...",
]

def get_random_loading_message():
    import random
    return random.choice(LOADING_MESSAGES)

async def get_sports_tips(sport: str):
    try:
        async with asyncio.timeout(65):
            client = AsyncClient(api_key=XAI_API_KEY, timeout=60)
            chat = client.chat.create(
                model="grok-4.20-reasoning",
                tools=[web_search(), x_search()],
                temperature=0.7,
                max_turns=4,
            )
            
            prompt = f"Give 4 good {sport} tips for today and tomorrow. Include meet, race name, time, pick and a savage comment. Just reply normally, no JSON."
            
            chat.append(system("You are a savage, cheeky Racing AI bot. Be funny and brutal. Use real races only."))
            chat.append(user(prompt))
            response = await chat.sample()
            
            return response.content[:3900]
            
    except Exception as e:
        logger.error(f"Error: {e}")
        return "❌ Failed to fetch tips. Try again in 30 seconds."

@bot.tree.command(name="tips", description="Get hot tips")
async def hot_tips(interaction: discord.Interaction, sport: str = "horse"):
    await interaction.response.defer(thinking=True)
    status_msg = await interaction.followup.send(get_random_loading_message())
    
    try:
        display = await get_sports_tips(sport)

        embed = discord.Embed(
            title=f"🔥 Top Tips for {sport.replace('_', ' ').title()}",
            description=f"📅 {datetime.now(pytz.timezone('Europe/London')).strftime('%A %d %B %Y %H:%M')} BST",
            color=0xff00ff
        )
        embed.add_field(name="Tips", value=display or "No tips right now", inline=False)
        embed.set_footer(text="🔥 For entertainment only • Not real betting advice • Gamble responsibly • 18+")
        await interaction.followup.send(embed=embed)
    except:
        await interaction.followup.send("❌ Error. Try again.")
    finally:
        try: await status_msg.delete()
        except: pass

@bot.event
async def on_ready():
    print(f"✅ {bot.user} V5.0 — SIMPLE & WORKING!")
    await bot.tree.sync()

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
