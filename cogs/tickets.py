import fileinput
import nextcord as discord
import os
import sqlite3 as sql
import datetime
import random
import aiohttp
import io
import aiofiles
import asyncio
import contextlib

from nextcord.ext import commands
from nextcord.ext.commands import cooldown, BucketType
from nextcord import SlashOption, Interaction
from nextcord.ext import application_checks



class MessageView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)


    @discord.ui.button(
        label="Lock ticket",
        style=discord.ButtonStyle.red, custom_id="delete:red",
        emoji="🔒",
        disabled=False
    )
    async def del_ticket(self, button:discord.ui.Button, interaction:discord.Interaction):
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            interaction.user: discord.PermissionOverwrite(read_messages=False, send_messages=False)

        }

        for role in interaction.guild.roles:
            if role.permissions.manage_messages:
                overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        await interaction.channel.edit(overwrites=overwrites, topic="Locked ticket 🔒", name=f"locked-ticket-{interaction.user}")
        button = discord.ui.Button(
            label="Delete channel",
            style=discord.ButtonStyle.danger,
            emoji="🗑️"
        )

        async def callback(interaction: discord.Interaction):
            await interaction.send("Deleting ticket...")
            await asyncio.sleep(0.5)
            await interaction.channel.delete()

        button.callback = callback

        await asyncio.sleep(1)
        embed = discord.Embed(
            title="Ticket successfully locked 🔒",
            description="To delete, please press `Delete button` below 😁",
            color=discord.Colour.random()
            )
        view = discord.ui.View()
        view.add_item(button)
        await interaction.send(embed=embed, view=view)
        with sql.connect('data/publicTicketData.db') as db:
            cursor = db.cursor()
            cursor.execute("SELECT ticket_id FROM data WHERE server_id = ?", (interaction.guild.id,))
            tID = cursor.fetchone()
            try:
                message = await interaction.channel.fetch_message(int(tID[0]))
            except Exception as e:
                await interaction.send(f"There was an error handling your request.\n{e}\n**This issue is known, please don't report it!**")
            await message.delete()

    @discord.ui.button(
        label="Save message log",
        style=discord.ButtonStyle.blurple, custom_id="save:blurple",
        emoji="📄",
        disabled=False
    )
    async def sav_transcript(self, button:discord.ui.Button, interaction:discord.Interaction):       

        # Get current date and time
        now = datetime.datetime.now()

        # Format the filename

        filename = f"{now.strftime('%Y-%m-%d')}-{interaction.guild}-ticket-logs.txt"


    # write messages and authors to the file
        await interaction.response.defer()        
        await interaction.send("Creating log...")
        
        with open(filename, 'w', encoding='utf-8') as file:
            file.write(f"TICKET LOG\n{filename}\n;LOG START;\n")
            async for message in interaction.channel.history(limit=None, oldest_first=True):
                if message.author.id == 1096576282394890431: # check if the message sent is from the bot, if it is, continue
                    continue
                else:
                    file.write(f'{message.author.name}: {message.content}\n')
            print("wrote file")

            await asyncio.sleep(2)


        # create a file object from the file name

        async with aiofiles.open(filename, 'rb') as f:
            file_bytes = await f.read()
            file_object = discord.File(io.BytesIO(file_bytes), filename=filename)
        # send the file object in a list
        await interaction.send(files=[file_object])

        # remove the file
        await asyncio.sleep(5) # wait for a few seconds to ensure file is closed
        os.remove(filename)





class TicketView(discord.ui.View):
    def __init__(self, tag):
        super().__init__(timeout=None)
        self.tag = tag

    @discord.ui.button(
        label="Create Ticket",
        style=discord.ButtonStyle.green, custom_id="persistent_view:green",
        emoji="🎫"
    )
    async def create_ticket(self, button: discord.ui.Button, interaction: discord.Interaction):
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True)

        }
        with sql.connect('data/publicTicketData.db') as db:
            cursor = db.cursor()
            cursor.execute("SELECT tag FROM data WHERE server_id=?", (interaction.guild.id,))

            self.tag = cursor.fetchone()

        for role in interaction.guild.roles:
            if role.permissions.manage_messages:
                overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)


        channel = await interaction.guild.create_text_channel(name=f"{self.tag}-ticket-{interaction.user}", overwrites=overwrites, topic=f"Ticket for {interaction.user.mention}")

        # Send a response message to the user
        await interaction.response.send_message(f"Creating your ticket... {channel.mention}", ephemeral=True)
        embed = discord.Embed(
            title=f"Welcome, {interaction.user}",
            description=f"The staff team of `{interaction.guild.name}` are working hard to respond to your ticket. While you're waiting, please provide a reason to why you have opened this ticket.",
            color=discord.Colour.random()
        )
        embed.set_footer(text="developed by olxver#9999")
        embed.set_image(url="https://media.tenor.com/uUNv_-QQhTIAAAAd/mrbean-bean.gif")
        message = await channel.send(embed=embed, view=MessageView())
        with sql.connect('data/publicTicketData.db') as db:
            cursor = db.cursor()
            cursor.execute("INSERT INTO data (ticket_id, server_id) VALUES (?, ?)", (message.id, interaction.guild.id))
            db.commit()

        

class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @discord.slash_command(force_global=True)
    @commands.has_guild_permissions(manage_messages=True)
    @commands.cooldown(1, 10, BucketType.guild)
    async def tickets(self, interaction:Interaction):
        """parent command"""
        pass

    @tickets.subcommand(description="Create a message in which a user can create a ticket")
    @commands.has_guild_permissions(manage_messages=True)
    @commands.cooldown(1, 120, BucketType.guild)
    async def create(self, interaction:Interaction, 
                    name:str=SlashOption(description="The label for the button?", required=True),
                    tag=SlashOption(description="The tag to show on the created channels. (e.g tag-ticket-user0000)", required=True),
                    desc:str=SlashOption(description="The description for the embed. (we recommend to set guidelines for a ticket)", required=True),
                    channel:discord.TextChannel=SlashOption(description="The channel to send the message into. (dont type anything to choose current channel)", required=False),
                ):
        if not channel:
            channel = interaction.channel
        
        embed = discord.Embed(
            title="Create a ticket",
            description=desc,
            color=discord.Colour.random()
        )
        view = TicketView(tag=tag)
        with sql.connect('data/publicTicketData.db') as db:
            cursor = db.cursor()
            cursor.execute("INSERT INTO data (tag, server_id) VALUES (?,?) ", (tag, interaction.guild.id))
            db.commit()
        view.children[0].label = name

        await channel.send(embed=embed, view=view)
        await interaction.send("Successfully created a ticket system!", ephemeral=True) 





def setup(bot):
    bot.add_cog(Tickets(bot))
    print("Tickets cog loaded")
