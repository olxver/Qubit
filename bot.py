
import fnmatch
import sys
import nextcord as discord
import os
import sqlite3 as sql
import random
import gitignore_parser
import asyncio
from cogs.tickets import TicketView
from cogs.server_locked import VerifyView, PrivTicketView, PrivMessageView
from nextcord.ext import commands
from nextcord import SlashOption, Interaction
from nextcord.ext import application_checks
from github import Github, InputGitTreeElement
from dotenv import load_dotenv

load_dotenv()  # load environment variables from .env file

github_token = os.getenv("GITHUB_API_TOKEN")  
token = os.getenv("BOT_TOKEN")
ID = os.getenv("ID")

intents = discord.Intents.default()
intents.message_content = True

class Bot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.persistent_views_added = False

    async def on_ready(self):
        if not self.persistent_views_added:
            self.add_view(TicketView(tag=None))
            self.add_view(VerifyView())
            self.add_view(PrivTicketView())
            self.add_view(PrivMessageView())


            self.persistent_views_added = True

        print(f"Logged in as {self.user} (ID: {self.user.id})")


bot = Bot(command_prefix="q>", intents=intents)
code = ""
# load databases

with sql.connect('data/server_entries.db') as db: 
    db.execute('''CREATE TABLE IF NOT EXISTS help_entries
                (server_id TEXT, help_name TEXT, tag TEXT, answer TEXT, image TEXT)''')

with sql.connect('data/publicTicketData.db') as db:
    db.execute('CREATE TABLE IF NOT EXISTS data (tag TEXT, server_id TEXT, ticket_id TEXT)')

# load cogs
try:
    for file in os.listdir('./cogs'):
        if file.endswith('.py'):
            bot.load_extension(f'cogs.{file[:-3]}')
except FileNotFoundError:
    print("The system cannot find the cogs folder. You most likely haven't created it, or the program does not have the permissions to access it.")




# owner commands:
@bot.slash_command(description="Reloads a cog.", force_global=False, guild_ids=[ID])
@application_checks.is_owner()
async def reload(interaction:Interaction, cog:str=SlashOption(required=True)):
    cog = cog.lower()
    try:
        bot.reload_extension(f"cogs.{cog}")
        await interaction.send(f"{cog} has been reloaded.", ephemeral=True)
    except commands.ExtensionNotLoaded:
        await interaction.send(f"{cog} is not currently loaded/does not exist", ephemeral=True)
    except Exception as error:
        await interaction.send(f"a fatal error occurred that was not handled correctly. log:\n{error}", ephemeral=True)
    

@bot.slash_command(description="Reload all cogs", force_global=False, guild_ids=[ID])
@application_checks.is_owner()
async def sync(interaction:Interaction):
    try:
        cogs = []
        for file in os.listdir('./cogs'):
            if file.endswith('.py'):
                bot.load_extension(f'cogs.{file[:-3]}')
                cogs.append(file)
        await interaction.send(f"Reloaded cogs\n{cogs}",ephemeral=True)
    except Exception as e:
        await interaction.send(f"There was an error trying to reload the cog `{file}`\nLog:\n{e}", ephemeral=True)

@bot.slash_command(description="Unloads a cog.", force_global=False, guild_ids=[ID])
@application_checks.is_owner()
async def unload(interaction:Interaction, cog:str=SlashOption(required=True)):
    cog = cog.lower()
    try:
        bot.reload_extension(f"cogs.{cog}")
        await interaction.send(f"{cog} has been unloaded.", ephemeral=True)
    except commands.ExtensionNotFound:
        await interaction.send(f"{cog} does not exist.", ephemeral=True)
    except Exception as error:
        await interaction.send(f"a fatal error occurred that was not handled correctly. log:\n{error}", ephemeral=True)
    
@bot.slash_command(description="Shuts down the bot.", force_global=False, guild_ids=[ID])
@application_checks.is_owner()
async def shutdown(interaction:Interaction):
    global confirmation_code
    
    letters_numbers = "abcdefghijklmnopqrstuvwxyz0123456789"
    confirmation_code = "".join(random.choices(letters_numbers, k=4))
    
    await interaction.send(f"Are you sure you want to shut down the bot? Type `{confirmation_code}` to confirm.")
    
    # define a function to check if the user's message matches the confirmation code
    def check_message(message: discord.Message):
        if message.content == confirmation_code and message.author == interaction.user:
            return True
        else:
            pass
    try:
        # wait for the user to confirm with the code
        message = await bot.wait_for('message', check=check_message, timeout=8)
    except TimeoutError:
        # if the user doesn't confirm within 8 seconds, cancel the shutdown
        await interaction.send("Shutdown canceled. You took too long to confirm.")
    else:
        # if the confirmation code matches, shut down the bot
        await interaction.send("Shutting down...")
        await bot.close()

@bot.slash_command(description="Wipes all data in the entries database.", force_global=False, guild_ids=[ID])
@application_checks.is_owner()
async def wipe_data(interaction:Interaction):
    global confirmation_code
    
    letters_numbers = "abcdefghijklmnopqrstuvwxyz0123456789"
    confirmation_code = "".join(random.choices(letters_numbers, k=4))
    
    await interaction.send(f"Are you sure you want to wipe all data? Type `{confirmation_code}` to confirm.")
    
    # define a function to check if the user's message matches the confirmation code
    def check_message(message: discord.Message):
        if message.content == confirmation_code and message.author == interaction.user:
            return True
        else:
            pass
    try:
        # wait for the user to confirm with the code
        message = await bot.wait_for('message', check=check_message, timeout=8)
    except TimeoutError:
        # if the user doesn't confirm within 8 seconds, cancel the shutdown
        await interaction.send("Canceled. You took too long to confirm.")
    else:
        # if the confirmation code matches, shut down the bot
        await interaction.send("Wiping... (requires restart)")
        print("wiping data...")
        with open("data/server_entries.db", "w") as f:
            f.truncate(0)
        await asyncio.sleep(3)
        await interaction.send("All data wiped. Restarting...")
        def restart_program():
            python = sys.executable
            os.execl(python, python, *sys.argv)

        # call the restart function
        restart_program()



bot.run(token)