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
bot = commands.Bot(command_prefix="/", intents=intents)

scheduler = AsyncIOScheduler(timezone="GMT")

TODAYS_MEETINGS = "Warwick, Perth, Beverley, Dundalk, Southwell"

@bot.command(name="setmeetings")
async def set_meetings(ctx, *, meetings: str):
    global TODAYS_MEETINGS
    TODAYS_MEETINGS = meetings.strip()
    await ctx.send(f"✅ **Meetings updated!**\nToday's meetings: **{TODAYS_MEETINGS}**")

@bot.command(name="meetings")
async def list_meetings(ctx):
    await ctx.send("**Common UK & Irish Racecourses:**\nAscot, Aintree, Ayr, Bangor, Bath, Beverley, Brighton, Carlisle, Cartmel, Catterick, Cheltenham, Chester, Doncaster, Dundalk, Epsom, Exeter, Ffos Las, Fontwell, Goodwood, Gowran Park, Hamilton, Haydock, Hereford, Hexham, Huntingdon, Kelso, Kempton, Leicester, Lingfield, Ludlow, Market Rasen, Musselburgh, Newbury, Newcastle, Newmarket, Nottingham, Perth, Plumpton, Pontefract, Redcar, Ripon, Salisbury, Sandown, Sedgefield, Southwell, Stratford, Taunton, Thirsk, Towcester, Uttoxeter, Warwick, Wincanton, Windsor, Wolverhampton, Worcester, Yarmouth, York\n\nUse: `/setmeetings Warwick, Perth, Beverley, Dundalk, Southwell`")

async def analyze_with_ai():
    try:
        client = OpenAI(api_key=XAI_API_KEY, base_url="https://api.x.ai/v1")
        date_today = datetime.now(pytz.timezone('GMT')).strftime('%A %d %B %Y')

        prompt = f"""Strict UK & Irish horse racing tipster.
Date: {date_today}
Today's meetings: {TODAYS_MEETINGS}

Only tip from these meetings.
Give exactly 4 strong bets + 1 4-fold.
Format: Time - Venue - Horse - Confidence (1-10) - Short reasoning."""

        response = client.chat.completions.create(
            model="grok-4.20-reasoning",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.55,
            max_tokens=1000
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"❌ Error: {str(e)[:150]}"

@bot.command(name="tips")
async def manual_tips(ctx):
    msg = await ctx.send("🐎 **RacingAI Tips** – Analysing today's meetings... ⏳")
    analysis = await analyze_with_ai()
    
    embed = discord.Embed(
        title="🐎 RacingAI Tips",
        description=f"📅 {datetime.now(pytz.timezone('GMT')).strftime('%A %d %B %Y')}\n🔥 Powered by xAI Grok",
        color=0x00ff88
    )
    embed.add_field(name="Today's Meetings", value=TODAYS_MEETINGS, inline=False)
    embed.add_field(name="📌 4 Best Bets + 4-Fold Acca", value=analysis[:1020], inline=False)
    embed.set_footer(text="For entertainment only • Gamble responsibly • 18+")
    await msg.edit(embed=embed)

@bot.event
async def on_ready():
    print(f"✅ {bot.user} is ONLINE!")
    scheduler.start()

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
