import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import asyncio

# Carrega variáveis de ambiente do .env
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix='#', intents=intents, help_command=None)

@bot.event
async def on_ready():
    print(f'Bot conectado como {bot.user.name}')

async def main():
    # Carrega o cog de música
    await bot.load_extension('cogs.music_cog')
    await bot.start(TOKEN)

asyncio.run(main())

