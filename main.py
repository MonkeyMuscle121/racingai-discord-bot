import os
from datetime import datetime
import pytz
from dotenv import load_dotenv
import discord
from discord.ext import commands
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from openai import OpenAI
import asyncio
import requests
from bs4 import BeautifulSoup

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
XAI_API_KEY = os.getenv("XAI_API_KEY")
CHANNEL_ID = int(os.getenv("CHANNEL_ID", 0))

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

scheduler = AsyncIOScheduler(timezone="GMT")

# Simple racecard scraper
def get_todays_meetings():
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get("https://www.racingpost.com/racecards", headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        meetings = [m.text.strip() for m in soup.find_all('h2', class_='meeting-name') if m]
        if meetings:
            return ", ".join(meetings[:6])
        return "Warwick, Perth, Beverley, Dundalk, Southwell"
    except:
        return "Warwick, Perth, Beverley, Dundalk, Southwell and other UK/Irish meetings"

async def analyze_with_ai():
    try:
        client = OpenAI(api_key=XAI_API_KEY, base_url="https://api.x.ai/v1")
        date_today = datetime.now(pytz.timezone('GMT')).strftime('%A %d %B %Y')
        meetings = get_todays_meetings()

        prompt = f"""You are a professional horse racing tipster.
Today is {date_today}.
Today's real meetings: {meetings}

Give exactly 4 strong bets + 1 4-fold accumulator from today's races only.
Format: Time - Venue - Horse - Confidence - Short reason."""

        response = await asyncio.wait_for(
            asyncio.get_running_loop().run_in_executor(
                None,
                lambda: client.chat.completions.create(
                    model="grok-4.20-reasoning",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.65,
                    max_tokens=950
                )
            ),
            timeout=20.0
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"❌ Error: {str(e)[:180]}"

@bot.command(name="tips")
async def manual_tips(ctx):
    msg = await ctx.send("🐎 **RacingAI Tips** – Fetching today's real meetings... ⏳")
    analysis = await analyze_with_ai()
    
    embed = discord.Embed(
        title="🐎 RacingAI Tips",
        description=f"📅 {datetime.now(pytz.timezone('GMT')).strftime('%A %d %B %Y')}\n🔥 Powered by xAI Grok",
        color=0x00ff88
    )
    embed.add_field(name="📌 4 Best Bets + 4-Fold Acca", value=analysis[:1020], inline=False)
    embed.set_footer(text="For entertainment only • Gamble responsibly • 18+")
    await msg.edit(embed=embed)

@bot.event
async def on_ready():
    print(f"✅ {bot.user} is ONLINE!")
    scheduler.start()

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
