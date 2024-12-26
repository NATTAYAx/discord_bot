import os
from dotenv import load_dotenv
import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timedelta

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
SERVER_NAME = os.getenv('SERVER_NAME')

intents = discord.Intents.default()
intents.members = True  # Enables the member events, including on_member_join
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

GUILD_ID = int(os.getenv('GUILD_ID')) 
INTRODUCTIONS_CHANNEL_ID = int(os.getenv('INTRODUCTIONS_CHANNEL_ID'))
MESSAGE_ID = int(os.getenv('MESSAGE_ID'))

emojis_roles = {
    'Overwatch2': 'Overwatch2',
    'Valorant': 'Valorant',
    'ApexLegeands': 'ApexLegeands',
    'PUBG': 'PUBG'
}

@bot.command()
async def setup_roles(ctx):
    try:
        message = await ctx.channel.fetch_message(MESSAGE_ID)
        for emoji in emojis_roles.keys():
            await message.add_reaction(emoji)
    except Exception as e:
        await ctx.send(f"Error setting up roles: {e}")
                
@bot.event
async def on_raw_reaction_add(payload):
    if payload.MESSAGE_ID == MESSAGE_ID:
        guild = bot.get_guild(payload.GUILD_ID)
        member = guild.get_member(payload.user_id)
        role_name = emojis_roles.get(payload.emoji.name, payload.emoji.name)
        role = discord.utils.get(guild.roles, name=role_name)
        if role:
            await member.add_roles(role)
            try:
                embed = discord.Embed(
                    color=discord.Color.light_gray(),
                    description=f'✅ คุณได้รับ Role {role.name} บนเซิร์ฟเวอร์ {guild.name} เรียบร้อยแล้ว'
                )
                await member.send(embed=embed)
            except discord.Forbidden:
                print(f"Couldn't send DM to {member.name}")

# add role & remove role
@bot.event
async def on_raw_reaction_remove(payload):
    if payload.MESSAGE_ID == MESSAGE_ID:
        guild = bot.get_guild(payload.GUILD_ID)
        member = guild.get_member(payload.user_id)
        role_name = emojis_roles.get(payload.emoji.name, payload.emoji.name)
        role = discord.utils.get(guild.roles, name=role_name)
        if role:
            await member.remove_roles(role)
            try:
                embed = discord.Embed(
                    color=discord.Color.light_gray(),
                    description=f':no_entry: คุณได้ปลด Role {role.name} บนเซิร์ฟเวอร์ {guild.name} เรียบร้อยแล้ว'
                )
                await member.send(embed=embed)
            except discord.Forbidden:
                print(f"Couldn't send DM to {member.name}")

# On Member Join
@bot.event
async def on_member_join(member):
    try:
        # Send a welcome message in the introductions channel visible only for a short time
        introductions_channel = bot.get_channel(INTRODUCTIONS_CHANNEL_ID)
        if introductions_channel:
            message = await introductions_channel.send(
                f"ยินดีตอนรับเข้าสู่ server, {member.mention}! โปรดพิมพ์ `/ind` เพื่อแนะนำตัวเอง"
            )
            # Delete the message after 10 seconds
            await message.delete(delay=10)
    except Exception as e:
        print(f"Error in on_member_join: {e}")
        
# Slash Command for Introduction
@bot.tree.command(name="ind", description="Introduce yourself")
async def ind(interaction: discord.Interaction):
    if interaction.channel.id != INTRODUCTIONS_CHANNEL_ID:
        await interaction.response.send_message(
            "โปรดใช้คำสั่งนี้ใน Introduction channel", ephemeral=True
        )
        return

    await interaction.response.send_message("บอทได้ทำการส่งข้อความไปยังแชทส่วนตัว", ephemeral=True)

    def check(m):
        return m.author == interaction.user and isinstance(m.channel, discord.DMChannel)

    try:
        # Collect user input via DMs
        await interaction.user.send("ชื่อเล่น ?")
        name_msg = await bot.wait_for('message', check=check, timeout=120)

        await interaction.user.send("เพศ ?")
        gender_msg = await bot.wait_for('message', check=check, timeout=120)

        await interaction.user.send("อื่น ๆ ?")
        other_msg = await bot.wait_for('message', check=check, timeout=120)

        name, gender, other_info = name_msg.content, gender_msg.content, other_msg.content
        utc_time = datetime.utcnow()
        thailand_time = utc_time + timedelta(hours=7)
        formatted_time = thailand_time.strftime('%m/%d/%Y %I:%M %p Thailand Time')

        # Prepare the introduction embed with proper formatting and profile image
        introduction_text = (
            "༶•┈┈⛧┈♛ ♛┈⛧┈┈•༶\n"
            f"**name** : {name}\n"
            f"**gender** : {gender}\n"
            f"**other** : {other_info}\n"
            "༶•┈┈⛧┈♛ ♛┈⛧┈┈•༶"
        )

        embed = discord.Embed(color=discord.Color.dark_gray())
        embed.set_author(name=f"{interaction.user.display_name}", icon_url=interaction.user.avatar.url)
        embed.set_thumbnail(url=interaction.user.avatar.url)  # Set thumbnail to profile image
        embed.add_field(name="Introduction", value=introduction_text, inline=False)
        embed.set_footer(text=f"ID: {interaction.user.id} • {formatted_time}")
        
        # Post introduction card in the introduction channel
        introductions_channel = bot.get_channel(INTRODUCTIONS_CHANNEL_ID)
        if introductions_channel:
            await introductions_channel.send(embed=embed)
        else:
            await interaction.response.send_message(
                "Introduction channel not found. Please contact an admin.", ephemeral=True
            )

    except discord.Forbidden:
        await interaction.response.send_message(
            "I cannot send you DMs. Please enable DMs from server members.", ephemeral=True
        )
    except Exception as e:
        await interaction.user.send(f"An error occurred: {e}")

bot.run(TOKEN)