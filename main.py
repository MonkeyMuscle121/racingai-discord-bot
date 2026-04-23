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

print("DEBUG: DISCORD_TOKEN loaded =", bool(DISCORD_TOKEN))  # This will help us see the issue
print("DEBUG: XAI_API_KEY loaded =", bool(XAI_API_KEY))
print("DEBUG: CHANNEL_ID =", CHANNEL_ID)

if not DISCORD_TOKEN:
    print("❌ CRITICAL ERROR: DISCORD_TOKEN is missing or empty in Render Environment!")
    print("Please add it correctly and redeploy.")
    # Don't crash immediately so we can see logs

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

scheduler = AsyncIOScheduler(timezone="GMT")

async def analyze_with_ai():
    if not XAI_API_KEY:
        return "❌ XAI_API_KEY is missing."
    client = OpenAI(api_key=XAI_API_KEY, base_url="https://api.x.ai/v1")
    date_today = datetime.now(pytz.timezone('GMT')).strftime('%A %d %B %Y')
    prompt = f"You are an expert horse racing tipster on {date_today}. Give 4 good bets and 1 four-fold acca with short reasoning and confidence."
    try:
        resp = client.chat.completions.create(model="grok-beta", messages=[{"role": "user", "content": prompt}], temperature=0.7, max_tokens=1200)
        return resp.choices[0].message.content
    except Exception as e:
        return f"AI Error: {str(e)[:300]}"

@bot.command(name="tips")
async def manual_tips(ctx):
    await ctx.send("🐎 Generating RacingAI tips... ⏳")
    analysis = await analyze_with_ai()
    embed = discord.Embed(title="🐎 RacingAI Tips", color=0x00ff88, timestamp=datetime.now(pytz.utc))
    embed.add_field(name="Today's Picks", value=analysis[:4000], inline=False)
    embed.set_footer(text="For entertainment only • Gamble responsibly")
    await ctx.send(embed=embed)

@bot.event
async def on_ready():
    print(f"✅ SUCCESS: {bot.user} is ONLINE and ready!")
    scheduler.start()

@scheduler.scheduled_job('cron', hour=10, minute=0, timezone='GMT')
async def daily_post():
    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        await channel.send("🐎 **Daily RacingAI Tips** – 10:00 GMT")
        analysis = await analyze_with_ai()
        embed = discord.Embed(title="🐎 Daily Tips", color=0x00ff88)
        embed.add_field(name="Analysis", value=analysis[:4000], inline=False)
        await channel.send(embed=embed)

if __name__ == "__main__":
    if DISCORD_TOKEN:
        bot.run(DISCORD_TOKEN)
    else:
        print("Bot cannot start without DISCORD_TOKEN.")
