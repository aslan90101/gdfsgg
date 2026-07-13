import json
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime

connected_accounts = {}
command_queue = {}

WEBHOOK_URL = "https://discord.com/api/webhooks/1526233781135216785/t80ZHnnjkgrnncWE7qfEFa89UZ4FfXj6BzV-Taws7hd-rxnN6TMkUb5qJTAhVA1C9ar2"

def send_discord_msg(content):
    import urllib.request
    try:
        data = json.dumps({"content": content}).encode("utf-8")
        req = urllib.request.Request(WEBHOOK_URL, data=data, headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=5)
    except Exception as e:
        print(f"Discord send error: {e}")

class TrackerHandler(BaseHTTPRequestHandler):

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)

        if self.path == "/report":
            try:
                data = json.loads(body.decode("utf-8"))
                account = data.get("account", "?")
                user_id = data.get("userId", "?")
                connected_accounts[account] = {
                    "userId": user_id,
                    "last_seen": datetime.now().strftime("%H:%M:%S"),
                }
                now = datetime.now().strftime("%H:%M:%S")
                total = len(connected_accounts)
                print(f"[{now}] ONLINE ({total}) | {account} (ID: {user_id})")
                send_discord_msg(f":white_check_mark: **{account}** (ID: {user_id}) connected | Total: {total}")
            except Exception as e:
                print(f"Error: {e}")

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(b'{"ok":true}')
        else:
            self.send_response(404)
            self.end_headers()

    def do_GET(self):
        if self.path.startswith("/commands/"):
            account = self.path.split("/commands/", 1)[1]
            if account in command_queue:
                cmd = command_queue.pop(account)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps(cmd).encode("utf-8"))
            else:
                self.send_response(204)
                self.end_headers()
        elif self.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            now = datetime.now().strftime("%H:%M:%S")
            rows = ""
            for name, info in sorted(connected_accounts.items()):
                rows += f"<tr><td>{name}</td><td>{info['userId']}</td><td>{info['last_seen']}</td></tr>\n"
            html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Account Tracker</title>
<meta http-equiv="refresh" content="3">
<style>
body {{ background:#111; color:#eee; font-family:monospace; padding:20px; }}
h1 {{ color:#0f0; }}
table {{ border-collapse:collapse; width:100%; }}
th,td {{ border:1px solid #444; padding:8px 12px; text-align:left; }}
th {{ background:#222; color:#0f0; }}
</style></head>
<body>
<h1>Account Tracker</h1>
<p>Total connected: {len(connected_accounts)} | Updated: {now}</p>
<table><tr><th>Account</th><th>UserId</th><th>Last Seen</th></tr>
{rows}</table>
</body></html>"""
            self.wfile.write(html.encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def log_message(self, fmt, *args):
        pass


def start_bot():
    try:
        import discord
        from discord.ext import commands

        intents = discord.Intents.default()
        intents.message_content = True
        bot = commands.Bot(command_prefix="!", intents=intents)

        @bot.event
        async def on_ready():
            print(f"[BOT] Logged in as {bot.user}")

        @bot.command()
        async def kick(ctx, *, player_name: str = None):
            if not player_name:
                await ctx.send("Usage: `!kick PlayerName`")
                return
            command_queue[player_name] = {"command": "kick", "from": str(ctx.author), "time": datetime.now().strftime("%H:%M:%S")}
            await ctx.send(f":boot: Kick command queued for **{player_name}**")
            print(f"[CMD] Kick -> {player_name} (by {ctx.author})")

        @bot.command()
        async def bring(ctx, *, player_name: str = None):
            if not player_name:
                await ctx.send("Usage: `!bring PlayerName`")
                return
            command_queue[player_name] = {"command": "bring", "from": str(ctx.author), "time": datetime.now().strftime("%H:%M:%S")}
            await ctx.send(f":arrow_up: Bring command queued for **{player_name}**")
            print(f"[CMD] Bring -> {player_name} (by {ctx.author})")

        @bot.command()
        async def freeze(ctx, *, player_name: str = None):
            if not player_name:
                await ctx.send("Usage: `!freeze PlayerName`")
                return
            command_queue[player_name] = {"command": "freeze", "from": str(ctx.author), "time": datetime.now().strftime("%H:%M:%S")}
            await ctx.send(f":ice_cube: Freeze command queued for **{player_name}**")
            print(f"[CMD] Freeze -> {player_name} (by {ctx.author})")

        @bot.command()
        async def unfreeze(ctx, *, player_name: str = None):
            if not player_name:
                await ctx.send("Usage: `!unfreeze PlayerName`")
                return
            command_queue[player_name] = {"command": "unfreeze", "from": str(ctx.author), "time": datetime.now().strftime("%H:%M:%S")}
            await ctx.send(f":fire: Unfreeze command queued for **{player_name}**")
            print(f"[CMD] Unfreeze -> {player_name} (by {ctx.author})")

        @bot.command()
        async def listplayers(ctx):
            if not connected_accounts:
                await ctx.send("No players connected.")
                return
            lines = []
            for name, info in connected_accounts.items():
                lines.append(f"- **{name}** (ID: {info['userId']}) - last seen: {info['last_seen']}")
            await ctx.send("\n".join(lines))

        token = os.environ.get("DISCORD_BOT_TOKEN", "")
        if not token:
            print("[BOT] No DISCORD_BOT_TOKEN set. Bot disabled.")
            print("[BOT] Set it with: set DISCORD_BOT_TOKEN=your_token_here")
            return

        bot.run(token)
    except ImportError:
        print("[BOT] discord.py not installed. Run: pip install discord.py")
    except Exception as e:
        print(f"[BOT] Error: {e}")


if __name__ == "__main__":
    port = 5000

    bot_thread = threading.Thread(target=start_bot, daemon=True)
    bot_thread.start()

    server = HTTPServer(("0.0.0.0", port), TrackerHandler)
    banner = f"""
===============================================
  Account Tracker + Command Server
  Listening on 0.0.0.0:{port}
  Web panel: http://localhost:{port}
===============================================
  Commands:
    !kick PlayerName
    !bring PlayerName
    !freeze PlayerName
    !unfreeze PlayerName
    !listplayers
===============================================
"""
    print(banner)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.server_close()
