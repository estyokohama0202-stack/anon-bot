import discord
from discord.ext import commands
import time
import json
import os

TOKEN = os.getenv("TOKEN")

BUTTON_CHANNEL_ID = 1482009837062721596
POST_CHANNEL_ID = 1482009887658606643
LOG_CHANNEL_ID = 1482004336866492629

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

cooldowns = {}
COOLDOWN_TIME = 30

DATA_FILE = "anon_data.json"


def load_count():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            data = json.load(f)
            return data.get("count", 0)
    return 0


def save_count(count):
    with open(DATA_FILE, "w") as f:
        json.dump({"count": count}, f)


anon_count = load_count()


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
                    f"⏳ あと {int(remaining)} 秒待ってください。",
                    ephemeral=True
                )
                return

        cooldowns[user_id] = now

        anon_count += 1
        save_count(anon_count)

        channel = bot.get_channel(POST_CHANNEL_ID)

        embed = discord.Embed(
            title=f"匿名 #{anon_count}",
            description=self.message.value if self.message.value else "（画像のみ投稿）",
            color=0x2F3136
        )

        embed.set_footer(text="この投稿のスレッドで返信できます")

        msg = await channel.send(embed=embed)

        await msg.create_thread(
            name=f"匿名 #{anon_count} のスレッド",
            auto_archive_duration=1440
        )

        log = bot.get_channel(LOG_CHANNEL_ID)
        await log.send(
            f"匿名 #{anon_count}\n投稿者: {interaction.user}\n内容: {self.message.value}"
        )

        await interaction.response.send_message(
            "投稿しました！スレッドで返信できます。",
            ephemeral=True
        )


class AnonView(discord.ui.View):

    @discord.ui.button(label="匿名投稿する", style=discord.ButtonStyle.primary)
    async def anon_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(AnonModal())


@bot.command()
async def setup(ctx):

    channel = bot.get_channel(BUTTON_CHANNEL_ID)

    view = AnonView()

    await channel.send(
        "匿名投稿\n下のボタンから投稿できます",
        view=view
    )


@bot.event
async def on_message(message):

    if message.author.bot:
        return

    if isinstance(message.channel, discord.Thread):

        if "匿名 #" in message.channel.name:

            content = message.content
            attachments = message.attachments

            await message.delete()

            files = []

            for attachment in attachments:
                file = await attachment.to_file()
                files.append(file)

            text = f"""匿名返信
----------------
{content if content else ""}"""

            await message.channel.send(text, files=files)

    await bot.process_commands(message)


@bot.event
async def on_ready():
    print(f"ログイン成功: {bot.user}")


bot.run(TOKEN)
