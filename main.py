import os
import logging
import discord
from discord import app_commands
from discord.ext import commands
from aiohttp import web

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)
log = logging.getLogger("vanta-hub")

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID", "717167928255971351"))
OWNER_ID = int(os.getenv("OWNER_ID", "694270550524035112"))

if not TOKEN:
    raise RuntimeError("Missing DISCORD_TOKEN environment variable.")

intents = discord.Intents.default()
intents.guilds = True

# Roles are listed from highest to lowest. The bot's own role must be
# positioned above the roles it creates in Server Settings > Roles.
ROLE_DEFINITIONS = [
    ("👑 • Owner", 0xE53935, "owner"),
    ("📝 • Lead Developer", 0x9B59B6, "staff"),
    ("💻 • Developer", 0x2ECC71, "staff"),
    ("🤖 • Bot's", 0x95A5A6, "staff"),
    ("🛠️ • Server Manager", 0xE91E63, "staff"),
    ("⚙️ • Administrator", 0xE53935, "staff"),
    ("🛡️ • Head of Support", 0xF4D03F, "staff"),
    ("🔷 • Support", 0x3498DB, "staff"),
    ("🔷 • Trial Support", 0x00BCD4, "staff"),
    ("🚀 • Friends", 0x2ECC71, "community"),
    ("🌠 • Staff Team", 0x95A5A6, "staff"),
    ("💲 • Reseller", 0x3498DB, "community"),
    ("🍀 • Premium", 0x9B59B6, "community"),
    ("🚀 • Server Booster", 0xFF4FC3, "community"),
    ("🧪 • Tester", 0x16A085, "community"),
    ("👥 • Member", 0xB23A48, "community"),
    ("🔗 • Partner", 0xA93226, "community"),
    ("🎥 • Media Partner", 0xE91E63, "community"),
    ("──────────────", 0x95A5A6, "community"),
    ("unverified", 0xFFFFFF, "restricted"),
    ("Application Blacklisted", 0x95A5A6, "restricted"),
    ("Rule's Read 📝", 0x95A5A6, "community"),
    ("Announcement Ping", 0x00D084, "community"),
    ("Giveaway Ping", 0x00D084, "community"),
    ("Script Update's Ping", 0x00D084, "community"),
    ("────────────── ", 0x95A5A6, "community"),
    ("🏢 • Office Key", 0x95A5A6, "restricted"),
    ("VaultCord verified", 0x00AA00, "community"),
]

# Each category contains (channel name, type). "voice" creates a voice channel.
CATEGORY_LAYOUT = [
    ("Main", [
        ("📋・rules", "text"),
        ("📣・announcements", "text"),
        ("📁・update-log", "text"),
        ("💲・purchase-premium", "text"),
        ("🎭・reaction-roles", "text"),
        ("💲・reseller", "text"),
    ]),
    ("Script & Key", [
        ("📜・scripts", "text"),
        ("🗝️・key", "text"),
        ("🎮・supported-games", "text"),
    ]),
    ("Support", [
        ("⁉️・faq", "text"),
        ("🎟️・ticket", "text"),
        ("💠・premium-panel", "text"),
    ]),
    ("Public", [
        ("💬・chat", "text"),
        ("💠・premium-chat", "text"),
        ("💡・suggestions", "text"),
        ("🤖・commands", "text"),
    ]),
    ("Staff", [
        ("📢・staff-announcements", "text"),
        ("💬・staff-chat", "text"),
        ("💬・reseller", "text"),
        ("🔊・Staff VC", "voice"),
        ("🏢・Zyven Office", "voice"),
    ]),
    ("🛡️・Admin / Dev", [
        ("📢・admin-announcement", "text"),
        ("💬・admin-chat", "text"),
        ("🚪・joins", "text"),
        ("⚠️・warning-logs", "text"),
        ("💬・message-logs", "text"),
        ("⏱️・timeout-logs", "text"),
        ("🥾・kick-logs", "text"),
        ("⛔・ban-logs", "text"),
        ("🛡️・channel-logs", "text"),
        ("📜・all-logs", "text"),
        ("📝・transcripts", "text"),
        ("📩・join-logs", "text"),
        ("📤・leave-logs", "text"),
        ("🎙️・vc-logs", "text"),
        ("🤖・automod-logs", "text"),
        ("🍄・vanta-loader", "text"),
        ("🪤・traps", "text"),
    ]),
]

STAFF_ROLE_NAMES = {
    "📝 • Lead Developer", "💻 • Developer", "🛠️ • Server Manager",
    "⚙️ • Administrator", "🛡️ • Head of Support", "🔷 • Support",
    "🔷 • Trial Support", "🌠 • Staff Team", "👑 • Owner"
}
ADMIN_ROLE_NAMES = {
    "👑 • Owner", "📝 • Lead Developer", "💻 • Developer",
    "🛠️ • Server Manager", "⚙️ • Administrator"
}
PREMIUM_ROLE_NAMES = {"🍀 • Premium", "👑 • Owner"} | STAFF_ROLE_NAMES

