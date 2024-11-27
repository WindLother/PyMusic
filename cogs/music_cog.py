import discord
from discord.ext import commands
import asyncio
from utils import youtube

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.queues = {}
        self.FFMPEG_OPTIONS = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            'options': '-vn'
        }

    @commands.command(name='p')
    async def play(self, ctx, *, search: str):
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
        song_urls = await youtube.search_youtube_async(search)

        if song_urls is None or len(song_urls) == 0:
            embed = discord.Embed(
                title="Erro",
                description="Desculpe, não consegui encontrar a música ou playlist.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return

        guild_id = ctx.guild.id

        if guild_id not in self.queues:
            self.queues[guild_id] = []

        # Busca as informações das músicas
        songs = []
        for url in song_urls:
            song = await youtube.get_song_info_async(url)
            if song:
                songs.append(song)
            else:
                print(f'Erro ao obter informações da música para {url}')

        if ctx.voice_client.is_playing() or ctx.voice_client.is_paused():
            self.queues[guild_id].extend(songs)
            embed = discord.Embed(
                title="Adicionado à Fila",
                description=f"Adicionado {len(songs)} música(s) à fila.",
                color=discord.Color.blue()
            )
            await ctx.send(embed=embed)
        else:
            # Toca a primeira música imediatamente
            if songs:
                first_song = songs.pop(0)
                await self.play_song(ctx, first_song)
                # Adiciona as demais à fila
                if songs:
                    self.queues[guild_id].extend(songs)
            else:
                embed = discord.Embed(
                    title="Erro",
                    description="Não foi possível obter informações das músicas.",
                    color=discord.Color.red()
                )
                await ctx.send(embed=embed)

    async def play_song(self, ctx, song):
        if not ctx.voice_client or not ctx.voice_client.is_connected():
            await ctx.send("O bot não está conectado a um canal de voz.")
            return

        url = song['url']
        voice_client = ctx.voice_client

        def after_playing(error):
            if error:
                print(f'Erro no player: {error}')
            # Verificamos se o voice_client ainda está conectado
            if voice_client and voice_client.is_connected():
                coro = self.check_queue(ctx)
                fut = asyncio.run_coroutine_threadsafe(coro, self.bot.loop)
                try:
                    fut.result()
                except Exception as e:
                    print(f'Erro no after_playing: {e}')
            else:
                print('Voice client desconectado.')

        source = discord.FFmpegPCMAudio(url, **self.FFMPEG_OPTIONS)
        voice_client.play(source, after=after_playing)

        embed = discord.Embed(
            title="Tocando Agora",
            description=f"[{song['title']}]({song['webpage_url']})",
            color=discord.Color.green()
        )
        if song['thumbnail']:
            embed.set_thumbnail(url=song['thumbnail'])
        await ctx.send(embed=embed)

    async def check_queue(self, ctx):
        guild_id = ctx.guild.id
        if self.queues[guild_id]:
            next_song = self.queues[guild_id].pop(0)
            if ctx.voice_client and ctx.voice_client.is_connected():
                await self.play_song(ctx, next_song)
            else:
                print('Voice client não está conectado em check_queue.')
        else:
            try:
                await ctx.voice_client.disconnect()
            except asyncio.TimeoutError:
                await ctx.voice_client.disconnect(force=True)
            except Exception as e:
                print(f'Erro ao desconectar: {e}')

    @commands.command(name='stop')
    async def stop(self, ctx):
        guild_id = ctx.guild.id
        self.queues[guild_id] = []
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

    @commands.command(name='skip')
    async def skip(self, ctx):
        if ctx.voice_client and (ctx.voice_client.is_playing() or ctx.voice_client.is_paused()):
            ctx.voice_client.stop()
            embed = discord.Embed(
                title="Música Pulada",
                description="Pulando para a próxima música.",
                color=discord.Color.orange()
            )
            await ctx.send(embed=embed)
            # Não chamamos check_queue aqui
        else:
            embed = discord.Embed(
                title="Erro",
                description="Não há música sendo tocada no momento.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)

    @commands.command(name='queue')
    async def queue_command(self, ctx):
        guild_id = ctx.guild.id
        if guild_id not in self.queues or not self.queues[guild_id]:
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
        for idx, song in enumerate(self.queues[guild_id], start=1):
            description += f"{idx}. [{song['title']}]({song['webpage_url']})\n"

        embed.description = description
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Music(bot))

