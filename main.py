import os
from datetime import datetime
import pytz
from dotenv import load_dotenv
import discord
from discord.ext import commands
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import asyncio

# xAI SDK with real-time tools
from xai_sdk import AsyncClient  # ← Changed to AsyncClient
from xai_sdk.chat import user, system
from xai_sdk.tools import web_search, x_search

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
XAI_API_KEY = os.getenv("XAI_API_KEY")
CHANNEL_ID = int(os.getenv("CHANNEL_ID", 0))

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)
scheduler = AsyncIOScheduler(timezone="GMT")

# ====================== FULL SPORTS HOT TIPS ======================
async def get_full_sports_hot_tips():
    try:
        client = AsyncClient(api_key=XAI_API_KEY)  # ← AsyncClient
        
        chat = client.chat.create(
            model="grok-4.20-reasoning",
            tools=[web_search(), x_search()],   # Real-time web + X search enabled
            temperature=0.7,
        )

        date_today = datetime.now(pytz.timezone('GMT')).strftime('%A %d %B %Y')
        
        prompt = f"""
Analyse within the next 48 hours all sports bets: UFC, boxing, darts, horse racing, and any other relevant events.
Date: {date_today}
Give me the top 4 hot tip outcomes in this exact format:

**Top 4 hot tip outcomes for the next 48 hours...**

1. **Event** – Outcome (odds if available, why it's hot)
2. ...
3. ...
4. ...

Use real-time data only. Include participants, approximate times (BST), and strong reasoning.
"""

        chat.append(system("You are an expert sports betting analyst. Always use the latest real-time data via tools. Be accurate with events, participants and times."))
        chat.append(user(prompt))

        response = await chat.sample()   # ← This is async

        return response.content   # ← .content not .text

    except Exception as e:
        return f"❌ Error generating tips: {str(e)[:400]}"

# ====================== SLASH COMMAND ======================
@bot.tree.command(name="tips", description="Get the top 4 hot sports betting tips for the next 48 hours")
async def hot_tips(interaction: discord.Interaction):
    await interaction.response.defer()
    
    analysis = await get_full_sports_hot_tips()
    
    embed = discord.Embed(
        title="🔥 Top 4 Hot Tip Outcomes",
        description=f"📅 {datetime.now(pytz.timezone('GMT')).strftime('%A %d %B %Y %H:%M')} BST\n🔥 Powered by xAI Grok (real-time search)",
        color=0xff00ff
    )
    embed.add_field(name="Analysis", value=analysis[:4000], inline=False)
    embed.set_footer(text="For entertainment only • Bet responsibly • 18+ • Odds change quickly")
    
    await interaction.followup.send(embed=embed)

# ====================== OPTIONAL AUTO DAILY ======================
async def auto_daily_hottips():
    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        analysis = await get_full_sports_hot_tips()
        embed = discord.Embed(
            title="🔥 Daily Hot Tips",
            description=f"📅 {datetime.now(pytz.timezone('GMT')).strftime('%A %d %B %Y')}",
            color=0xff00ff
        )
        embed.add_field(name="Top 4 Outcomes", value=analysis[:4000], inline=False)
        embed.set_footer(text="Bet responsibly • 18+")
        await channel.send(embed=embed)

@bot.event
async def on_ready():
    print(f"✅ {bot.user} is ONLINE!")
    try:
        await bot.tree.sync()
        print("✅ Slash commands synced")
    except Exception as e:
        print(f"Sync warning: {e}")
    
    scheduler.start()
    
    # Auto daily tips at 8:00 AM GMT - Uncomment if you want automatic posts
    # scheduler.add_job(lambda: asyncio.create_task(auto_daily_hottips()), 'cron', hour=8, minute=0)

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
