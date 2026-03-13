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

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

cooldowns = {}
COOLDOWN_TIME = 10

DATA_FILE = "anon_data.json"
REPLY_FILE = "reply_data.json"


def load_count():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE) as f:
            return json.load(f).get("count", 0)
    return 0


def save_count(count):
    with open(DATA_FILE, "w") as f:
        json.dump({"count": count}, f)


def load_reply():
    if os.path.exists(REPLY_FILE):
        with open(REPLY_FILE) as f:
            return json.load(f)
    return {"reply": 0}


def save_reply(data):
    with open(REPLY_FILE, "w") as f:
        json.dump(data, f)


anon_count = load_count()
reply_data = load_reply()


class AnonModal(discord.ui.Modal, title="匿名投稿"):

    message = discord.ui.TextInput(
        label="投稿内容",
        style=discord.TextStyle.paragraph,
        required=False
    )

    async def on_submit(self, interaction: discord.Interaction):

        global anon_count

        user_id = interaction.user.id
        now = time.time()

        if user_id in cooldowns:
            remaining = COOLDOWN_TIME - (now - cooldowns[user_id])
            if remaining > 0:
                await interaction.response.send_message(
                    f"あと {int(remaining)} 秒待ってください",
                    ephemeral=True
                )
                return

        cooldowns[user_id] = now

        anon_count += 1
        save_count(anon_count)

        channel = bot.get_channel(POST_CHANNEL_ID)
        log_channel = bot.get_channel(LOG_CHANNEL_ID)

        content = self.message.value if self.message.value else "（画像のみ投稿）"

        embed = discord.Embed(
            title=f"匿名 #{anon_count}",
            description=content,
            color=0x2F3136
        )

        await channel.send(embed=embed)

        if log_channel:
            await log_channel.send(
                f"匿名 #{anon_count}\n投稿者: {interaction.user}\n内容: {content}"
            )

        await interaction.response.send_message(
            "投稿しました",
            ephemeral=True
        )


class AnonView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="匿名投稿する",
        style=discord.ButtonStyle.primary,
        custom_id="anon_post"
    )
    async def anon_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(AnonModal())


@bot.command()
async def setup(ctx):

    channel = bot.get_channel(BUTTON_CHANNEL_ID)

    async for msg in channel.history(limit=20):
        if msg.author == bot.user:
            await msg.delete()

    await channel.send(
        "匿名投稿\n下のボタンから投稿できます",
        view=AnonView()
    )


@bot.event
async def on_message(message):

    if message.author.bot:
        return

    if message.channel.id == POST_CHANNEL_ID:

        if message.author.bot:
            return

        content = message.content
        attachments = message.attachments

        await message.delete()

        reply_data["reply"] += 1
        save_reply(reply_data)

        reply_number = reply_data["reply"]

        anchor = ""
        match = re.search(r">>\d+", content)

        if match:
            anchor = match.group()

        files = []

        for attachment in attachments:
            file = await attachment.to_file()
            files.append(file)

       embed = discord.Embed(
    title=f"返信 #{reply_number} {anchor}",
    description=content if content else "（画像）",
    color=0x2F3136
)

await message.channel.send(embed=embed, files=files)

    await bot.process_commands(message)


@bot.event
async def on_ready():
    bot.add_view(AnonView())
    print(f"ログイン成功: {bot.user}")


bot.run(TOKEN)
