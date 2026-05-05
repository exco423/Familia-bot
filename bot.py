import discord
import asyncio
from datetime import datetime, timedelta
from discord.ext import commands
from discord import app_commands
import os
from dotenv import load_dotenv

load_dotenv()

GUILD_ID = 1199291746610315274
ROLE_PRESENCE_ID = 1327023008426102826
SALON_PRESENCE_ID = 1327023098679263296

CHECK_EMOJI = "✅"
CROSS_EMOJI = "❌"
LATE_EMOJI = "⌛"

intents = discord.Intents.default()
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    try:
        guild = discord.Object(id=GUILD_ID)
        bot.tree.copy_global_to(guild=guild)
        synced = await bot.tree.sync(guild=guild)
        print(f"{len(synced)} commande(s) synchronisée(s).")
    except Exception as e:
        print(f"Erreur sync : {e}")

    print(f"Bot connecté : {bot.user}")


@bot.tree.command(name="presence", description="Lancer un appel de présence")
@app_commands.describe(
    raison="La raison de la présence",
    heure_fin="Heure d'arrêt des rappels (ex: 20:00)"
)
async def presence(interaction: discord.Interaction, raison: str, heure_fin: str):
    if not interaction.user.guild_permissions.manage_roles:
        await interaction.response.send_message("❌ Tu n'as pas la permission !", ephemeral=True)
        return

    guild = interaction.guild
    if guild is None:
        await interaction.response.send_message("❌ Cette commande doit être utilisée dans le serveur.", ephemeral=True)
        return

    role = guild.get_role(ROLE_PRESENCE_ID)
    salon = guild.get_channel(SALON_PRESENCE_ID)

    if role is None or salon is None:
        await interaction.response.send_message("❌ Rôle ou salon introuvable !", ephemeral=True)
        return

    try:
        heure, minute = map(int, heure_fin.split(":"))
        maintenant = datetime.now()
        heure_stop = maintenant.replace(hour=heure, minute=minute, second=0, microsecond=0)
    except ValueError:
        await interaction.response.send_message(
            "❌ Format d'heure invalide ! Utilise `HH:MM` (ex: 20:00)",
            ephemeral=True
        )
        return

    if heure_stop <= maintenant:
        heure_stop += timedelta(days=1)

    message = await salon.send(
    f"{role.mention}\n"
    f"# {raison}\n\n"
    f"* Heure : {heure_fin}\n\n"
    f"Réagissez avec {CHECK_EMOJI} si vous serez là,\n"
    f"{CROSS_EMOJI} si vous serez absent,\n"
    f"{LATE_EMOJI} si vous serez en retard !",
    allowed_mentions=discord.AllowedMentions(roles=True)

    )

    await message.add_reaction(CHECK_EMOJI)
    await message.add_reaction(CROSS_EMOJI)
    await message.add_reaction(LATE_EMOJI)

    await interaction.response.send_message("✅ Appel de présence lancé !", ephemeral=True)

    async def rappel_loop():
        while True:
            await asyncio.sleep(4 * 3600)

            now = datetime.now()
            if now >= heure_stop:
                break

            try:
                msg = await salon.fetch_message(message.id)
            except discord.NotFound:
                break

            reactions_users = set()

            for reaction in msg.reactions:
                if str(reaction.emoji) in [CHECK_EMOJI, CROSS_EMOJI, LATE_EMOJI]:
                    async for user in reaction.users():
                        if not user.bot:
                            reactions_users.add(user.id)

            non_repondus = [
                membre for membre in role.members
                if membre.id not in reactions_users and not membre.bot
            ]

            if non_repondus:
                mentions = " ".join(m.mention for m in non_repondus)

                await salon.send(
                    f"⚠️ Rappel présence\n"
                    f"Les membres suivants n'ont pas encore répondu :\n{mentions}",
                    allowed_mentions=discord.AllowedMentions(users=True, roles=False)
                )

    asyncio.create_task(rappel_loop())


bot.run(os.getenv("TOKEN"))