def role_color(hex_value: int) -> discord.Colour:
    return discord.Colour(hex_value)

async def get_or_create_role(guild: discord.Guild, name: str, color: int, kind: str):
    role = discord.utils.get(guild.roles, name=name)
    if role:
        return role

    # Deliberately avoid granting Administrator automatically to named roles.
    # The server owner retains control of privileged permissions.
    perms = discord.Permissions.none()
    if kind == "owner":
        # Keep the Owner role as a visual/hierarchy role; do not make it a
        # blanket admin grant that could be misused if assigned accidentally.
        pass
    return await guild.create_role(
        name=name,
        colour=role_color(color),
        permissions=perms,
        hoist=name in STAFF_ROLE_NAMES,
        mentionable=name.endswith("Ping"),
        reason="VANTA HUB automated server setup"
    )

async def get_or_create_category(guild: discord.Guild, name: str, overwrites):
    category = discord.utils.get(guild.categories, name=name)
    if category:
        await category.edit(overwrites=overwrites, reason="VANTA HUB setup permissions")
        return category
    return await guild.create_category(
        name=name, overwrites=overwrites, reason="VANTA HUB automated setup"
    )

async def ensure_channel(category, name: str, channel_type: str):
    existing = discord.utils.get(category.channels, name=name)
    if existing:
        return existing
    if channel_type == "voice":
        return await category.create_voice_channel(name, reason="VANTA HUB automated setup")
    return await category.create_text_channel(name, reason="VANTA HUB automated setup")

class VantaBot(commands.Bot):
    async def setup_hook(self):
        # Render Web Services must bind an HTTP listener to 0.0.0.0:$PORT.
        # This lightweight endpoint keeps the service healthy while the bot runs.
        async def health(_request):
            return web.json_response({"status": "ok", "service": "VANTA HUB Server Creator"})

        app = web.Application()
        app.router.add_get("/", health)
        app.router.add_get("/health", health)
        self.web_runner = web.AppRunner(app)
        await self.web_runner.setup()
        port = int(os.getenv("PORT", "10000"))
        self.web_site = web.TCPSite(self.web_runner, "0.0.0.0", port)
        await self.web_site.start()
        log.info("Render health server listening on 0.0.0.0:%s", port)

        guild_obj = discord.Object(id=GUILD_ID)
        self.tree.copy_global_to(guild=guild_obj)
        await self.tree.sync(guild=guild_obj)
        log.info("Slash commands synced to guild %s", GUILD_ID)

    async def close(self):
        if getattr(self, "web_runner", None):
            await self.web_runner.cleanup()
        await super().close()

bot = VantaBot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    log.info("Logged in as %s (%s)", bot.user, bot.user.id)

@bot.tree.command(name="setup", description="Create the VANTA HUB server layout")
@app_commands.guild_only()
async def setup_server(interaction: discord.Interaction):
    if interaction.guild_id != GUILD_ID:
        await interaction.response.send_message(
            "This bot is configured for a different server.", ephemeral=True
        )
        return

    if interaction.user.id != OWNER_ID and not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(
            "Only the configured bot owner or a server administrator can run this setup.", ephemeral=True
        )
        return

    await interaction.response.defer(ephemeral=True, thinking=True)
    guild = interaction.guild
    try:
        role_map = {}
        for name, color, kind in ROLE_DEFINITIONS:
            role_map[name] = await get_or_create_role(guild, name, color, kind)

        # Reorder created roles to follow the reference hierarchy (highest first).
        # The bot's own role still needs to sit above this entire group.
        role_positions = {}
        bot_member = guild.me

if bot_member is None:
    bot_member = await guild.fetch_member(bot.user.id)

