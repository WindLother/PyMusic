import yt_dlp
import asyncio
import browser_cookie3
import os

search_cache = {}
song_info_cache = {}

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
                for entry in info['entries']:
                    entries.append(entry['url'])
                result = entries
            else:
                result = [info['url']]
            search_cache[search] = result
            return result
    except Exception as e:
        print(f'Erro ao buscar no YouTube: {e}')
        return None
    finally:
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
        'default_search': 'ytsearch1',
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)'
                      ' Chrome/115.0.0.0 Safari/537.36',
        'cookiefile': cookiefile,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url_or_id, download=False)
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

