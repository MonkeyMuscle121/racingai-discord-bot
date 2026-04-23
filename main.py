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

async def analyze_with_ai():
    if not XAI_API_KEY:
        return "❌ XAI API key is missing."

    client = OpenAI(
        api_key=XAI_API_KEY,
        base_url="https://api.x.ai/v1"
    )

    date_today = datetime.now(pytz.timezone('GMT')).strftime('%A %d %B %Y')

    prompt = f"""You are a professional UK & Irish horse racing tipster.
Today is {date_today}.

Give:
- 4 strong bets (win or each-way)
- 1 solid 4-fold accumulator

Include venue, time, horse, confidence, and short reason.
Use emojis. Be realistic."""

    try:
        response = client.chat.completions.create(
            model="grok-4.20-reasoning",   # Correct current model
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=1000
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"❌ AI Error: {str(e)[:250]}"

@bot.command(name="tips")
async def manual_tips(ctx):
    msg = await ctx.send("🐎 **RacingAI Tips** – Generating now... ⏳")
    analysis = await analyze_with_ai()
    
    embed = discord.Embed(
        title="🐎 RacingAI Tips",
        description=f"📅 {datetime.now(pytz.timezone('GMT')).strftime('%A %d %B %Y')}\n🔥 Powered by xAI Grok",
        color=0x00ff88,
        timestamp=datetime.now(pytz.utc)
    )
    embed.add_field(name="📌 4 Best Bets + 4-Fold Acca", value=analysis[:4096], inline=False)
    embed.set_footer(text="For entertainment only • Gamble responsibly • 18+")
    await msg.edit(embed=embed)

@bot.event
async def on_ready():
    print(f"✅ {bot.user} is ONLINE!")
    scheduler.start()

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
