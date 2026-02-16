import discord
from discord.ext import commands
import asyncio
import os
from threading import Thread
from flask import Flask, render_template_string, request, jsonify
import wavelink
from wavelink.ext import spotify

# Настройки
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# Flask приложение для веб-интерфейса
app = Flask(__name__)

# Глобальные переменные состояния
bot_state = {
    "connected": False,
    "channel_id": None,
    "guild_id": None,
    "disconnect_task": None,
    "current_track": None,
    "queue": []
}

# HTML интерфейс
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🎵 Music Bot Control</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        
        .container {
            background: rgba(255, 255, 255, 0.98);
            border-radius: 25px;
            padding: 40px;
            box-shadow: 0 25px 70px rgba(0,0,0,0.4);
            max-width: 600px;
            width: 100%;
            backdrop-filter: blur(10px);
        }
        
        h1 {
            text-align: center;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 10px;
            font-size: 2.5em;
            font-weight: 800;
        }
        
        .subtitle {
            text-align: center;
            color: #64748b;
            margin-bottom: 30px;
            font-size: 0.9em;
        }
        
        .input-section {
            margin-bottom: 25px;
        }
        
        label {
            display: block;
            margin-bottom: 8px;
            color: #475569;
            font-weight: 600;
            font-size: 0.95em;
        }
        
        input[type="text"] {
            width: 100%;
            padding: 15px 18px;
            border: 2px solid #e2e8f0;
            border-radius: 12px;
            font-size: 16px;
            transition: all 0.3s ease;
            background: white;
        }
        
        input[type="text"]:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }
        
        input[type="text"]::placeholder {
            color: #cbd5e1;
        }
        
        .controls {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 12px;
            margin-top: 25px;
        }
        
        button {
            padding: 16px;
            border: none;
            border-radius: 12px;
            font-size: 16px;
            font-weight: 700;
            cursor: pointer;
            transition: all 0.2s ease;
            color: white;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
        }
        
        .btn-play {
            background: linear-gradient(135deg, #10b981, #059669);
            grid-column: 1 / -1;
        }
        
        .btn-pause {
            background: linear-gradient(135deg, #f59e0b, #d97706);
        }
        
        .btn-stop {
            background: linear-gradient(135deg, #ef4444, #dc2626);
        }
        
        .btn-skip {
            background: linear-gradient(135deg, #3b82f6, #2563eb);
            grid-column: 1 / -1;
        }
        
        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 20px rgba(0,0,0,0.15);
        }
        
        button:active {
            transform: translateY(0);
        }
        
        button:disabled {
            opacity: 0.5;
            cursor: not-allowed;
            transform: none;
        }
        
        .status-card {
            margin-top: 30px;
            padding: 20px;
            background: linear-gradient(135deg, #f8fafc, #f1f5f9);
            border-radius: 15px;
            border: 2px solid #e2e8f0;
        }
        
        .status-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 0;
            border-bottom: 1px solid #e2e8f0;
        }
        
        .status-item:last-child {
            border-bottom: none;
        }
        
        .status-label {
            color: #64748b;
            font-weight: 600;
            font-size: 0.9em;
        }
        
        .status-value {
            color: #0f172a;
            font-weight: 700;
        }
        
        .now-playing {
            margin-top: 15px;
            padding: 15px;
            background: white;
            border-radius: 12px;
            border-left: 4px solid #667eea;
        }
        
        .now-playing-title {
            font-weight: 700;
            color: #667eea;
            margin-bottom: 5px;
            font-size: 0.9em;
        }
        
        .now-playing-track {
            color: #0f172a;
            font-size: 0.95em;
        }
        
        .loading {
            display: inline-block;
            width: 14px;
            height: 14px;
            border: 2px solid #667eea;
            border-radius: 50%;
            border-top-color: transparent;
            animation: spin 0.8s linear infinite;
        }
        
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        
        .hint {
            margin-top: 20px;
            padding: 15px;
            background: #fef3c7;
            border-radius: 12px;
            border-left: 4px solid #f59e0b;
            font-size: 0.85em;
            color: #92400e;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎵 Music Bot</h1>
        <div class="subtitle">Управление музыкой в Discord</div>
        
        <div class="input-section">
            <label for="songUrl">🔗 Ссылка на трек или плейлист</label>
            <input 
                type="text" 
                id="songUrl" 
                placeholder="YouTube, Spotify, SoundCloud..."
                autocomplete="off"
            >
        </div>
        
        <div class="controls">
            <button class="btn-play" onclick="play()">
                <span>▶</span> Воспроизвести
            </button>
            <button class="btn-pause" onclick="pause()">
                <span>⏸</span> Пауза
            </button>
            <button class="btn-stop" onclick="stop()">
                <span>⏹</span> Стоп
            </button>
            <button class="btn-skip" onclick="skip()">
                <span>⏭</span> Следующий трек
            </button>
        </div>
        
        <div class="status-card">
            <div class="status-item">
                <span class="status-label">Статус бота:</span>
                <span class="status-value" id="status">Загрузка...</span>
            </div>
            <div class="status-item">
                <span class="status-label">Подключен:</span>
                <span class="status-value" id="connected">Нет</span>
            </div>
            
            <div class="now-playing" id="nowPlayingBlock" style="display: none;">
                <div class="now-playing-title">🎵 Сейчас играет:</div>
                <div class="now-playing-track" id="nowPlaying">-</div>
            </div>
        </div>
        
        <div class="hint">
            💡 <strong>Подсказка:</strong> Бот подключится автоматически, когда 2+ человека зайдут в голосовой канал
        </div>
    </div>
    
    <script>
        async function play() {
            const url = document.getElementById('songUrl').value.trim();
            if (!url) {
                alert('⚠️ Вставь ссылку на трек!');
                return;
            }
            
            try {
                const res = await fetch('/play', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({url})
                });
                const data = await res.json();
                
                if (data.success) {
                    alert('✅ ' + data.message);
                    updateStatus();
                } else {
                    alert('❌ ' + data.message);
                }
            } catch (error) {
                alert('❌ Ошибка подключения к боту');
            }
        }
        
        async function pause() {
            try {
                const res = await fetch('/pause', {method: 'POST'});
                const data = await res.json();
                alert(data.success ? '⏸ Пауза' : '❌ ' + data.message);
                updateStatus();
            } catch (error) {
                alert('❌ Ошибка');
            }
        }
        
        async function stop() {
            try {
                const res = await fetch('/stop', {method: 'POST'});
                const data = await res.json();
                alert(data.success ? '⏹ Остановлено' : '❌ ' + data.message);
                updateStatus();
            } catch (error) {
                alert('❌ Ошибка');
            }
        }
        
        async function skip() {
            try {
                const res = await fetch('/skip', {method: 'POST'});
                const data = await res.json();
                alert(data.success ? '⏭ Следующий трек' : '❌ ' + data.message);
                updateStatus();
            } catch (error) {
                alert('❌ Ошибка');
            }
        }
        
        async function updateStatus() {
            try {
                const res = await fetch('/status');
                const data = await res.json();
                
                document.getElementById('status').textContent = data.status;
                document.getElementById('connected').textContent = data.connected ? 'Да ✅' : 'Нет ❌';
                
                if (data.now_playing) {
                    document.getElementById('nowPlayingBlock').style.display = 'block';
                    document.getElementById('nowPlaying').textContent = data.now_playing;
                } else {
                    document.getElementById('nowPlayingBlock').style.display = 'none';
                }
            } catch (error) {
                document.getElementById('status').textContent = 'Ошибка подключения';
            }
        }
        
        // Обновление статуса каждые 3 секунды
        setInterval(updateStatus, 3000);
        updateStatus();
    </script>
</body>
</html>
"""

# Flask маршруты
@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/play', methods=['POST'])
def play():
    try:
        data = request.json
        url = data.get('url')
        
        if not url:
            return jsonify({"success": False, "message": "Не указана ссылка"})
        
        # Добавляем трек в очередь
        bot_state["queue"].append(url)
        
        # Запускаем воспроизведение
        asyncio.run_coroutine_threadsafe(play_music(url), bot.loop)
        
        return jsonify({"success": True, "message": "Трек добавлен в очередь!"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route('/pause', methods=['POST'])
def pause():
    try:
        asyncio.run_coroutine_threadsafe(pause_music(), bot.loop)
        return jsonify({"success": True, "message": "Пауза"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route('/stop', methods=['POST'])
def stop():
    try:
        asyncio.run_coroutine_threadsafe(stop_music(), bot.loop)
        return jsonify({"success": True, "message": "Остановлено"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route('/skip', methods=['POST'])
def skip():
    try:
        asyncio.run_coroutine_threadsafe(skip_music(), bot.loop)
        return jsonify({"success": True, "message": "Следующий трек"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route('/status')
def status():
    return jsonify({
        "status": "Работает" if bot.is_ready() else "Загрузка",
        "connected": bot_state["connected"],
        "now_playing": bot_state["current_track"]
    })

# Музыкальные функции
async def play_music(url):
    try:
        if not bot_state["connected"]:
            return
        
        guild = bot.get_guild(bot_state["guild_id"])
        if not guild:
            return
        
        player = guild.voice_client
        if not player:
            return
        
        # Поиск трека
        tracks = await wavelink.YouTubeTrack.search(query=url, return_first=True)
        
        if not tracks:
            return
        
        bot_state["current_track"] = tracks.title
        await player.play(tracks)
        
    except Exception as e:
        print(f"Ошибка воспроизведения: {e}")

async def pause_music():
    try:
        if bot_state["guild_id"]:
            guild = bot.get_guild(bot_state["guild_id"])
            if guild and guild.voice_client:
                await guild.voice_client.pause()
    except Exception as e:
        print(f"Ошибка паузы: {e}")

async def stop_music():
    try:
        if bot_state["guild_id"]:
            guild = bot.get_guild(bot_state["guild_id"])
            if guild and guild.voice_client:
                await guild.voice_client.stop()
                bot_state["current_track"] = None
    except Exception as e:
        print(f"Ошибка остановки: {e}")

async def skip_music():
    try:
        if bot_state["guild_id"]:
            guild = bot.get_guild(bot_state["guild_id"])
            if guild and guild.voice_client:
                await guild.voice_client.stop()
    except Exception as e:
        print(f"Ошибка пропуска: {e}")

# События Discord бота
@bot.event
async def on_ready():
    print(f'✅ Бот {bot.user} запущен и готов к работе!')
    print(f'📊 Серверов: {len(bot.guilds)}')
    
    # Подключение к Lavalink
    try:
        node = wavelink.Node(
            uri='http://lavalink.darrennathanael.com:80',
            password='default'
        )
        await wavelink.Pool.connect(client=bot, nodes=[node])
        print('✅ Подключено к Lavalink')
    except Exception as e:
        print(f'❌ Ошибка подключения к Lavalink: {e}')

@bot.event
async def on_voice_state_update(member, before, after):
    # Игнорируем ботов
    if member.bot:
        return
    
    # Проверяем изменения в голосовых каналах
    if after.channel:
        # Считаем реальных пользователей (не ботов)
        users = [m for m in after.channel.members if not m.bot]
        
        # Если 2+ человека и бот еще не подключен
        if len(users) >= 2 and not bot_state["connected"]:
            try:
                # Подключаемся к каналу
                player = await after.channel.connect(cls=wavelink.Player)
                bot_state["connected"] = True
                bot_state["channel_id"] = after.channel.id
                bot_state["guild_id"] = after.channel.guild.id
                
                # Отправляем ссылку на веб-интерфейс
                text_channel = member.guild.system_channel or member.guild.text_channels[0]
                web_url = os.environ.get('WEB_URL', 'http://localhost:5000')
                
                embed = discord.Embed(
                    title="🎵 Музыкальный бот подключен!",
                    description=f"Управляйте музыкой через веб-интерфейс:",
                    color=0x667eea
                )
                embed.add_field(name="🔗 Ссылка", value=f"[Открыть панель управления]({web_url})", inline=False)
                embed.add_field(name="💡 Подсказка", value="Вставьте ссылку на YouTube, Spotify или SoundCloud", inline=False)
                embed.set_footer(text="Бот отключится через 5 минут, если останется 1 человек")
                
                await text_channel.send(embed=embed)
                
                print(f'✅ Подключился к каналу: {after.channel.name}')
                
            except Exception as e:
                print(f'❌ Ошибка подключения: {e}')
        
        # Если остался 1 человек - запускаем таймер
        elif len(users) == 1 and bot_state["connected"]:
            if bot_state["disconnect_task"]:
                bot_state["disconnect_task"].cancel()
            
            bot_state["disconnect_task"] = asyncio.create_task(disconnect_timer())
            print('⏱ Таймер отключения запущен (5 минут)')
        
        # Если снова 2+ человека - отменяем таймер
        elif len(users) >= 2 and bot_state["disconnect_task"]:
            bot_state["disconnect_task"].cancel()
            bot_state["disconnect_task"] = None
            print('✅ Таймер отключения отменен')
    
    # Если все вышли из канала
    elif before.channel and bot_state["connected"]:
        users = [m for m in before.channel.members if not m.bot]
        if len(users) == 0:
            await disconnect_bot()

async def disconnect_timer():
    """Таймер на 5 минут перед отключением"""
    try:
        await asyncio.sleep(300)  # 5 минут = 300 секунд
        await disconnect_bot()
        print('⏱ Бот отключен по таймеру')
    except asyncio.CancelledError:
        print('⏱ Таймер отменен')

async def disconnect_bot():
    """Отключение бота от голосового канала"""
    try:
        if bot_state["guild_id"]:
            guild = bot.get_guild(bot_state["guild_id"])
            if guild and guild.voice_client:
                await guild.voice_client.disconnect()
        
        bot_state["connected"] = False
        bot_state["channel_id"] = None
        bot_state["guild_id"] = None
        bot_state["current_track"] = None
        bot_state["disconnect_task"] = None
        
        print('👋 Бот отключен от голосового канала')
    except Exception as e:
        print(f'❌ Ошибка отключения: {e}')

# Запуск Flask в отдельном потоке
def run_flask():
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

# Главная функция запуска
if __name__ == '__main__':
    # Проверка токена
    token = os.environ.get('DISCORD_TOKEN')
    if not token:
        print('❌ ОШИБКА: Не найден DISCORD_TOKEN в переменных окружения!')
        print('📝 Создай переменную окружения DISCORD_TOKEN с токеном бота')
        exit(1)
    
    # Запускаем Flask в отдельном потоке
    flask_thread = Thread(target=run_flask, daemon=True)
    flask_thread.start()
    print('✅ Веб-сервер запущен')
    
    # Запускаем Discord бота
    try:
        bot.run(token)
    except Exception as e:
        print(f'❌ Ошибка запуска бота: {e}')