top_position = max(1, bot_member.top_role.position - 1)
        for index, (name, _color, _kind) in enumerate(ROLE_DEFINITIONS):
            role = role_map[name]
            target = top_position - index
            if target > 0:
                role_positions[role] = target
        if role_positions:
            try:
                await guild.edit_role_positions(positions=role_positions, reason="VANTA HUB role hierarchy")
            except discord.HTTPException:
                log.warning("Could not automatically reorder roles; arrange them manually in Server Settings > Roles.")

        everyone = guild.default_role
        unverified = role_map["unverified"]
        member = role_map["👥 • Member"]
        premium = role_map["🍀 • Premium"]

        public_overwrites = {
            everyone: discord.PermissionOverwrite(view_channel=False),
            unverified: discord.PermissionOverwrite(view_channel=True, read_message_history=True),
            member: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
        }
        staff_overwrites = {
            everyone: discord.PermissionOverwrite(view_channel=False),
        }
        admin_overwrites = {
            everyone: discord.PermissionOverwrite(view_channel=False),
        }
        for role_name in STAFF_ROLE_NAMES | {"💲 • Reseller"}:
            role = role_map.get(role_name)
            if role:
                staff_overwrites[role] = discord.PermissionOverwrite(
                    view_channel=True, send_messages=True, read_message_history=True,
                    connect=True, speak=True
                )
        for role_name in ADMIN_ROLE_NAMES:
            role = role_map.get(role_name)
            if role:
                admin_overwrites[role] = discord.PermissionOverwrite(
                    view_channel=True, send_messages=True, read_message_history=True,
                    manage_messages=True, manage_channels=True
                )

        created_categories = 0
        created_channels = 0
        for category_name, channels in CATEGORY_LAYOUT:
            if category_name == "Staff":
                overwrites = staff_overwrites
            elif "Admin" in category_name:
                overwrites = admin_overwrites
            else:
                overwrites = public_overwrites.copy()
                if category_name == "Public":
                    overwrites[premium] = discord.PermissionOverwrite(
                        view_channel=True, send_messages=True, read_message_history=True
                    )
                    overwrites[member] = discord.PermissionOverwrite(
                        view_channel=True, send_messages=True, read_message_history=True
                    )
                if category_name == "Support":
                    for role_name in STAFF_ROLE_NAMES:
                        role = role_map.get(role_name)
                        if role:
                            overwrites[role] = discord.PermissionOverwrite(
                                view_channel=True, send_messages=True, read_message_history=True
                            )
            category = discord.utils.get(guild.categories, name=category_name)
            if category is None:
                category = await guild.create_category(
                    name=category_name, overwrites=overwrites,
                    reason="VANTA HUB automated setup"
                )
                created_categories += 1
            else:
                await category.edit(overwrites=overwrites, reason="VANTA HUB setup permissions")

            for channel_name, channel_type in channels:
                before = discord.utils.get(category.channels, name=channel_name)
                channel = await ensure_channel(category, channel_name, channel_type)
                if before is None:
                    created_channels += 1
                # Premium chat is restricted to Premium and staff roles.
                if channel_name == "💠・premium-chat":
                    premium_overwrites = {
                        everyone: discord.PermissionOverwrite(view_channel=False),
                        premium: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
                    }
                    for role_name in STAFF_ROLE_NAMES:
                        role = role_map.get(role_name)
                        if role:
                            premium_overwrites[role] = discord.PermissionOverwrite(
                                view_channel=True, send_messages=True, read_message_history=True
                            )
                    await channel.edit(overwrites=premium_overwrites, reason="VANTA HUB premium chat access")

        # Create read-only counter/info voice channels similar to the reference.
        info_category = discord.utils.get(guild.categories, name="Main")
        info_specs = [
            ("🧬・verify", "text"),
            ("👤・Members: stats", "voice"),
            ("🎯・Goal: 5000", "voice"),
            ("🌐・vantahub", "voice"),
        ]
        for name, channel_type in info_specs:
            before = discord.utils.get(info_category.channels, name=name)
            channel = await ensure_channel(info_category, name, channel_type)
            if channel_type == "voice":
                await channel.set_permissions(everyone, connect=False, view_channel=True)
            if before is None:
                created_channels += 1

        await interaction.followup.send(
            f"**VANTA HUB setup complete.**\n"
            f"Created: {created_categories} categories, {created_channels} channels.\n"
            f"Roles checked/created: {len(role_map)}.\n\n"
            "Existing channels and roles with matching names were reused. "
            "No existing channels, roles, or members were deleted or moved.",
            ephemeral=True
        )
    except discord.Forbidden:
        await interaction.followup.send(
            "I don't have enough permissions. Give the bot **Manage Roles**, "
            "**Manage Channels**, and **View Channels**, then move the bot's role "
            "above the roles it needs to create/manage.",
            ephemeral=True
        )
    except Exception:
        log.exception("Setup failed")
        await interaction.followup.send(
            "Setup stopped because of an error. Check the Render logs for details.",
            ephemeral=True
        )

@bot.tree.command(name="setup_status", description="Check the VANTA HUB setup")
@app_commands.guild_only()
async def setup_status(interaction: discord.Interaction):
    if interaction.guild_id != GUILD_ID:
        await interaction.response.send_message("Wrong server.", ephemeral=True)
        return
    await interaction.response.send_message(
        f"VANTA HUB bot is online. Server: **{interaction.guild.name}** "
        f"(`{interaction.guild.id}`).",
        ephemeral=True
    )

bot.run(TOKEN)
