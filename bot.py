import discord
from discord.ext import commands
import json
import os
import re
from datetime import datetime

TOKEN = os.getenv("TOKEN")

BUTTON_CHANNEL_ID = 1482009837062721596
POST_CHANNEL_ID = 1482009887658606643
LOG_CHANNEL_ID = 1482004336866492629

DATA_FILE = "thread.json"
LINK_FILE = "links.json"

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ---------------- JSON ----------------

def load_json(file, default):
    if os.path.exists(file):
        with open(file) as f:
            return json.load(f)
    return default

def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f)

data = load_json(DATA_FILE, {"count": 0})
links = load_json(LINK_FILE, {})

# ---------------- 時間 ----------------

def now():
    return datetime.now().strftime("%Y/%m/%d %H:%M:%S")

# ---------------- 投票 ----------------

class VoteView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)
        self.up = 0
        self.down = 0
        self.voters = set()

    @discord.ui.button(label="👍 0", style=discord.ButtonStyle.success)
    async def upvote(self, interaction: discord.Interaction, button):

        if interaction.user.id in self.voters:
            await interaction.response.send_message("投票済み", ephemeral=True)
            return

        self.voters.add(interaction.user.id)
        self.up += 1
        button.label = f"👍 {self.up}"

        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="👎 0", style=discord.ButtonStyle.danger)
    async def downvote(self, interaction: discord.Interaction, button):

        if interaction.user.id in self.voters:
            await interaction.response.send_message("投票済み", ephemeral=True)
            return

        self.voters.add(interaction.user.id)
        self.down += 1
        button.label = f"👎 {self.down}"

        await interaction.response.edit_message(view=self)

# ---------------- 引用処理 ----------------

async def build_preview(channel, text):

    anchors = re.findall(r">>(\d+)", text)

    preview = ""

    for a in anchors:

        if a in links:

            link = links[a]

            try:
                msg_id = int(link.split("/")[-1])
                m = await channel.fetch_message(msg_id)

                quoted = "\n".join(m.content.split("\n")[2:])[:120]

                preview += f">>{a}\n{quoted}\n\n"

                text = text.replace(f">>{a}", f"[>>{a}]({link})")

            except:
                pass

    return preview + text

# ---------------- 投稿処理 ----------------

async def post(channel, user, text, image=None):

    data["count"] += 1
    save_json(DATA_FILE, data)

    num = data["count"]

    body = f"{num} 名前：匿名 投稿日：{now()}\n\n{text}"

    if image:

        embed = discord.Embed(description=body)
        embed.set_image(url=image)

        msg = await channel.send(embed=embed, view=VoteView())

    else:

        msg = await channel.send(body, view=VoteView())

    links[str(num)] = msg.jump_url
    save_json(LINK_FILE, links)

    log = bot.get_channel(LOG_CHANNEL_ID)

    if log:
        await log.send(
            f"匿名投稿ログ\n番号:{num}\nユーザー:{user}\n内容:{text}"
        )

# ---------------- 投稿Modal ----------------

class PostModal(discord.ui.Modal, title="匿名投稿"):

    text = discord.ui.TextInput(
        label="投稿内容",
        style=discord.TextStyle.paragraph,
        required=False
    )

    async def on_submit(self, interaction: discord.Interaction):

        channel = bot.get_channel(POST_CHANNEL_ID)

        await post(channel, interaction.user, self.text.value)

        await interaction.response.send_message(
            "投稿しました", ephemeral=True
        )

# ---------------- 投稿ボタン ----------------

class PostView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="匿名投稿",
        style=discord.ButtonStyle.primary,
        custom_id="anon_post_button"
    )
    async def post_button(self, interaction, button):

        await interaction.response.send_modal(PostModal())

# ---------------- setup ----------------

@bot.command()
async def setup(ctx):

    channel = bot.get_channel(BUTTON_CHANNEL_ID)

    async for m in channel.history(limit=20):
        if m.author == bot.user:
            try:
                await m.delete()
            except:
                pass

    await channel.send(
        "匿名掲示板\n下のボタンから投稿できます",
        view=PostView()
    )

# ---------------- 投稿監視 ----------------

@bot.event
async def on_message(message):

    if message.author.bot:
        return

    if message.channel.id == POST_CHANNEL_ID:

        text = await build_preview(message.channel, message.content)

        image = None

        if message.attachments:
            image = message.attachments[0].url

        try:
            await message.delete()
        except:
            pass

        await post(message.channel, message.author, text, image)

    await bot.process_commands(message)

# ---------------- 起動 ----------------

@bot.event
async def on_ready():

    bot.add_view(PostView())

    print("匿名掲示板Bot 起動")

bot.run(TOKEN)
