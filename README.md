# PyMusic

PyMusic é um bot de música para Discord, desenvolvido em Python, que permite tocar músicas diretamente do YouTube em canais de voz. 

## Funcionalidades
- Tocar músicas ou playlists diretamente do YouTube.
- Comandos para gerenciar fila de reprodução.
- Comando para parar e desconectar o bot.
- Uso de cookies para autenticação de YouTube, melhorando a compatibilidade com vídeos privados ou regionais.

## Requisitos
- Python 3.8 ou superior
- FFmpeg
- yt-dlp

## Instalação

1. Clone este repositório:
   ```bash
   git clone https://github.com/WindLother/PyMusic.git
   cd PyMusic
   ```

2. Crie e ative um ambiente virtual:
   python3 -m venv venv
   source venv/bin/activate

3. Instale as dependências:
   pip install -r requirements.txt

4. Crie um arquivo `.env` na raiz do projeto e adicione seu token do Discord:
   DISCORD_TOKEN=seu_token_aqui

5. Certifique-se de que o FFmpeg está instalado no sistema:
   sudo apt install ffmpeg

## Uso

Para iniciar o bot:
python bot.py

O bot escutará comandos com o prefixo `#`.

## Notas
- **O arquivo `cookies.txt` contém informações sensíveis e NÃO deve ser enviado para o repositório. Ele é usado para autenticação no YouTube.**
- O bot usa `yt-dlp` para buscar músicas no YouTube.

## Comandos Disponíveis
- `#p <busca>`: Toca uma música ou playlist com base na busca fornecida.
- `#queue`: Exibe a fila de reprodução atual.
- `#skip`: Pula para a próxima música na fila.
- `#stop`: Para a reprodução e desconecta o bot.

## Contribuição
Contribuições são bem-vindas. Por favor, abra uma issue ou envie um pull request.

---

Criado por WindLother

