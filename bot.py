import discord
from discord.ext import commands
import yt_dlp
import asyncio
import os
import browser_cookie3
from dotenv import load_dotenv

# Carrega variáveis de ambiente do .env
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix='#', intents=intents, help_command=None)

queues = {}
search_cache = {}
song_info_cache = {}

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
    Retorna uma lista de URLs ou IDs de vídeos.
    """
    if search in search_cache:
        return search_cache[search]
    cookiefile = get_cookies()
    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'skip_download': True,
        'default_search': 'ytsearch1',
        'extract_flat': True,  # Adicionado para acelerar a busca
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
                    entries.append(entry['url'])
                result = entries  # Retorna uma lista de URLs ou IDs
            else:
                # Não é uma playlist, é um único vídeo
                result = [info['url']]
            # Armazena no cache
            search_cache[search] = result
            return result
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

def get_song_info(video_url_or_id):
    """
    Função síncrona que obtém informações detalhadas de uma música.
    """
    if video_url_or_id in song_info_cache:
        return song_info_cache[video_url_or_id]
    cookiefile = get_cookies()
    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'skip_download': True,
        'default_search': 'ytsearch1',  # Alterado para garantir um único resultado
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)'
                      ' Chrome/115.0.0.0 Safari/537.36',
        'cookiefile': cookiefile,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url_or_id, download=False)
            # Verifica se 'entries' está em info e extrai o primeiro resultado
            if 'entries' in info:
                info = info['entries'][0]
            song = {
                'url': info['url'],
                'title': info['title'],
                'webpage_url': info['webpage_url'],
                'thumbnail': info.get('thumbnail')
            }
            song_info_cache[video_url_or_id] = song
            return song
    except Exception as e:
        print(f'Erro ao obter informações da música: {e}')
        return None
    finally:
        if cookiefile and os.path.exists(cookiefile):
            os.remove(cookiefile)

async def get_song_info_async(video_url_or_id):
    """
    Função assíncrona que executa get_song_info em um executor.
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, get_song_info, video_url_or_id)

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
    song_urls = await search_youtube_async(search)

    if song_urls is None or len(song_urls) == 0:
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
        queues[guild_id].extend(song_urls)
        embed = discord.Embed(
            title="Adicionado à Fila",
            description=f"Adicionado {len(song_urls)} música(s) à fila.",
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed)
    else:
        # Toca a primeira música imediatamente
        first_song_url = song_urls.pop(0)
        await play_song(ctx, first_song_url)
        # Adiciona as demais à fila
        if song_urls:
            queues[guild_id].extend(song_urls)

async def play_song(ctx, video_url_or_id):
    song = await get_song_info_async(video_url_or_id)
    if not song:
        await ctx.send("Erro ao obter informações da música.")
        return
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
        next_song_url = queues[guild_id].pop(0)
        await play_song(ctx, next_song_url)
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
    for idx, video_url_or_id in enumerate(queues[guild_id], start=1):
        # Tenta obter informações da música do cache
        song = song_info_cache.get(video_url_or_id)
        if song:
            description += f"{idx}. [{song['title']}]({song['webpage_url']})\n"
        else:
            description += f"{idx}. {video_url_or_id}\n"

    embed.description = description
    await ctx.send(embed=embed)

bot.run(TOKEN)

