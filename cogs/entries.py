
import nextcord as discord
import os
import sqlite3 as sql
import random
import aiohttp
import io
import asyncio
from nextcord.ext import commands
from nextcord.ext.commands import cooldown, BucketType
from nextcord import SlashOption, Interaction
from nextcord.ext import application_checks

class Entries(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @discord.slash_command(description="Parent command for entries")
    async def entries(self, interaction: Interaction):
        """
        This is the main slash command that will be the prefix of all commands below.
        This will never get called since it has subcommands.
        """
        pass


    @entries.subcommand(name="create", description="Creates a help entry.")
    @commands.has_guild_permissions(manage_messages=True)
    @commands.cooldown(1, 10, BucketType.guild)
    async def create_entry(self, interaction:Interaction, name: str = SlashOption(description="The name of the entry?", required=True), tag: str = SlashOption(description="The tag for the entry? (e.g Python support or LSPDFR support.)", required=True), answer: str = SlashOption(description="The answer for the entry?", required=True), image_check: bool = SlashOption(description="Would you like an image for the answer to the entry?", required=True)):
        name, tag = name.lower(), tag.lower()
        with sql.connect('data/server_entries.db') as db:
            entry = db.execute("SELECT * FROM help_entries WHERE server_id=? AND help_name=? AND tag=?", (interaction.guild.id, name, tag)).fetchone()
            if entry:
                await interaction.send("This entry already exists, please try a different name or tag.", ephemeral=True)
            else:
                if image_check:
                    await interaction.response.defer()
                    await interaction.send("Please provide the Imgur link for the image.\nExample: `https://i.imgur.com/1N6mAei.png`\n(Note that MP4 or other video types do not work at this time. Please use GIFs instead while we work on this!)")
                    try:
                        response = await self.bot.wait_for("message", check=lambda message: message.author == interaction.user and message.channel == interaction.channel, timeout=60.0)
                        image_url = response.content
                    except asyncio.TimeoutError:
                        await interaction.send("You took too long to provide the Imgur link. Please try again.")
                        return
                else:
                    image_url = None
                db.execute("INSERT INTO help_entries (server_id, help_name, tag, answer, image) VALUES (?,?,?,?,?)", (interaction.guild.id, name, tag, answer, image_url))
                db.commit()
                await interaction.send(f"Entry successfully made, with name `{name}` and tag `{tag}`", ephemeral=True)

    @entries.subcommand(name="h", description="Grab a help entry and display it.")
    @commands.has_guild_permissions(manage_messages=True)
    @commands.cooldown(1, 5, BucketType.guild)
    async def grab_entry(self, interaction:Interaction, name: str = SlashOption(description="The name of the entry?", required=True), tag: str = SlashOption(description="The tag for the entry?", required=True)):
        name, tag = name.lower(), tag.lower()
        with sql.connect('data/server_entries.db') as db:
            entry = db.execute("SELECT * FROM help_entries WHERE server_id=? AND help_name=? AND tag=?", (interaction.guild.id, name, tag)).fetchone()
            if entry:
                answer = entry[3]
                image_url = entry[4]
                embed = discord.Embed(
                    title=f"{tag}, {name}",
                    description=answer
                )
                if image_url:
                    embed.set_image(url=image_url)
                    await interaction.send(embed=embed)
                else:
                    await interaction.send(embed=embed)
            else:
                await interaction.send("Sorry, could not find an entry with the specified name and tag.", ephemeral=True)

    @entries.subcommand(name='list', description="Lists all entries, not limited by tag.")
    async def list_help_entries(self, interaction:Interaction):
        await interaction.response.defer() # Defer the response first
        entries = self.get_entries(interaction.guild.id)
        if not entries:
            await interaction.followup.send('No help entries found.')
            return

        pages = self.paginate_entries(entries)
        current_page = 0
        embed = self.get_embed1(pages[current_page], current_page, len(pages))
        message = await interaction.followup.send(embed=embed) # Use followup to send message response

        await asyncio.sleep(1)

        if len(pages) > 1:
            # Add reactions for page navigation
            reactions = ["◀️", "▶️", "❌"]
            for reaction in reactions:
                await message.add_reaction(reaction)

            # Define the check function for reaction events
            def reaction_check(reaction, user):
                return user == interaction.user and reaction.message.id == message.id and reaction.emoji in reactions

            # Listen for reactions and update the embed
            while True:
                try:
                    reaction, user = await self.bot.wait_for("reaction_add", timeout=60.0, check=reaction_check)
                    if reaction.emoji == "▶️":
                        if current_page < len(pages) - 1:
                            current_page += 1
                            embed = self.get_embed1(pages[current_page], current_page, len(pages))
                            await message.edit(embed=embed)
                    elif reaction.emoji == "◀️":
                        if current_page > 0:
                            current_page -= 1
                            embed = self.get_embed1(pages[current_page], current_page, len(pages))
                            await message.edit(embed=embed)
                    elif str(reaction.emoji) == '❌':
                        await message.clear_reactions()
                        break

                    await message.remove_reaction(reaction, user)
                except asyncio.TimeoutError:
                    break

    def get_entries(self, server_id):
        entries = []
        with sql.connect('data/server_entries.db') as db:
            cursor = db.cursor()
            cursor.execute("SELECT * FROM help_entries WHERE server_id=?", (server_id,))
            rows = cursor.fetchall()
            for row in rows:
                entries.append(f'**Tag** `{row[2]}`: **Name** `{row[1]}`')
        return entries

    def paginate_entries(self, entries, page_size=5):
        return [entries[i:i+page_size] for i in range(0, len(entries), page_size)]

    def get_embed1(self, entries, current_page, total_pages):
        entries_text = "\n".join(entries)
        embed = discord.Embed(title="Help entries", description=entries_text)
        embed.set_footer(text=f"Page {current_page+1}/{total_pages}")
        return embed

            
    @entries.subcommand(name="search", description="Search for help entries by a tag.")
    @commands.has_guild_permissions(manage_messages=True)
    @commands.cooldown(1, 5, BucketType.guild)
    async def search_entries(self, interaction: Interaction, tag: str = SlashOption(description="The tag for the entry?", required=True)):
        tag = tag.lower()
        with sql.connect('data/server_entries.db') as db:
            entries = db.execute("SELECT help_name, tag, answer, image FROM help_entries WHERE server_id=? AND tag=?", (interaction.guild.id, tag)).fetchall()
            if not entries:
                await interaction.send(f"Sorry, could not find any entries with the specified tag: `{tag}`", ephemeral=True)
                return

            page_size = 5  # Number of entries to show per page
            pages = [entries[i:i+page_size] for i in range(0, len(entries), page_size)]  # Split entries into pages

            current_page = 0
            embed = self.get_embed(entries, current_page, page_size)
            message = await interaction.send(embed=embed)

            if len(pages) > 1:
                # Add reactions for page navigation
                reactions = ["◀️", "▶️"]
                for reaction in reactions:
                    await message.add_reaction(reaction)

                # Define the check function for reaction events
                def reaction_check(reaction, user):
                    return user == interaction.user and reaction.message.id == message.id and reaction.emoji in reactions

                # Listen for reactions and update the embed
                while True:
                    try:
                        reaction, user = await self.bot.wait_for("reaction_add", timeout=60.0, check=reaction_check)
                        if reaction.emoji == "▶️":
                            if current_page < len(pages) - 1:
                                current_page += 1
                                embed = self.get_embed(entries, current_page, page_size)
                                await message.edit(embed=embed)
                        elif reaction.emoji == "◀️":
                            if current_page > 0:
                                current_page -= 1
                                embed = self.get_embed(entries, current_page, page_size)
                                await message.edit(embed=embed)
                        await message.remove_reaction(reaction, user)
                    except asyncio.TimeoutError:
                        break


    def get_embed(self, entries, current_page, page_size):
        start_index = current_page * page_size + 1
        end_index = min((current_page + 1) * page_size, len(entries))
        embed = discord.Embed(title=f"Help entries ({start_index}-{end_index} of {len(entries)})")
        for i, entry in enumerate(entries[current_page * page_size: (current_page + 1) * page_size], start=start_index):
            name, tag, answer, image_url = entry
            embed.add_field(name=f"{i}. `{name}` ({tag})", value=answer, inline=False)
        return embed
    

def setup(bot):
    bot.add_cog(Entries(bot))
    print("Entries cog loaded")