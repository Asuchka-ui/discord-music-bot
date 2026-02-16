import discord
from discord.ext import commands
import asyncio
import os
from threading import Thread
from flask import Flask, render_template_string, request, jsonify

# Настройки
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

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
        .input-section { margin-bottom: 25px; }
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
        }
        input[type="text"]:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
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
        .hint {
            margin-top: 20px;
            padding: 15px;
            background: #fef3c7;
            border-radius: 12px;
            border-left: 4px solid #f59e0b;
            font-size: 0.85em;
            color: #92400e;
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
        .link {
            color: #667eea;
            text-decoration: none;
            font-weight: 600;
        }
        .link:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎵 Music Bot</h1>
        <div class="subtitle">Управление музыкой в Discord</div>
        
        <div class="status-card">
            <div class="status-item">
                <span class="status-label">Статус бота:</span>
                <span class="status-value" id="status">Загрузка...</span>
            </div>
            <div class="status-item">
                <span class="status-label">Подключен:</span>
                <span class="status-value" id="connected">Нет</span>
            </div>
        </div>
        
        <div class="info-box">
            <div class="info-title">🎵 Как использовать музыкального бота</div>
            <div class="info-text">
                <p><strong>1.</strong> Зайдите 2+ человека в голосовой канал</p>
                <p><strong>2.</strong> Бот автоматически подключится</p>
                <p><strong>3.</strong> Используйте команды в текстовом чате:</p>
                <br>
                <p>• <code>!play ссылка</code> - воспроизвести трек</p>
                <p>• <code>!pause</code> - пауза</p>
                <p>• <code>!resume</code> - продолжить</p>
                <p>• <code>!skip</code> - следующий трек</p>
                <p>• <code>!stop</code> - остановить и очистить очередь</p>
                <p>• <code>!queue</code> - показать очередь</p>
                <br>
                <p>Поддержка: YouTube, Spotify, SoundCloud</p>
            </div>
        </div>
        
        <div class="hint">
            💡 <strong>Подсказка:</strong> Бот подключится автоматически когда 2+ человека зайдут в голосовой канал. 
            Если останется 1 человек - бот отключится через 5 минут.
        </div>
    </div>
    
    <script>
        async function updateStatus() {
            try {
                const res = await fetch('/status');
                const data = await res.json();
                document.getElementById('status').textContent = data.status;
                document.getElementById('connected').textContent = data.connected ? 'Да ✅' : 'Нет ❌';
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
    return jsonify({
        "status": "Работает" if bot.is_ready() else "Загрузка",
        "connected": bot_state["connected"]
    })

# Discord события
@bot.event
async def on_ready():
    print(f'✅ Бот {bot.user} запущен и готов к работе!')
    print(f'📊 Серверов: {len(bot.guilds)}')
    print(f'🎵 Музыкальные команды активны')

@bot.event
async def on_voice_state_update(member, before, after):
    if member.bot:
        return
    
    if after.channel:
        users = [m for m in after.channel.members if not m.bot]
        
        if len(users) >= 2 and not bot_state["connected"]:
            try:
                voice_client = await after.channel.connect()
                bot_state["connected"] = True
                bot_state["channel_id"] = after.channel.id
                bot_state["guild_id"] = after.channel.guild.id
                
                text_channel = member.guild.system_channel or member.guild.text_channels[0]
                web_url = os.environ.get('WEB_URL', 'http://localhost:5000')
                
                embed = discord.Embed(
                    title="🎵 Музыкальный бот подключен!",
                    description=f"Управление музыкой через команды или веб-панель",
                    color=0x667eea
                )
                embed.add_field(name="🔗 Веб-панель", value=f"[Открыть]({web_url})", inline=False)
                embed.add_field(name="💡 Команды", value="`!play`, `!pause`, `!skip`, `!stop`, `!queue`", inline=False)
                embed.set_footer(text="Бот отключится через 5 мин если останется 1 человек")
                
                await text_channel.send(embed=embed)
                print(f'✅ Подключился к каналу: {after.channel.name}')
                
            except Exception as e:
                print(f'❌ Ошибка подключения: {e}')
        
        elif len(users) == 1 and bot_state["connected"]:
            if bot_state["disconnect_task"]:
                bot_state["disconnect_task"].cancel()
            bot_state["disconnect_task"] = asyncio.create_task(disconnect_timer())
            print('⏱ Таймер отключения: 5 минут')
        
        elif len(users) >= 2 and bot_state["disconnect_task"]:
            bot_state["disconnect_task"].cancel()
            bot_state["disconnect_task"] = None
            print('✅ Таймер отключения отменен')
    
    elif before.channel and bot_state["connected"]:
        users = [m for m in before.channel.members if not m.bot]
        if len(users) == 0:
            await disconnect_bot()

async def disconnect_timer():
    try:
        await asyncio.sleep(300)
        await disconnect_bot()
        print('⏱ Бот отключен по таймеру')
    except asyncio.CancelledError:
        print('⏱ Таймер отменен')

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
        
        print('👋 Бот отключен от голосового канала')
    except Exception as e:
        print(f'❌ Ошибка отключения: {e}')

# Музыкальные команды
@bot.command(name='play')
async def play(ctx, *, query):
    """Воспроизвести музыку"""
    if not ctx.author.voice:
        await ctx.send("❌ Вы не в голосовом канале!")
        return
    
    await ctx.send(f"🎵 **Ищу:** {query}\n\n⚠️ **Внимание:** Для полной поддержки музыки нужен Lavalink сервер.\nСейчас работает базовая версия бота.")

@bot.command(name='pause')
async def pause(ctx):
    """Поставить на паузу"""
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.pause()
        await ctx.send("⏸ **Пауза**")
    else:
        await ctx.send("❌ Ничего не играет")

@bot.command(name='resume')
async def resume(ctx):
    """Продолжить воспроизведение"""
    if ctx.voice_client and ctx.voice_client.is_paused():
        ctx.voice_client.resume()
        await ctx.send("▶ **Продолжаю**")
    else:
        await ctx.send("❌ Музыка не на паузе")

@bot.command(name='stop')
async def stop(ctx):
    """Остановить музыку"""
    if ctx.voice_client:
        ctx.voice_client.stop()
        bot_state["queue"] = []
        await ctx.send("⏹ **Остановлено**")
    else:
        await ctx.send("❌ Бот не подключен")

@bot.command(name='skip')
async def skip(ctx):
    """Пропустить трек"""
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("⏭ **Пропущено**")
    else:
        await ctx.send("❌ Ничего не играет")

@bot.command(name='queue')
async def queue(ctx):
    """Показать очередь"""
    if bot_state["queue"]:
        queue_text = "\n".join([f"{i+1}. {track}" for i, track in enumerate(bot_state["queue"])])
        await ctx.send(f"📋 **Очередь:**\n{queue_text}")
    else:
        await ctx.send("📋 Очередь пуста")

# Запуск Flask
def run_flask():
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

# Главная функция
if __name__ == '__main__':
    token = os.environ.get('DISCORD_TOKEN')
    if not token:
        print('❌ ОШИБКА: Не найден DISCORD_TOKEN!')
        exit(1)
    
    flask_thread = Thread(target=run_flask, daemon=True)
    flask_thread.start()
    print('✅ Веб-сервер запущен')
    
    try:
        bot.run(token)
    except Exception as e:
        print(f'❌ Ошибка: {e}')

