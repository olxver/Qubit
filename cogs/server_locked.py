import fileinput
import string
import nextcord as discord
import os
import sqlite3 as sql
import datetime
import random
import aiohttp
import io
import aiofiles
import openai
import asyncio
import contextlib


from nextcord.ext import commands
from nextcord.ext.commands import cooldown, BucketType
from nextcord import SlashOption, Interaction
from nextcord.ext import application_checks
from dotenv import load_dotenv

load_dotenv()  # load environment variables from .env file

github_token = os.getenv("GITHUB_API_TOKEN")  
token = os.getenv("BOT_TOKEN")
openai_key = os.getenv("OPENAI_API_KEY")


with sql.connect('data/privateTicketData.db') as db:
    cursor = db.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS ticketData (id TEXT, open INTEGER, date TEXT, user TEXT, cID TEXT)')

class AddUserModal(discord.ui.Modal):
    def __init__(self, channel):
        super().__init__(
            "Add a user to your ticket", 
            timeout=5 * 60,
        )
        self.channel = channel

        self.user = discord.ui.TextInput(
            style=discord.TextInputStyle.short,
            label="User's ID",
            min_length=1,
            max_length=36,
            required=True,
            placeholder="User's ID, must be int, not their name."
        )
        self.add_item(self.user)
        print(self.user.value)
        
    
    async def callback(self, interaction:Interaction):
        user = interaction.guild.get_member(int(self.user.value))
        print(user.name)
        print(user.id)
        overwrite = discord.PermissionOverwrite()
        overwrite.read_messages = True
        await self.channel.set_permissions(user, overwrite=overwrite)
        await interaction.send("Added user to ticket")

class PrivMessageView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)


    @discord.ui.button(
        label="Lock ticket",
        style=discord.ButtonStyle.red, custom_id="deletePriv:red",
        emoji="🔒",
        disabled=False
    )
    async def lock_priv_ticket(self, button:discord.ui.Button, interaction:discord.Interaction):
        with sql.connect('data/privateTicketData.db') as db:
            cur = db.cursor()
            cur.execute("SELECT id FROM ticketData WHERE cID = ?", (interaction.channel.id,))
            ticketID= cur.fetchone()
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            interaction.user: discord.PermissionOverwrite(read_messages=False, send_messages=False)

        }

        for role in interaction.guild.roles:
            if role.permissions.manage_messages:
                overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        await interaction.channel.edit(overwrites=overwrites, topic="Locked ticket 🔒", name=f"locked-{ticketID}-{interaction.user}")
        button = discord.ui.Button(
            label="Delete channel",
            style=discord.ButtonStyle.danger,
            emoji="🗑️"
        )

        async def callback(interaction: discord.Interaction):
            await interaction.send("Deleting ticket...")
            with sql.connect('data/privateTicketData.db') as db:
                cursor = db.cursor()
                cur.execute("SELECT id FROM ticketData WHERE cID = ?", (interaction.channel.id,))
                ticketID = cur.fetchone()[0]
                print(ticketID)
                cursor.execute("UPDATE ticketData SET open = ? WHERE id = ?", (0, ticketID))

                db.commit()
            await asyncio.sleep(2)
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
        with sql.connect('data/privateTicketData.db') as db:
            cursor = db.cursor()
            cursor.execute("SELECT id FROM ticketData WHERE cID = ?", (interaction.channel.id,))
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
        with sql.connect('data/privateTicketData.db') as db:
            cur = db.cursor()
            cur.execute("SELECT id FROM ticketData WHERE cID = ?", (interaction.channel.id,))
            ticketID= cur.fetchone()

        # Get current date and time
        now = datetime.datetime.now()

        # Format the filename

        print(ticketID[0])
        print("h", ticketID[0])

        filename = f"{now.strftime('%Y-%m-%d')}-{ticketID[0]}-log.txt"


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



        # create a file object from the file name

        async with aiofiles.open(filename, 'rb') as f:
            file_bytes = await f.read()
            file_object = discord.File(io.BytesIO(file_bytes), filename=filename)
        # send the file object in a list
        await interaction.send(files=[file_object])

        # remove the file
        await asyncio.sleep(5) # wait for a few seconds to ensure file is closed
        os.remove(filename)
    @discord.ui.button(
        label="Add user",
        style=discord.ButtonStyle.green, custom_id="add:green",
        emoji="🧑",
        disabled=False
    )
    async def add_user(self, button:discord.ui.Button, interaction:discord.Interaction):  
        await interaction.response.send_modal(AddUserModal(interaction.channel))
    

