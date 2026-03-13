import discord
from discord.ext import commands
import json
import os
import re
from datetime import datetime, timezone, timedelta

TOKEN = os.getenv("TOKEN")

BUTTON_CHANNEL_ID = 1482009837062721596
POST_CHANNEL_ID = 1482009887658606643
LOG_CHANNEL_ID = 1482004336866492629

DATA_FILE = "thread.json"
LINK_FILE = "links.json"

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ---------- 日本時間 ----------

JST = timezone(timedelta(hours=9))
week = ["月","火","水","木","金","土","日"]

def now():
    t = datetime.now(JST)
    w = week[t.weekday()]
    return t.strftime(f"%Y/%m/%d({w}) %H:%M:%S")

# ---------- JSON ----------

def load_json(file, default):
    if os.path.exists(file):
        with open(file) as f:
            return json.load(f)
    return default

def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f)

data = load_json(DATA_FILE, {"count":0})
links = load_json(LINK_FILE, {})

# ---------- 投票 ----------

class VoteView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)
        self.up=0
        self.down=0
        self.voters=set()

    @discord.ui.button(label="👍 0", style=discord.ButtonStyle.success)
    async def up(self, interaction:discord.Interaction, button):

        if interaction.user.id in self.voters:
            await interaction.response.send_message("投票済み",ephemeral=True)
            return

        self.voters.add(interaction.user.id)
        self.up+=1
        button.label=f"👍 {self.up}"

        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="👎 0", style=discord.ButtonStyle.danger)
    async def down(self, interaction:discord.Interaction, button):

        if interaction.user.id in self.voters:
            await interaction.response.send_message("投票済み",ephemeral=True)
            return

        self.voters.add(interaction.user.id)
        self.down+=1
        button.label=f"👎 {self.down}"

        await interaction.response.edit_message(view=self)

# ---------- 引用 ----------

async def build_quote(channel,text):

    anchors=re.findall(r">>(\d+)",text)

    quote_embed=None

    for a in anchors:

        if a in links:

            try:

                link=links[a]
                msg_id=int(link.split("/")[-1])

                m=await channel.fetch_message(msg_id)

                quoted=m.embeds[0].description if m.embeds else m.content

                quote_embed=discord.Embed(
                    description=f">>{a}\n{quoted}",
                    color=0xf1c40f
                )

                text=text.replace(f">>{a}",f"[>>{a}]({link})")

            except:
                pass

    return text,quote_embed

# ---------- 投稿 ----------

async def post(channel,user,text,files=None,is_reply=False,quote_embed=None):

    data["count"]+=1
    save_json(DATA_FILE,data)

    num=data["count"]

    title="返信" if is_reply else "匿名"
    color=0x2ecc71 if is_reply else 0x5865F2

    embed=discord.Embed(
        title=f"{title} #{num}",
        description=text,
        color=color
    )

    embed.set_footer(text=now())

    msg=await channel.send(
        embed=embed,
        view=VoteView(),
        files=files
    )

    if quote_embed:
        await channel.send(embed=quote_embed)

    links[str(num)]=msg.jump_url
    save_json(LINK_FILE,links)

    log=bot.get_channel(LOG_CHANNEL_ID)

    if log:
        await log.send(
            f"匿名投稿ログ\n番号:{num}\nユーザー:{user}\n内容:{text}"
        )

# ---------- Modal ----------

class PostModal(discord.ui.Modal,title="匿名投稿"):

    text=discord.ui.TextInput(
        label="投稿内容",
        style=discord.TextStyle.paragraph,
        required=False
    )

    async def on_submit(self,interaction:discord.Interaction):

        channel=bot.get_channel(POST_CHANNEL_ID)

        await post(channel,interaction.user,self.text.value)

        await interaction.response.send_message("投稿しました",ephemeral=True)

# ---------- ボタン ----------

class PostView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="匿名投稿",
        style=discord.ButtonStyle.primary,
        custom_id="anon_post_button"
    )
    async def post_button(self,interaction,button):

        await interaction.response.send_modal(PostModal())

# ---------- setup ----------

@bot.command()
async def setup(ctx):

    channel=bot.get_channel(BUTTON_CHANNEL_ID)

    async for m in channel.history(limit=20):
        if m.author==bot.user:
            try:
                await m.delete()
            except:
                pass

    await channel.send(
        "下記の匿名投稿から投稿できます。\nこちらのチャンネルに画像やGIF動画も送ると匿名投稿出来ます。\n返信は>>で出来ます。",
        view=PostView()
    )

# ---------- メッセージ ----------

@bot.event
async def on_message(message):

    if message.author.bot:
        return

    # 画像匿名投稿
    if message.channel.id==BUTTON_CHANNEL_ID:

        if message.attachments:

            files=[]

            for a in message.attachments:
                file=await a.to_file()
                files.append(file)

            try:
                await message.delete()
            except:
                pass

            await post(
                bot.get_channel(POST_CHANNEL_ID),
                message.author,
                "（画像投稿）",
                files
            )

            return

    # 返信
    if message.channel.id==POST_CHANNEL_ID:

        text,quote_embed=await build_quote(
            message.channel,
            message.content
        )

        files=None

        if message.attachments:

            files=[]

            for a in message.attachments:
                file=await a.to_file()
                files.append(file)

        try:
            await message.delete()
        except:
            pass

        await post(
            message.channel,
            message.author,
            text,
            files,
            True,
            quote_embed
        )

    await bot.process_commands(message)

# ---------- 起動 ----------

@bot.event
async def on_ready():

    bot.add_view(PostView())

    print("匿名掲示板Bot 起動")

bot.run(TOKEN)
