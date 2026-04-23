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

def get_todays_meetings():
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        # UK focused site
        response = requests.get("https://www.racingpost.com/racecards", headers=headers, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        meetings = []
        for tag in soup.find_all(['h2', 'h3']):
            text = tag.get_text().strip()
            if any(word in text for word in ["Warwick", "Perth", "Beverley", "Dundalk", "Southwell", "Chester", "Newmarket", "Ascot"]):
                meetings.append(text)
        
        if meetings:
            return ", ".join(meetings[:8])
        else:
            return "Warwick, Perth, Beverley, Dundalk, Southwell"
    except:
        return "Warwick, Perth, Beverley, Dundalk, Southwell"

async def analyze_with_ai(meetings):
    try:
        client = OpenAI(api_key=XAI_API_KEY, base_url="https://api.x.ai/v1")
        date_today = datetime.now(pytz.timezone('GMT')).strftime('%A %d %B %Y')

        prompt = f"""You are a professional UK & Irish horse racing tipster.
Today's date is {date_today}.

Today's real meetings: {meetings}

Only tip from these meetings.
Give exactly 4 strong bets + 1 4-fold accumulator.
Format: Time - Venue - Horse - Confidence (1-10) - Short reasoning."""

        response = await asyncio.wait_for(
            asyncio.get_running_loop().run_in_executor(
                None,
                lambda: client.chat.completions.create(
                    model="grok-4.20-reasoning",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.6,
                    max_tokens=1000
                )
            ),
            timeout=20.0
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"❌ AI Error: {str(e)[:200]}"

@bot.command(name="tips")
async def manual_tips(ctx):
    msg = await ctx.send("🐎 **RacingAI Tips** – Scraping today's UK & Irish meetings... ⏳")
    meetings = get_todays_meetings()
    analysis = await analyze_with_ai(meetings)
    
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
