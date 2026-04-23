import os
from datetime import datetime
import pytz
from dotenv import load_dotenv
import discord
from discord.ext import commands
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from openai import OpenAI
import asyncio

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
XAI_API_KEY = os.getenv("XAI_API_KEY")
CHANNEL_ID = int(os.getenv("CHANNEL_ID", 0))

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

scheduler = AsyncIOScheduler(timezone="GMT")

async def analyze_with_ai():
    try:
        if not XAI_API_KEY:
            return "❌ XAI API key is missing."

        client = OpenAI(
            api_key=XAI_API_KEY,
            base_url="https://api.x.ai/v1"
        )

        prompt = "Today horse racing tips: Give 4 bets + 1 fourfold accumulator. Keep it short."

        response = await asyncio.wait_for(
            asyncio.get_event_loop().run_in_executor(
                None,
                lambda: client.chat.completions.create(
                    model="grok-4.1",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7,
                    max_tokens=800
                )
            ),
            timeout=25.0  # 25 second timeout
        )
        return response.choices[0].message.content

    except asyncio.TimeoutError:
        return "❌ Timeout - AI took too long. Try again."
    except Exception as e:
        return f"❌ AI Error: {str(e)[:150]}"

@bot.command(name="tips")
async def manual_tips(ctx):
    msg = await ctx.send("🐎 **RacingAI Tips** – Generating now... ⏳")
    
    analysis = await analyze_with_ai()
    
    embed = discord.Embed(
        title="🐎 RacingAI Tips",
        description=f"📅 {datetime.now(pytz.timezone('GMT')).strftime('%A %d %B %Y')}\n🔥 Powered by xAI Grok",
        color=0x00ff88
    )
    embed.add_field(name="📌 4 Best Bets + 4-Fold Acca", value=analysis[:4000], inline=False)
    embed.set_footer(text="For entertainment only • Gamble responsibly • 18+")
    
    await msg.edit(embed=embed)   # Update the message

@bot.event
async def on_ready():
    print(f"✅ {bot.user} is ONLINE!")
    scheduler.start()

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
