import os
import io
import datetime
import asyncio
import threading
from flask import Flask
import discord
from discord.ext import commands
from discord.ui import Select, View, Button

# ==========================================
# 1. FLASK KEEP-ALIVE WEBSERVER (24/7)
# ==========================================
app = Flask(__name__)

@app.route('/')
def home():
    return "ENTE HOLULN Ticket Bot 24/7 амжилттай ажиллаж байна!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    thread = threading.Thread(target=run_flask)
    thread.daemon = True
    thread.start()

# ==========================================
# 2. DISCORD BOT CONFIGURATION
# ==========================================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ⚙️ ӨӨРИЙН СЕРВЕРИЙН ID-НУУДЫГ ЭНД ОРУУЛНА УУ
ADMIN_ROLE_ID = 992682483348930570      # Админ ролийн ID
TICKET_CATEGORY_ID = 1561358461206528091 # Тикетүүд нээгдэх Category ID
LOG_CHANNEL_ID = 1566358811223138375     # Хаагдсан тикетийн лог очих сувгийн ID

# ==========================================
# 3. HTML TRANSCRIPT (LOG) GENERATOR
# ==========================================
async def generate_html_transcript(channel):
    messages = []
    async for msg in channel.history(limit=None, oldest_first=True):
        messages.append(msg)

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Ticket Transcript - {channel.name}</title>
        <style>
            body {{ font-family: Arial, sans-serif; background-color: #36393f; color: #dcddde; padding: 20px; }}
            .message {{ border-bottom: 1px solid #4f545c; padding: 10px 0; }}
            .author {{ font-weight: bold; color: #7289da; }}
            .timestamp {{ font-size: 0.8em; color: #72767d; margin-left: 10px; }}
            .content {{ margin-top: 5px; line-height: 1.4; }}
            .attachment {{ margin-top: 5px; }}
            .attachment img {{ max-width: 400px; border-radius: 5px; }}
            a {{ color: #00aff4; }}
        </style>
    </head>
    <body>
        <h2>Ticket Log: {channel.name}</h2>
        <hr>
    """

    for msg in messages:
        time_str = msg.created_at.strftime("%Y-%m-%d %H:%M:%S")
        content_text = msg.clean_content.replace("\n", "<br>")
        
        attachments_html = ""
        for att in msg.attachments:
            if any(att.filename.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp']):
                attachments_html += f'<div class="attachment"><a href="{att.url}" target="_blank"><img src="{att.url}" alt="Attachment"></a></div>'
            else:
                attachments_html += f'<div class="attachment"><a href="{att.url}" target="_blank">📄 Attachment: {att.filename}</a></div>'

        html_content += f"""
        <div class="message">
            <span class="author">{msg.author.display_name} ({msg.author.name})</span>
            <span class="timestamp">{time_str}</span>
            <div class="content">{content_text}</div>
            {attachments_html}
        </div>
        """

    html_content += """
    </body>
    </html>
    """
    
    file_bytes = html_content.encode('utf-8')
    return discord.File(fp=io.BytesIO(file_bytes), filename=f"{channel.name}-log.html")

# ==========================================
# 4. TICKET CONTROL VIEW (CLAIM & CLOSE)
# ==========================================
class TicketControlView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Claim", style=discord.ButtonStyle.green, custom_id="claim_ticket_btn", emoji="🛡️")
    async def claim_button(self, interaction: discord.Interaction, button: Button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Энэ товчлуурыг зөвхөн админууд ашиглах боломжтой!", ephemeral=True)
            return

        embed = discord.Embed(
            title="🛡️ ТИКЕТ ХҮЛЭЭЖ АВСАН",
            description=f"Эрхэм хэрэглэгч таны үүсгэсэн билетийг **{interaction.user.mention}** амжилттай хүлээж авлаа.\n\n• Таны өгсөн мэдээллийг шалгаж байна, түр хүлээнэ үү.",
            color=discord.Color.green()
        )
        embed.set_footer(text=f"Хариуцаж буй админ: {interaction.user.display_name}")
        await interaction.response.send_message(content=f"{interaction.user.mention}", embed=embed)

    @discord.ui.button(label="Close", style=discord.ButtonStyle.red, custom_id="close_ticket_btn", emoji="🔒")
    async def close_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message("🔒 Энэ суваг хаагдаж, log рүү хадгалагдаж байна...")
        
        transcript_file = await generate_html_transcript(interaction.channel)
        log_channel = interaction.guild.get_channel(LOG_CHANNEL_ID)
        
        if log_channel:
            embed = discord.Embed(
                title="🎫 Ticket Closed & Logged",
                description=f"**Ticket:** `{interaction.channel.name}`\n**Closed By:** {interaction.user.mention}",
                color=discord.Color.red(),
                timestamp=datetime.datetime.utcnow()
            )
            await log_channel.send(embed=embed, file=transcript_file)

        await asyncio.sleep(5)
        await interaction.channel.delete()

# ==========================================
# 5. TICKET SELECT MENU & PANEL LOGIC
# ==========================================
class TicketSelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Clan Join", description="Кланд орох хүсэлт илгээх", emoji="🛡️"),
            discord.SelectOption(label="Support Ticket", description="Ямар нэгэн тусламж авах", emoji="🎫"),
            discord.SelectOption(label="Report Ticket", description="Админ эсвэл тоглогчид гомдол гаргах", emoji="⚠️"),
            discord.SelectOption(label="Partnership Ticket", description="Хамтын ажиллагаа болон реклам", emoji="🤝"),
        ]
        super().__init__(
            placeholder="Доорх цэснээс сонголт хийж билет нээнэ үү.", 
            min_values=1, 
            max_values=1, 
            options=options,
            custom_id="ticket_select_menu"
        )

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        member = interaction.user
        selected_value = self.values[0]

        admin_role = guild.get_role(ADMIN_ROLE_ID)
        category = guild.get_channel(TICKET_CATEGORY_ID)  # Товлосон категори

        if not category or not isinstance(category, discord.CategoryChannel):
            category = discord.utils.get(guild.categories, name="TICKETS")
            if not category:
                category = await guild.create_category("TICKETS")

        # 🔒 Эрх тохируулах (Зөвхөн хэрэглэгч, бот, админ хоёр л харна)
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            member: discord.PermissionOverwrite(read_messages=True, send_messages=True, view_channel=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, view_channel=True)
        }
        if admin_role:
            overwrites[admin_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True, view_channel=True)

        clean_name = selected_value.lower().replace(" ", "-")
        channel_name = f"ticket-{clean_name}-{member.name}"
        
        ticket_channel = await guild.create_text_channel(
            name=channel_name, 
            overwrites=overwrites, 
            category=category
        )

        admin_mention = admin_role.mention if admin_role else "@admin"

        if selected_value == "Clan Join":
            embed = discord.Embed(
                title="🛡️ ELITE CLAN — ЭЛСЭЛТИЙН ШААРДЛАГА",
                description=(
                    f"Сайн байна уу, {member.mention}!\n\n"
                    "**Доорх асуултуудад дарааллаар нь үнэн зөв хариулна уу:**\n"
                    "1. Нас: Хэдэн настай вэ?\n"
                    "2. Тоглосон цаг: CS2 дээр нийт хэдэн цаг тоглосон бэ?\n"
                    "3. Элсэх шалтгаан: Яагаад ELITE clan-д орохыг хүсэж байна вэ?\n"
                    "4. Өмнөх clan: Өмнө нь ямар ямар clan-д орж байсан бэ?\n"
                    "5. FACEIT: FACEIT-ийн түвшин хэд вэ?\n"
                    "6. Premier ELO: Premier горимын одоогийн ELO хэд вэ?\n"
                    "7. Novacs rank: Novacs дээрх rank чинь хэд вэ?\n"
                    "8. Хүйс?\n\n"
                    "━━━━━━━━━━━━━━━━━━━━ **АНХААРУУЛГА**\n"
                    "Таны хариултаас tax тань 5-20к-д бодогдоно шүү.\n"
                    "Асуултуудыг бүрэн бөглөсний дараа ELITE-ийн Lounge call-д орж, шалгуулна. "
                    "Шалгалтад тэнцсэн тохиолдолд clan-д элсэх боломжтой. Баярлалаа. ELITE-д амжилт хүсье!\n\n"
                    f"{admin_mention} - Админууд хариултыг тань шалгах болно."
                ),
                color=discord.Color.gold()
            )
        else:
            embed = discord.Embed(
                title=f"🎫 {selected_value} - Билет нээгдлээ",
                description=(
                    f"Сайн байна уу, {member.mention}!\n\n"
                    f"Та **{selected_value}** чиглэлээр билет нээсэн байна.\n"
                    "Бидэнд тулгарсан асуудал болон холбогдох дэлгэрэнгүй мэдээллээ үлдээгээрэй.\n\n"
                    f"{admin_mention} - Удахгүй админууд тантай холбогдох болно."
                ),
                color=discord.Color.blue()
            )

        embed.set_footer(text="Асуудлаа шийдвэрлэсний дараа доорх товчлуураар хаана уу.")

        await ticket_channel.send(content=f"{member.mention} {admin_mention}", embed=embed, view=TicketControlView())
        await interaction.response.send_message(f"✅ Таны билет амжилттай нээгдлээ: {ticket_channel.mention}", ephemeral=True)

class TicketView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketSelect())

# ==========================================
# 6. BOT EVENTS & COMMANDS
# ==========================================
@bot.event
async def on_ready():
    bot.add_view(TicketView())
    bot.add_view(TicketControlView())
    print(f"✅ {bot.user} тикет бот амжилттай аслаа!")

@bot.command()
@commands.has_permissions(administrator=True)
async def setup_ticket(ctx):
    embed = discord.Embed(
        title="ELITE Support Center",
        description="Доорх цэснээс сонголт хийж билет нээнэ үү.",
        color=discord.Color.dark_theme()
    )
    await ctx.send(embed=embed, view=TicketView())

@bot.command()
@commands.has_permissions(administrator=True)
async def claim(ctx):
    if not ctx.channel.name.startswith("ticket-"):
        await ctx.send("❌ Энэ команд зөвхөн тикет суваг дээр ажиллана!", delete_after=5)
        return

    admin = ctx.author
    embed = discord.Embed(
        title="🛡️ ТИКЕТ ХҮЛЭЭЖ АВСАН",
        description=f"Эрхэм хэрэглэгч таны үүсгэсэн билетийг **{admin.mention}** амжилттай хүлээж авлаа.\n\n• Таны өгсөн мэдээллийг шалгаж байна, түр хүлээнэ үү.",
        color=discord.Color.green()
    )
    embed.set_footer(text=f"Хариуцаж буй админ: {admin.display_name}")
    await ctx.message.delete()
    await ctx.send(content=f"{admin.mention}", embed=embed)

@bot.command()
async def close(ctx):
    if ctx.channel.name.startswith("ticket-"):
        await ctx.send("🔒 Энэ суваг хаагдаж, log рүү хадгалагдаж байна...")
        
        transcript_file = await generate_html_transcript(ctx.channel)
        log_channel = ctx.guild.get_channel(LOG_CHANNEL_ID)
        
        if log_channel:
            embed = discord.Embed(
                title="🎫 Ticket Closed & Logged",
                description=f"**Ticket:** `{ctx.channel.name}`\n**Closed By:** {ctx.author.mention}",
                color=discord.Color.red(),
                timestamp=datetime.datetime.utcnow()
            )
            await log_channel.send(embed=embed, file=transcript_file)

        await asyncio.sleep(5)
        await ctx.channel.delete()
    else:
        await ctx.send("❌ Энэ команд зөвхөн тикет суваг дээр ажиллана!", delete_after=5)

# ==========================================
# 7. RUN BOT
# ==========================================
if __name__ == "__main__":
    keep_alive()
    TOKEN = os.getenv("DISCORD_TOKEN")  # Render Environment Variable-аас токен уншина
    bot.run(TOKEN)