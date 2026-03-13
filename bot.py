import discord
from discord.ext import commands
import time
import json
import os
import re

TOKEN = os.getenv("TOKEN")

BUTTON_CHANNEL_ID = 1482009837062721596
POST_CHANNEL_ID = 1482009887658606643
LOG_CHANNEL_ID = 1482004336866492629

DATA_FILE = "anon_data.json"
REPLY_FILE = "reply_data.json"
LINK_FILE = "anon_links.json"

COOLDOWN_TIME = 10

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

cooldowns = {}

# -----------------------
# JSON
# -----------------------

def load_json(file, default):
    if os.path.exists(file):
        with open(file) as f:
            return json.load(f)
    return default


def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f)


anon_data = load_json(DATA_FILE, {"count": 0})
reply_data = load_json(REPLY_FILE, {"reply": 0})
anon_links = load_json(LINK_FILE, {})

# -----------------------
# Modal
# -----------------------

class AnonModal(discord.ui.Modal, title="匿名投稿"):

    message = discord.ui.TextInput(
        label="投稿内容",
        style=discord.TextStyle.paragraph,
        required=False
    )

    async def on_submit(self, interaction: discord.Interaction):

        user_id = interaction.user.id
        now = time.time()

        if user_id in cooldowns:
            remain = COOLDOWN_TIME - (now - cooldowns[user_id])
            if remain > 0:
                await interaction.response.send_message(
                    f"{int(remain)}秒待ってください",
                    ephemeral=True
                )
                return

        cooldowns[user_id] = now

        anon_data["count"] += 1
        save_json(DATA_FILE, anon_data)

        number = anon_data["count"]

        text = self.message.value if self.message.value else "（内容なし）"

        embed = discord.Embed(
            title=f"匿名 #{number}",
            description=text,
            color=0x5865F2
        )

        channel = bot.get_channel(POST_CHANNEL_ID)
        msg = await channel.send(embed=embed)

        anon_links[str(number)] = msg.jump_url
        save_json(LINK_FILE, anon_links)

        log = bot.get_channel(LOG_CHANNEL_ID)
        if log:
            await log.send(f"匿名 #{number}\n投稿者:{interaction.user}\n{text}")

        await interaction.response.send_message("投稿しました", ephemeral=True)

# -----------------------
# Button
# -----------------------

class AnonView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="匿名投稿",
        style=discord.ButtonStyle.primary,
        custom_id="anon_post"
    )
    async def post(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(AnonModal())

# -----------------------
# Setup
# -----------------------

@bot.command()
async def setup(ctx):

    channel = bot.get_channel(BUTTON_CHANNEL_ID)

    async for msg in channel.history(limit=20):
        if msg.author == bot.user:
            await msg.delete()

    await channel.send(
        "匿名掲示板\nボタンか画像送信で投稿できます",
        view=AnonView()
    )

# -----------------------
# Message Event
# -----------------------

@bot.event
async def on_message(message):

    if message.author.bot:
        return

    # -----------------------
    # 画像匿名投稿
    # -----------------------

    if message.channel.id == BUTTON_CHANNEL_ID:

        if message.attachments or message.content:

            files = []

            for attachment in message.attachments:
                file = await attachment.to_file()
                files.append(file)

            await message.delete()

            anon_data["count"] += 1
            save_json(DATA_FILE, anon_data)

            number = anon_data["count"]

            text = message.content if message.content else "（画像投稿）"

            embed = discord.Embed(
                title=f"匿名 #{number}",
                description=text,
                color=0x5865F2
            )

            if message.attachments:
                embed.set_image(url=message.attachments[0].url)

            channel = bot.get_channel(POST_CHANNEL_ID)

            msg = await channel.send(embed=embed, files=files)

            anon_links[str(number)] = msg.jump_url
            save_json(LINK_FILE, anon_links)

            log = bot.get_channel(LOG_CHANNEL_ID)

            if log:
                await log.send(f"匿名 #{number}\n投稿者:{message.author}\n{text}")

            return

    # -----------------------
    # 返信
    # -----------------------

    if message.channel.id == POST_CHANNEL_ID:

        content = message.content
        attachments = message.attachments

        await message.delete()

        reply_data["reply"] += 1
        save_json(REPLY_FILE, reply_data)

        rnum = reply_data["reply"]

        anchors = re.findall(r">>(\d+)", content)

        anchor_text = ""

        for a in anchors:

            if a in anon_links:
                link = anon_links[a]
                anchor_text += f"🔗 [>>{a}]({link}) "
            else:
                anchor_text += f">>{a} "

        files = []

        for attachment in attachments:
            file = await attachment.to_file()
            files.append(file)

        embed = discord.Embed(
            title=f"返信 #{rnum}",
            description=f"{anchor_text}\n{content}",
            color=0x2ecc71
        )

        await message.channel.send(embed=embed, files=files)

    await bot.process_commands(message)

# -----------------------
# Ready
# -----------------------

@bot.event
async def on_ready():
    bot.add_view(AnonView())
    print("Bot起動")

bot.run(TOKEN)
