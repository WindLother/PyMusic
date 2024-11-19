import discord
from discord.ext import commands
import yt_dlp
import asyncio
from functools import partial
from dotenv import load_dotenv
import os
import browser_cookie3

# Carrega variáveis de ambiente do .env
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix='#', intents=intents, help_command=None)

queues = {}

# Opções do FFmpeg para streaming de áudio
FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

def get_cookies():
    """
    Extrai os cookies do navegador e retorna o caminho do arquivo de cookies.
    """
    try:
        cj = browser_cookie3.load()
        # Salva os cookies em um arquivo no formato Netscape
        with open('cookies.txt', 'w') as f:
            f.write('# Netscape HTTP Cookie File\n')
            for cookie in cj:
                if 'youtube' in cookie.domain:
                    domain = cookie.domain
                    include_subdomain = 'TRUE' if domain.startswith('.') else 'FALSE'
                    path = cookie.path
                    secure = 'TRUE' if cookie.secure else 'FALSE'
                    expires = str(int(cookie.expires)) if cookie.expires else '0'
                    name = cookie.name
                    value = cookie.value

                    line = '\t'.join([domain, include_subdomain, path, secure, expires, name, value])
                    f.write(line + '\n')
        return 'cookies.txt'
    except Exception as e:
        print(f'Erro ao extrair cookies: {e}')
        return None

def search_youtube(search):
    """
    Função síncrona que busca músicas no YouTube usando yt-dlp.
    """
    cookiefile = get_cookies()
    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'skip_download': True,
        'default_search': 'ytsearch1',  # Adicionamos novamente este parâmetro
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)'
                      ' Chrome/115.0.0.0 Safari/537.36',
        'cookiefile': cookiefile,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(search, download=False)
            entries = []
            if 'entries' in info:
                # É uma playlist ou resultado de pesquisa com múltiplas entradas
                for entry in info['entries']:
                    entries.append({
                        'url': entry['url'],
                        'title': entry['title'],
                        'webpage_url': entry['webpage_url'],
                        'thumbnail': entry.get('thumbnail')
                    })
                return entries  # Retorna uma lista de músicas
            else:
                # Não é uma playlist, é um único vídeo
                return [{
                    'url': info['url'],
                    'title': info['title'],
                    'webpage_url': info['webpage_url'],
                    'thumbnail': info.get('thumbnail')
                }]
    except Exception as e:
        print(f'Erro ao buscar no YouTube: {e}')
        return None
    finally:
        # Remove o arquivo de cookies após o uso
        if cookiefile and os.path.exists(cookiefile):
            os.remove(cookiefile)

async def search_youtube_async(search):
    """
    Função assíncrona que executa search_youtube em um executor.
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, search_youtube, search)

@bot.event
async def on_ready():
    print(f'Bot conectado como {bot.user.name}')

@bot.command(name='p')
async def play(ctx, *, search: str):
    if ctx.author.voice is None:
        embed = discord.Embed(
            title="Erro",
            description="Você precisa estar em um canal de voz para tocar música.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return

    voice_channel = ctx.author.voice.channel

    if ctx.voice_client is None:
        await voice_channel.connect()
    elif ctx.voice_client.channel != voice_channel:
        await ctx.voice_client.move_to(voice_channel)

    # Chama a função assíncrona para evitar bloqueio
    songs = await search_youtube_async(search)

    if songs is None or len(songs) == 0:
        embed = discord.Embed(
            title="Erro",
            description="Desculpe, não consegui encontrar a música ou playlist.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return

    guild_id = ctx.guild.id

    if guild_id not in queues:
        queues[guild_id] = []

    if ctx.voice_client.is_playing() or ctx.voice_client.is_paused():
        queues[guild_id].extend(songs)
        embed = discord.Embed(
            title="Adicionado à Fila",
            description=f"Adicionado {len(songs)} música(s) à fila.",
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed)
    else:
        # Toca a primeira música imediatamente
        first_song = songs.pop(0)
        await play_song(ctx, first_song)
        # Adiciona as demais à fila
        if songs:
            queues[guild_id].extend(songs)
        # Removemos a mensagem "Tocando Agora" daqui para evitar duplicação

async def play_song(ctx, song):
    url = song['url']

    def after_playing(error):
        if error:
            print(f'Erro no player: {error}')
        coro = check_queue(ctx)
        fut = asyncio.run_coroutine_threadsafe(coro, bot.loop)
        try:
            fut.result()
        except Exception as e:
            print(f'Erro no after_playing: {e}')

    source = discord.FFmpegPCMAudio(url, **FFMPEG_OPTIONS)
    ctx.voice_client.play(source, after=after_playing)

    embed = discord.Embed(
        title="Tocando Agora",
        description=f"[{song['title']}]({song['webpage_url']})",
        color=discord.Color.green()
    )
    if song['thumbnail']:
        embed.set_thumbnail(url=song['thumbnail'])
    await ctx.send(embed=embed)

async def check_queue(ctx):
    guild_id = ctx.guild.id
    if queues[guild_id]:
        next_song = queues[guild_id].pop(0)
        await play_song(ctx, next_song)
    else:
        try:
            await ctx.voice_client.disconnect()
        except asyncio.TimeoutError:
            await ctx.voice_client.disconnect(force=True)
        except Exception as e:
            print(f'Erro ao desconectar: {e}')

@bot.command(name='stop')
async def stop(ctx):
    guild_id = ctx.guild.id
    queues[guild_id] = []
    if ctx.voice_client and (ctx.voice_client.is_playing() or ctx.voice_client.is_paused()):
        ctx.voice_client.stop()
    if ctx.voice_client:
        try:
            await ctx.voice_client.disconnect()
        except asyncio.TimeoutError:
            await ctx.voice_client.disconnect(force=True)
        except Exception as e:
            print(f'Erro ao desconectar: {e}')
    embed = discord.Embed(
        title="Música Parada",
        description="Parando a música e desconectando do canal de voz.",
        color=discord.Color.orange()
    )
    await ctx.send(embed=embed)

@bot.command(name='skip')
async def skip(ctx):
    if ctx.voice_client and (ctx.voice_client.is_playing() or ctx.voice_client.is_paused()):
        ctx.voice_client.stop()
        embed = discord.Embed(
            title="Música Pulada",
            description="Pulando para a próxima música.",
            color=discord.Color.orange()
        )
        await ctx.send(embed=embed)
        await check_queue(ctx)
    else:
        embed = discord.Embed(
            title="Erro",
            description="Não há música sendo tocada no momento.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)

@bot.command(name='queue')
async def queue_command(ctx):
    guild_id = ctx.guild.id
    if guild_id not in queues or not queues[guild_id]:
        embed = discord.Embed(
            title="Fila Vazia",
            description="Não há músicas na fila.",
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed)
        return

    embed = discord.Embed(
        title="Fila de Músicas",
        color=discord.Color.purple()
    )

    description = ""
    for idx, song in enumerate(queues[guild_id], start=1):
        description += f"{idx}. [{song['title']}]({song['webpage_url']})\n"

    embed.description = description
    await ctx.send(embed=embed)

bot.run(TOKEN)

