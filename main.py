import os
from datetime import datetime
import pytz
from dotenv import load_dotenv
import discord
from discord.ext import commands
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from openai import OpenAI

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
XAI_API_KEY = os.getenv("XAI_API_KEY")
CHANNEL_ID = int(os.getenv("CHANNEL_ID", 0))

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

scheduler = AsyncIOScheduler(timezone="GMT")

async def get_daily_tips():
    try:
        client = OpenAI(api_key=XAI_API_KEY, base_url="https://api.x.ai/v1")
        date_today = datetime.now(pytz.timezone('GMT')).strftime('%A %d %B %Y')

        prompt = f"""You are a sharp multi-sport tipster.
Date: {date_today}

Give exactly 4 strong bets across different sports (Horse Racing, Soccer, Tennis, UFC, Boxing, Darts).

For each bet include:
- Sport & Event
- Pick
- Confidence (1-10)
- Short reasoning

Be realistic and only tip things you are confident in today."""

        response = client.chat.completions.create(
            model="grok-4.20-reasoning",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.65,
            max_tokens=1000
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"❌ AI Error: {str(e)[:200]}"

@bot.command(name="tips")
async def daily_tips(ctx):
    msg = await ctx.send("🔥 **Multi-Sport Daily Tips** – Generating strong picks... ⏳")
    analysis = await get_daily_tips()
    
    embed = discord.Embed(
        title="🔥 Multi-Sport Daily Tips",
        description=f"📅 {datetime.now(pytz.timezone('GMT')).strftime('%A %d %B %Y')}\nPowered by xAI Grok",
        color=0xff00ff
    )
    embed.add_field(name="📌 4 Strong Bets", value=analysis[:1020], inline=False)
    embed.set_footer(text="For entertainment only • Gamble responsibly • 18+")
    await msg.edit(embed=embed)

@bot.event
async def on_ready():
    print(f"✅ {bot.user} is ONLINE! Multi-Sport Mode Active")
    scheduler.start()

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
