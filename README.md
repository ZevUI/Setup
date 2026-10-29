# VANTA HUB Server Creator (Render)

This bot creates the VANTA HUB channel/category/role structure in the server
configured by `GUILD_ID`.

## 1. Create the Discord application

1. Open https://discord.com/developers/applications
2. Create an application named `VANTA HUB Server Creator`.
3. Open **Bot** and add a bot.
4. Copy its token. Keep it private; never paste it into GitHub or chat.
5. Under **OAuth2 > URL Generator**, select scopes:
   - `bot`
   - `applications.commands`
6. Select bot permissions:
   - Manage Roles
   - Manage Channels
   - View Channels
   - Send Messages
   - Read Message History
   - Manage Messages (optional, for later moderation features)
7. Open the generated invite URL and add the bot to your VANTA HUB server.

## 2. Important role position

In Discord Server Settings > Roles, move the bot's own role above the roles it
needs to create/manage. Discord prevents bots from managing roles above their
highest role.

## 3. Deploy on Render

1. Upload these files to a GitHub repository.
2. In Render, choose **New + > Blueprint** and connect that repository.
3. Render reads `render.yaml` and creates a Background Worker.
4. In the Render service's Environment tab, set `DISCORD_TOKEN` to your bot token.
5. Deploy. Check the Logs tab; the bot should log in and sync `/setup`.

You can also create a **Background Worker** manually:
- Runtime: Python
- Build command: `pip install -r requirements.txt`
- Start command: `python main.py`
- Environment variables:
  - `DISCORD_TOKEN` = your bot token
  - `GUILD_ID` = `717167928255971351`

## 4. Run setup

In VANTA HUB, run `/setup` as a server administrator. It creates missing roles,
categories and channels, and reuses existing matching names. It does not delete
anything or move members.

Use `/setup_status` to check the bot.

## Notes and limitations

- A Discord bot cannot create a brand-new Discord server. Create the server
  yourself first, then invite the bot.
- Discord requires the bot's role to be above roles it manages.
- The initial setup uses safe role permissions: it does not grant Administrator
  to any newly created role. Configure trusted staff permissions manually after
  checking the role assignments.
- Channel names and emoji can be adjusted in `CATEGORY_LAYOUT` in `main.py`.
- The member/goal/site voice channels are static labels, not live counters.
- A real ticket workflow, verification flow, reaction-role assignment and live
  member counters are separate features and are not activated by merely creating
  their channels.
