import os
import asyncio
import threading
from flask import Flask, render_template_string, request, jsonify
import discord
from discord.ext import commands
import wavelink

# Flask App Setup
app = Flask(__name__)

# HTML Template in Russian
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Музыкальный Бот Контроль</title>
    <style>
        body {
            margin: 0;
            padding: 0;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            color: white;
        }
        .container {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            padding: 2rem;
            border-radius: 20px;
            box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
            width: 90%;
            max-width: 500px;
            text-align: center;
        }
        input {
            width: 100%;
            padding: 12px;
            margin: 10px 0;
            border-radius: 10px;
            border: none;
            background: rgba(255, 255, 255, 0.2);
            color: white;
            box-sizing: border-box;
        }
        input::placeholder { color: rgba(255, 255, 255, 0.6); }
        .buttons {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
            margin-top: 10px;
        }
        button {
            padding: 12px;
            border-radius: 10px;
            border: none;
            background: #9f7aea;
            color: white;
            cursor: pointer;
            transition: 0.3s;
            font-weight: bold;
        }
        button:hover { background: #805ad5; }
        .status { margin-top: 20px; font-size: 0.9rem; opacity: 0.8; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Музыкальный Бот</h1>
        <input type="text" id="url" placeholder="Ссылка YouTube/Spotify/SoundCloud">
        <div class="buttons">
            <button onclick="sendAction('play')">Воспроизвести</button>
            <button onclick="sendAction('pause')">Пауза</button>
            <button onclick="sendAction('stop')">Стоп</button>
            <button onclick="sendAction('skip')">Следующий трек</button>
        </div>
        <div class="status" id="status">Готов к работе</div>
    </div>
    <script>
        async function sendAction(action) {
            const url = document.getElementById('url').value;
            const statusDiv = document.getElementById('status');
            statusDiv.innerText = 'Обработка...';
            
            try {
                const response = await fetch('/action', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({action, url})
                });
                const data = await response.json();
                statusDiv.innerText = data.message;
            } catch (e) {
                statusDiv.innerText = 'Ошибка соединения';
            }
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/action', methods=['POST'])
def action():
    data = request.json
    act = data.get('action')
    url = data.get('url')
    
    cog = bot.get_cog('MusicBot')
    if bot and bot.loop and cog:
        bot.loop.create_task(cog.handle_web_action(act, url))
        return jsonify({"message": f"Команда {act} отправлена"})
    return jsonify({"message": "Бот еще не запущен"}), 503

# Bot Setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

class MusicBot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.disconnect_timers = {}

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"Logged in as {self.bot.user}")
        await self.connect_lavalink()

    async def connect_lavalink(self):
        # Using a verified stable public node with correct protocol
        # lavalink.lexis.host is often stable
        node: wavelink.Node = wavelink.Node(uri='http://lavalink.lexis.host:80', password='youshallnotpass')
        try:
            await wavelink.NodePool.connect(client=self.bot, nodes=[node])
            print("Successfully connected to Lavalink node")
        except Exception as e:
            print(f"Failed to connect to Lavalink: {e}")

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.bot: return
        
        # Auto Join
        if after.channel:
            members = [m for m in after.channel.members if not m.bot]
            if len(members) >= 2:
                vc: wavelink.Player = member.guild.voice_client
                if not vc:
                    try:
                        vc = await after.channel.connect(cls=wavelink.Player)
                        # Send message to first available text channel
                        for channel in member.guild.text_channels:
                            if channel.permissions_for(member.guild.me).send_messages:
                                web_url = os.getenv('WEB_URL', 'http://localhost:5000')
                                await channel.send(f"🤖 Я подключился! Управляйте музыкой здесь: {web_url}")
                                break
                    except Exception as e:
                        print(f"Error connecting to voice: {e}")
                
                # Cancel disconnect timer if someone joined
                if member.guild.id in self.disconnect_timers:
                    self.disconnect_timers[member.guild.id].cancel()
                    del self.disconnect_timers[member.guild.id]

        # Auto Disconnect
        if before.channel:
            members = [m for m in before.channel.members if not m.bot]
            if len(members) == 0: # Everyone left
                if member.guild.id in self.disconnect_timers:
                    self.disconnect_timers[member.guild.id].cancel()
                self.disconnect_timers[member.guild.id] = asyncio.create_task(self.delayed_disconnect(member.guild))
            elif len(members) == 1: # Only 1 person left
                if member.guild.id not in self.disconnect_timers:
                    self.disconnect_timers[member.guild.id] = asyncio.create_task(self.delayed_disconnect(member.guild))

    async def delayed_disconnect(self, guild):
        await asyncio.sleep(300) # 5 minutes
        vc: wavelink.Player = guild.voice_client
        if vc:
            members = [m for m in vc.channel.members if not m.bot]
            if len(members) <= 1:
                await vc.disconnect()
        if guild.id in self.disconnect_timers:
            del self.disconnect_timers[guild.id]

    async def handle_web_action(self, action, url=None):
        if not self.bot.guilds: return
        guild = self.bot.guilds[0]
        vc: wavelink.Player = guild.voice_client
        
        if not vc: return 

        try:
            if action == 'play' and url:
                tracks = await wavelink.YouTubeTrack.search(url)
                if not tracks:
                    tracks = await wavelink.NodePool.get_node().get_tracks(wavelink.YouTubeTrack, url)
                
                if tracks:
                    track = tracks[0]
                    await vc.play(track)
            elif action == 'pause':
                await vc.set_pause(not vc.is_paused())
            elif action == 'stop':
                await vc.stop()
                await vc.disconnect()
            elif action == 'skip':
                await vc.stop()
        except Exception as e:
            print(f"Error handling web action {action}: {e}")

async def run_bot():
    await bot.add_cog(MusicBot(bot))
    await bot.start(os.getenv('DISCORD_TOKEN'))

def run_flask():
    app.run(host='0.0.0.0', port=5000)

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    asyncio.run(run_bot())
