import os
import asyncio
import logging
import discord
from discord import app_commands
from discord.ui import View, Select

# ===== LOGGING =====
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("goto-bot")

# ===== CONFIG =====
TOKEN = os.getenv("#token disc")  # îl punem în Render Env Vars
GUILD_ID = None  # pune aici un ID de server pentru sync mai rapid, ex: 123456789012345678
# ==================

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.voice_states = True

class ChannelSelect(Select):
    def __init__(self, voice_channels: list[discord.VoiceChannel], source_channel: discord.VoiceChannel):
        options = [
            discord.SelectOption(
                label=vc.name[:100],
                value=str(vc.id),
                description=f"Utilizatori: {len(vc.members)}"
            )
            for vc in voice_channels[:25]
        ]
        super().__init__(placeholder="Alege canalul destinație…", min_values=1, max_values=1, options=options)
        self.source_channel = source_channel

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            target_id = int(self.values[0])
            guild = interaction.guild
            target_channel = guild.get_channel(target_id)

            if not isinstance(target_channel, discord.VoiceChannel):
                return await interaction.followup.send("❌ Canalul ales nu mai este valid.", ephemeral=True)

            if self.source_channel.id == target_id:
                return await interaction.followup.send("ℹ️ Sursa și destinația sunt același canal.", ephemeral=True)

            moved = 0
            errors = 0
            for member in list(self.source_channel.members):
                try:
                    await member.move_to(target_channel, reason=f"/goto by {interaction.user}")
                    moved += 1
                    await asyncio.sleep(0.05)
                except:
                    errors += 1

            msg = f"✅ Am mutat **{moved}** membri din **{self.source_channel.name}** în **{target_channel.name}**."
            if errors:
                msg += f" (⚠️ {errors} ne-mutați din cauza permisiunilor/erorilor.)"

            await interaction.edit_original_response(content=msg, view=None)

        except Exception as e:
            await interaction.followup.send(f"❌ Eroare: {e}", ephemeral=True)

class ChannelSelectView(View):
    def __init__(self, voice_channels: list[discord.VoiceChannel], source_channel: discord.VoiceChannel, timeout: float = 120):
        super().__init__(timeout=timeout)
        self.add_item(ChannelSelect(voice_channels, source_channel))

class MyBot(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        if GUILD_ID:
            guild = discord.Object(id=int(GUILD_ID))
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            log.info(f"Comenzi sincronizate pe server {GUILD_ID}")
        else:
            await self.tree.sync()
            log.info("Comenzi slash sincronizate global.")

bot = MyBot()

@bot.tree.command(name="goto", description="Mută toți membrii activi din vocea ta curentă într-un alt canal de voce.")
async def goto(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True, thinking=True)
    if interaction.guild is None:
        return await interaction.followup.send("❌ Folosește comanda într-un server.", ephemeral=True)

    voice_state = interaction.user.voice
    if voice_state is None or voice_state.channel is None:
        return await interaction.followup.send("❌ Nu ești conectat la niciun canal de voce.", ephemeral=True)

    source_channel: discord.VoiceChannel = voice_state.channel
    members_in_source = [m for m in source_channel.members if not m.bot]
    if not members_in_source:
        return await interaction.followup.send(f"ℹ️ Nimeni de mutat în **{source_channel.name}**.", ephemeral=True)

    voice_channels = list(interaction.guild.voice_channels)
    if not voice_channels:
        return await interaction.followup.send("❌ Nu am găsit canale de voce în acest server.", ephemeral=True)

    view = ChannelSelectView(voice_channels=voice_channels, source_channel=source_channel)
    await interaction.followup.send(
        f"🎯 Sursa detectată: **{source_channel.name}**\nAlege canalul destinație din lista de mai jos:",
        view=view,
        ephemeral=True
    )

if __name__ == "__main__":
    if not TOKEN:
        raise SystemExit("Setează variabila DISCORD_TOKEN în Render sau direct în cod pentru test.")
    bot.run(TOKEN)
