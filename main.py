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
Current date: {date_today} (GMT).

ONLY tip events that are happening or starting **within the next 48 hours**.

Popular sports: Horse Racing, Premier League, Champions League, Tennis, UFC, Boxing, Darts.

For each bet include:
- Sport & Event (with date/time if known)
- Pick
- Confidence (1-10)
- Short reasoning

Give exactly 4 strong, realistic bets. Do not invent events."""

        response = client.chat.completions.create(
            model="grok-4.20-reasoning",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.6,
            max_tokens=1100
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"❌ Error: {str(e)[:150]}"

@bot.command(name="tips")
async def daily_tips(ctx):
    msg = await ctx.send("🔥 **Multi-Sport Tips** – Finding real events in next 48 hours... ⏳")
    analysis = await get_daily_tips()
    
    embed = discord.Embed(
        title="🔥 Multi-Sport Daily Tips",
        description=f"📅 {datetime.now(pytz.timezone('GMT')).strftime('%A %d %B %Y')}\nPowered by xAI Grok",
        color=0xff00ff
    )
    embed.add_field(name="📌 4 Strong Bets (Next 48 Hours)", value=analysis[:1020], inline=False)
    embed.set_footer(text="For entertainment only • Gamble responsibly • 18+")
    await msg.edit(embed=embed)

@bot.event
async def on_ready():
    print(f"✅ {bot.user} is ONLINE!")
    scheduler.start()

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
