import os
from datetime import datetime
import pytz
from dotenv import load_dotenv
import discord
from discord.ext import commands
import logging

# xAI SDK
from xai_sdk import AsyncClient
from xai_sdk.chat import user, system

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
XAI_API_KEY = os.getenv("XAI_API_KEY")

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.tree.command(name="tips", description="Get hot tips")
async def hot_tips(interaction: discord.Interaction, sport: str = "horse"):
    await interaction.response.defer(thinking=True)
    
    try:
        client = AsyncClient(api_key=XAI_API_KEY, timeout=50)
        chat = client.chat.create(
            model="grok-4.20-reasoning",
            temperature=0.7,
        )
        
        prompt = f"Give 4 savage hot tips for {sport} racing right now. Be funny and cheeky."
        
        chat.append(system("You are a savage, cheeky Racing AI bot."))
        chat.append(user(prompt))
        response = await chat.sample()
        
        embed = discord.Embed(
            title=f"🔥 Top Tips for {sport.replace('_', ' ').title()}",
            description=f"📅 {datetime.now(pytz.timezone('Europe/London')).strftime('%A %d %B %Y %H:%M')} BST",
            color=0xff00ff
        )
        embed.add_field(name="Tips", value=response.content[:3900], inline=False)
        embed.set_footer(text="🔥 For entertainment only • Gamble responsibly • 18+")
        
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        logger.error(f"Error: {e}")
        await interaction.followup.send("❌ Bot is struggling. Try again in 30 seconds.")

@bot.event
async def on_ready():
    print(f"✅ {bot.user} V4.6 — MINIMAL MODE!")
    await bot.tree.sync()

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
