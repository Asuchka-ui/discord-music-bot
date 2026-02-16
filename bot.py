import discord
from discord.ext import commands
import asyncio
import os
from threading import Thread
from flask import Flask, render_template_string, request, jsonify

# Настройки
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# Flask приложение
app = Flask(__name__)

# Состояние бота
bot_state = {
    "connected": False,
    "channel_id": None,
    "guild_id": None,
    "disconnect_task": None,
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
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
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
        .status-card {
            margin-top: 20px;
            padding: 20px;
            background: linear-gradient(135deg, #f8fafc, #f1f5f9);
            border-radius: 15px;
            border: 2px solid #e2e8f0;
        }
        .status-item {
            display: flex;
            justify-content: space-between;
            padding: 10px 0;
            border-bottom: 1px solid #e2e8f0;
        }
        .status-item:last-child { border-bottom: none; }
        .status-label {
            color: #64748b;
            font-weight: 600;
            font-size: 0.9em;
        }
        .status-value {
            color: #0f172a;
            font-weight: 700;
        }
        .info-box {
            margin-top: 20px;
            padding: 20px;
            background: #e0e7ff;
            border-radius: 12px;
            border-left: 4px solid #667eea;
        }
        .info-title {
            font-weight: 700;
            color: #3730a3;
            margin-bottom: 10px;
            font-size: 1.1em;
        }
        .info-text {
            color: #4338ca;
            font-size: 0.9em;
            line-height: 1.6;
        }
        code {
            background: #ddd6fe;
            padding: 2px 6px;
            border-radius: 4px;
            font-family: monospace;
            color: #5b21b6;
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
        <div class="subtitle">Автоматический музыкальный бот для Discord</div>
        
        <div class="status-card">
            <div class="status-item">
                <span class="status-label">Статус бота:</span>
                <span class="status-value" id="status">Загрузка...</span>
            </div>
            <div class="status-item">
                <span class="status-label">Подключен к каналу:</span>
                <span class="status-value" id="connected">Нет</span>
            </div>
            <div class="status-item">
                <span class="status-label">Людей в канале:</span>
                <span class="status-value" id="users">0</span>
            </div>
        </div>
        
        <div class="info-box">
            <div class="info-title">🎵 Как использовать бота</div>
            <div class="info-text">
                <p><strong>1. Автоматическое подключение:</strong></p>
                <p style="margin-left: 15px;">Зайдите 2+ человека в голосовой канал - бот автоматически подключится!</p>
                <br>
                <p><strong>2. Команды в Discord чате:</strong></p>
                <p style="margin-left: 15px;">• <code>!play ссылка</code> - воспроизвести трек с YouTube</p>
                <p style="margin-left: 15px;">• <code>!pause</code> - поставить на паузу</p>
                <p style="margin-left: 15px;">• <code>!resume</code> - продолжить воспроизведение</p>
                <p style="margin-left: 15px;">• <code>!skip</code> - пропустить текущий трек</p>
                <p style="margin-left: 15px;">• <code>!stop</code> - остановить и очистить очередь</p>
                <p style="margin-left: 15px;">• <code>!queue</code> - показать очередь треков</p>
                <p style="margin-left: 15px;">• <code>!np</code> - что сейчас играет</p>
                <br>
                <p><strong>3. Примеры использования:</strong></p>
                <p style="margin-left: 15px;"><code>!play https://youtube.com/watch?v=...</code></p>
                <p style="margin-left: 15px;"><code>!play название песни</code></p>
                <br>
                <p><strong>4. Автоотключение:</strong></p>
                <p style="margin-left: 15px;">Если останется 1 человек - бот отключится через 5 минут</p>
            </div>
        </div>
        
        <div class="hint">
            💡 <strong>Подсказка:</strong> Бот работает полностью автоматически. Просто зайдите в голосовой канал с другом и используйте команды!
        </div>
    </div>
    
    <script>
        async function updateStatus() {
            try {
                const res = await fetch('/status');
                const data = await res.json();
                document.getElementById('status').textContent = data.status;
                document.getElementById('connected').textContent = data.connected ? 'Да ✅' : 'Нет ❌';
                document.getElementById('users').textContent = data.users || '0';
            } catch (error) {
                document.getElementById('status').textContent = 'Ошибка подключения';
            }
        }
        setInterval(updateStatus, 3000);
        updateStatus();
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/status')
def status():
    users_count = 0
    if bot_state["connected"] and bot_state["guild_id"]:
        guild = bot.get_guild(bot_state["guild_id"])
        if guild:
            channel = guild.get_channel(bot_state["channel_id"])
            if channel:
                users_count = len([m for m in channel.members if not m.bot])
    
    return jsonify({
        "status": "Работает ✅" if bot.is_ready() else "Загрузка...",
        "connected": bot_state["connected"],
        "users": users_count
    })

# Discord события
@bot.event
async def on_ready():
    print('=' * 50)
    print(f'✅ Бот успешно запущен!')
    print(f'📝 Имя бота: {bot.user}')
    print(f'🆔 ID: {bot.user.id}')
    print(f'📊 Серверов: {len(bot.guilds)}')
    print(f'🎵 Музыкальные команды активны')
    print('=' * 50)

@bot.event
async def on_voice_state_update(member, before, after):
    if member.bot:
        return
    
    if after.channel:
        users = [m for m in after.channel.members if not m.bot]
        
        # Подключение при 2+ людях
        if len(users) >= 2 and not bot_state["connected"]:
            try:
                voice_client = await after.channel.connect()
                bot_state["connected"] = True
                bot_state["channel_id"] = after.channel.id
                bot_state["guild_id"] = after.channel.guild.id
                
                text_channel = member.guild.system_channel
                if not text_channel:
                    text_channel = next((ch for ch in member.guild.text_channels if ch.permissions_for(member.guild.me).send_messages), None)
                
                if text_channel:
                    web_url = os.environ.get('WEB_URL', 'http://localhost:5000')
                    
                    embed = discord.Embed(
                        title="🎵 Музыкальный бот подключен!",
                        description="Готов воспроизводить музыку",
                        color=0x667eea
                    )
                    embed.add_field(
                        name="🔗 Веб-панель", 
                        value=f"[Открыть панель управления]({web_url})", 
                        inline=False
                    )
                    embed.add_field(
                        name="💡 Основные команды", 
                        value="`!play`, `!pause`, `!resume`, `!skip`, `!stop`, `!queue`", 
                        inline=False
                    )
                    embed.add_field(
                        name="📖 Пример", 
                        value="`!play https://youtube.com/watch?v=...`", 
                        inline=False
                    )
                    embed.set_footer(text="Бот отключится через 5 мин если останется 1 человек")
                    
                    await text_channel.send(embed=embed)
                
                print(f'✅ Подключен к: {after.channel.name} ({len(users)} человек)')
                
            except Exception as e:
                print(f'❌ Ошибка подключения: {e}')
        
        # Таймер при 1 человеке
        elif len(users) == 1 and bot_state["connected"]:
            if bot_state["disconnect_task"]:
                bot_state["disconnect_task"].cancel()
            bot_state["disconnect_task"] = asyncio.create_task(disconnect_timer())
            print('⏱ Таймер отключения: 5 минут')
        
        # Отмена таймера
        elif len(users) >= 2 and bot_state["disconnect_task"]:
            bot_state["disconnect_task"].cancel()
            bot_state["disconnect_task"] = None
            print('✅ Таймер отменен')
    
    # Отключение если все вышли
    elif before.channel and bot_state["connected"]:
        users = [m for m in before.channel.members if not m.bot]
        if len(users) == 0:
            await disconnect_bot()

async def disconnect_timer():
    try:
        await asyncio.sleep(300)  # 5 минут
        await disconnect_bot()
        print('⏱ Бот отключен по таймеру')
    except asyncio.CancelledError:
        pass

async def disconnect_bot():
    try:
        if bot_state["guild_id"]:
            guild = bot.get_guild(bot_state["guild_id"])
            if guild and guild.voice_client:
                await guild.voice_client.disconnect()
        
        bot_state["connected"] = False
        bot_state["channel_id"] = None
        bot_state["guild_id"] = None
        bot_state["queue"] = []
        bot_state["disconnect_task"] = None
        
        print('👋 Отключен от голосового канала')
    except Exception as e:
        print(f'❌ Ошибка отключения: {e}')

# Команды
@bot.command(name='play')
async def play(ctx, *, query):
    """Воспроизвести музыку"""
    if not ctx.author.voice:
        await ctx.send("❌ Вы не в голосовом канале!")
        return
    
    bot_state["queue"].append(query)
    await ctx.send(f"✅ Добавлено в очередь: **{query}**\n\n⚠️ Для полного воспроизведения нужен Lavalink сервер (дополнительная настройка)")

@bot.command(name='pause')
async def pause_cmd(ctx):
    """Пауза"""
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.pause()
        await ctx.send("⏸ **Пауза**")
    else:
        await ctx.send("❌ Ничего не играет")

@bot.command(name='resume')
async def resume_cmd(ctx):
    """Продолжить"""
    if ctx.voice_client and ctx.voice_client.is_paused():
        ctx.voice_client.resume()
        await ctx.send("▶ **Продолжаю**")
    else:
        await ctx.send("❌ На паузе ничего нет")

@bot.command(name='stop')
async def stop_cmd(ctx):
    """Остановить"""
    if ctx.voice_client:
        ctx.voice_client.stop()
        bot_state["queue"] = []
        await ctx.send("⏹ **Остановлено и очередь очищена**")
    else:
        await ctx.send("❌ Не подключен")

@bot.command(name='skip')
async def skip_cmd(ctx):
    """Пропустить"""
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("⏭ **Пропущено**")
    else:
        await ctx.send("❌ Ничего не играет")

@bot.command(name='queue', aliases=['q'])
async def queue_cmd(ctx):
    """Очередь"""
    if bot_state["queue"]:
        queue_text = "\n".join([f"{i+1}. {track}" for i, track in enumerate(bot_state["queue"][:10])])
        await ctx.send(f"📋 **Очередь:**\n{queue_text}")
    else:
        await ctx.send("📋 Очередь пуста")

@bot.command(name='np', aliases=['nowplaying'])
async def now_playing(ctx):
    """Что играет"""
    if ctx.voice_client and ctx.voice_client.is_playing():
        await ctx.send("🎵 **Сейчас играет:** (требуется Lavalink для отображения)")
    else:
        await ctx.send("❌ Ничего не играет")

# Запуск Flask
def run_flask():
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

# Главная функция
if __name__ == '__main__':
    token = os.environ.get('DISCORD_TOKEN')
    if not token:
        print('❌ ОШИБКА: DISCORD_TOKEN не найден!')
        print('Добавьте переменную окружения DISCORD_TOKEN')
        exit(1)
    
    print('🚀 Запуск веб-сервера...')
    flask_thread = Thread(target=run_flask, daemon=True)
    flask_thread.start()
    print('✅ Веб-сервер запущен')
    
    print('🤖 Запуск Discord бота...')
    try:
        bot.run(token)
    except Exception as e:
        print(f'❌ Критическая ошибка: {e}')