# create ticket button 
class PrivTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Create Ticket",
        style=discord.ButtonStyle.green, custom_id="create_ticket_priv:green",
        emoji="🎫"
    )
    async def create_ticket(self, button: discord.ui.Button, interaction: discord.Interaction):
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True)

        }
        # Define the function to generate random ticket IDs
        def generate_ticket_id():
            # Generate a random string of length 4 consisting of uppercase letters and digits
            return ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))


        with sql.connect('data/privateTicketData.db') as db:

            cursor = db.cursor()
            
            while True:
                ticketID = generate_ticket_id()
                print(ticketID)
                cursor.execute("SELECT * FROM ticketData WHERE id = ?", (ticketID,)) # check if id exists

                if not cursor.fetchone():

                    break


        for role in interaction.guild.roles:
            if role.permissions.manage_messages:
                overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
        

        channel = await interaction.guild.create_text_channel(name=f"ID-{ticketID}--{interaction.user}", overwrites=overwrites, topic=f"Ticket for {interaction.user.mention}")
        with sql.connect('data/privateTicketData.db') as db:
            cursor = db.cursor()
            cursor.execute("INSERT INTO ticketData (id, open, date, user, cID) VALUES (?,?,?,?,?)", (ticketID,1,datetime.datetime.now(),interaction.user.id,channel.id,))
            db.commit()


        # Send a response message to the user
        await interaction.response.send_message(f"Creating your ticket... {channel.mention}", ephemeral=True)
        embed = discord.Embed(
            title=f"Welcome, {interaction.user}",
            description=f"Your Ticket ID: `{ticketID}`\nThe staff team of `{interaction.guild.name}` are working hard to respond to your ticket. While you're waiting, please provide a reason to why you have opened this ticket.",
            color=discord.Colour.random()
        )
        embed.set_footer(text="developed by olxver#9999")
        embed.set_image(url="https://media.tenor.com/uUNv_-QQhTIAAAAd/mrbean-bean.gif")
        message = await channel.send(embed=embed, view=PrivMessageView())

class VerifyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Verify yourself",
        style=discord.ButtonStyle.blurple, custom_id="verify_persistent:blurple",
        emoji="✅"
    )
    async def verify_member(self, button: discord.ui.Button, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        await interaction.send("Thanks! You should be verified now. If you're not, DM <@1059124562027094126>", ephemeral=True)
        await asyncio.sleep(1)
        try:
            await interaction.user.add_roles(interaction.guild.get_role(1097160033164337242), reason="Automated verification")
        except Exception as e:
            await interaction.send(f"An error occured while trying to verify you, please DM <@1059124562027094126> with this log:\n{e}", ephemeral=True)
            return


class ServerLocked(commands.Cog):
    # these are only available in Qubit's own server
    def __init__(self, bot):
        self.bot = bot

    @discord.slash_command(name="staff", description="Staff commands", guild_ids=[1096803115002515506], force_global=False)
    @application_checks.has_guild_permissions(manage_messages=True)
    async def staff(self, interaction: Interaction):
        pass # staff parent command



    @staff.subcommand(description="Purges a certain amount of messages from a channel.")
    @application_checks.has_guild_permissions(manage_messages=True)
    async def purge(self, interaction: Interaction, amount: int):
        await interaction.channel.purge(limit=amount)
        await interaction.send(f"Successfully purged {amount} messages from {interaction.channel.mention}!", delete_after=5)
    
    @staff.subcommand(description="WEBHOOK COMMAND")
    @application_checks.has_guild_permissions(manage_guild=True)
    async def webhook(self, interaction: Interaction, message):
        url = "https://discord.com/api/webhooks/1097167482982244512/sF1JYy0nNXX1euwu_RIc38JjcMZmGLcWMUlbgMkvCA9bsVvP3MuaezMeBM_D_2Hsgdnv"
        await interaction.response.defer(ephemeral=True)

        async def send_to_webhook(url, content):
            # Create a new HTTP session and use it to create webhook object
            async with aiohttp.ClientSession() as session:
                webhook = discord.Webhook.from_url(url, session=session)
                await webhook.send(content)


        await send_to_webhook(url=url, content=message)
        await interaction.send("Sent message to webhook!", ephemeral=True)
        
    @staff.subcommand(description="setup verify command|only on qubits server")
    @application_checks.has_guild_permissions(manage_guild=True)
    async def setup_verify_guild(self, interaction:Interaction, channel: discord.TextChannel):
        await interaction.response.defer(ephemeral=True)
        v = discord.Embed(
            title="Welcome! 😁",
            description="__Make sure to read the rules before verifying yourself__\nTo verify, **please press the big blue button below**\nThis is to avoid spam and bots.",
            color=discord.Color.green()
        )
        v.set_footer(text="developed by olxver#9999")
        v.set_thumbnail(url="https://media.tenor.com/cthCPXwiJV4AAAAC/bongo-cat-button.gif")
        await channel.send(embed=v, view=VerifyView())
        await interaction.send("Successfully setup verification", ephemeral=True)
    
    
    @staff.subcommand(description="Parent command for tickets")
    @commands.has_guild_permissions(manage_messages=True)
    @commands.cooldown(1, 10, BucketType.guild)
    async def tickets(self, interaction:Interaction):
        pass

    @tickets.subcommand(description="Create a message in which a user can create a ticket, with buttons|only on qubits server")
    @commands.has_guild_permissions(manage_messages=True)
    @commands.cooldown(1, 10, BucketType.guild)
    async def create_parent(self, interaction:Interaction, 
                    name:str=SlashOption(description="The label for the button?", required=True),
                    desc:str=SlashOption(description="The description for the embed. (we recommend to set guidelines for a ticket)", required=True),
                    channel:discord.TextChannel=SlashOption(description="The channel to send the message into. (dont type anything to choose current channel)", required=False)
                ):

        
        if not channel:
            channel = interaction.channel

        embed = discord.Embed(
            title="Create a ticket",
            description=desc,
            color=discord.Colour.random()
        )
        view = PrivTicketView()
        view.children[0].label = name

        await channel.send(embed=embed, view=view)
        await interaction.send("Successfully created a ticket system!", ephemeral=True) 

    @tickets.subcommand(description="Grab a ticket's information from a ticket ID|only on qubits server")
    @commands.has_guild_permissions(manage_messages=True)
    @commands.cooldown(1, 10, BucketType.user)
    async def info(self, interaction:Interaction, ticket_id=SlashOption(description="The ID of the ticket", required=True)):
        with sql.connect('data/privateTicketData.db') as db:
            cursor = db.cursor()
            cursor.execute("SELECT * FROM ticketData WHERE id=?", (ticket_id,))
            data = cursor.fetchone()
            if not data:
                await interaction.response.send_message("No ticket found with that ID (maybe you forgot to add the capital letters?)", ephemeral=True)
            else:
                id, open, date, user, cID = data
                open_status = "Open" if open else "Closed"
                embed = discord.Embed(
                    title="Ticket #"+str(id),
                    color=discord.Colour.random()
                )
                embed.add_field(name="Status", value=f"`{open_status}`")
                embed.add_field(name="Date created", value=f"`{date}`")
                embed.add_field(name="User", value=f"<@{user}>")
                embed.add_field(name="Channel ID", value=f"{cID} / `{cID}`")
                await interaction.send(embed=embed, ephemeral=True)






    # gpt-3

    @discord.slash_command(description="Generate a GPT-3 response | only on qubits server ", guild_ids=[1096803115002515506])
    @commands.cooldown(1, 10, BucketType.user)
    async def gpt(self, interaction:Interaction, text=SlashOption(description="Proompt? max 100 tokens or around 75 words", required=True), system_message=SlashOption(description="System message? (this is the message that will make GPT-3.5 change it's behaivour to)", required=False)):
        if len(text) > 75:
            await interaction.response.send_message("Please keep the prompt under 75 words", ephemeral=True)
        openai.api_key = openai_key
        chat_log = []
        
        chat_log.append({"role": "system", "content": "You are a large language model designed for Discord. Follow the user's prompt and try to be as human-like as possible."})
        
        chat_log.append({"role": "user", "content": text})
        await interaction.response.defer(ephemeral=True)

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=chat_log
        )
        assistant_response = response['choices'][0]['message']['content']
        await interaction.send(assistant_response.strip('\n').strip(), ephemeral=True)
        chat_log.append({"role": "assistant", "content": assistant_response.strip("\n").strip()})



        

def setup(bot):
    bot.add_cog(ServerLocked(bot))
    print("Server locked cog loaded")