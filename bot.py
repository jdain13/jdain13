import discord
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput
import datetime

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

POSITION_SLOTS = {
    "메인탱": 1,
    "1h아케인": 1,
    "그레이트 아케인": 1,
    "인큐탱(w3,w4필요)": 1,
    "메인힐": 1,
    "파티힐(w5필요)": 1,
    "섀도우 콜러": 1,
    "아이언 루트": 2,
    "블레이징": 1,
    "라콜": 4,
    "프로스트": 4,
    "DPS(무기이름도 써주세요)": 5,
}

POSITION_COLORS = {
    "메인탱": "🔵",
    "1h아케인": "🔵",
    "그레이트 아케인": "🔵",
    "인큐탱(w3,w4필요)": "🔵",
    "메인힐": "🟢",
    "파티힐(w5필요)": "🟢",
    "블레이징": "🔴",
    "섀도우 콜러": "🟣",
    "아이언 루트": "🟡",
    "라콜": "🟡",
    "프로스트": "🔷",
    "DPS(무기이름도 써주세요)": "🔴",
}

MANDATORY_POSITIONS = ["메인탱", "1h아케인", "그레이트 아케인", "메인힐", "아이언 루트"]

class RegisterModal(Modal, title="파티 정보 입력"):
    def __init__(self, view, position):
        super().__init__()
        self.view = view
        self.position = position
        self.ip_input = TextInput(label="무기플랫 (8~11)", placeholder="예: 9", required=True)
        self.gear_input = TextInput(label="방어구플랫 (8~11 스왑포함)", placeholder="예:8", required=True)

        self.add_item(self.ip_input)
        self.add_item(self.gear_input)

    async def on_submit(self, interaction: discord.Interaction):
        name = interaction.user.display_name
        ip = self.ip_input.value
        gear = self.gear_input.value

        if interaction.user.id in [p['id'] for plist in self.view.slots.values() for p in plist]:
            await interaction.response.send_message("이미 참여하셨습니다.", ephemeral=True)
            return

        self.view.slots[self.position].append({
            "name": name,
            "id": interaction.user.id,
            "ip": ip,
            "gear": gear
        })

        self.view.user_position[interaction.user.id] = self.position
        await interaction.response.edit_message(embed=self.view.make_embed(), view=self.view)

class CancelButton(Button):
    def __init__(self, view):
        super().__init__(label="지원 취소", style=discord.ButtonStyle.danger)
        self.custom_view = view

    async def callback(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        if user_id not in self.custom_view.user_position:
            await interaction.response.send_message("참여한 포지션이 없습니다.", ephemeral=True)
            return

        position = self.custom_view.user_position[user_id]
        self.custom_view.slots[position] = [p for p in self.custom_view.slots[position] if p['id'] != user_id]
        del self.custom_view.user_position[user_id]

        await interaction.response.edit_message(embed=self.custom_view.make_embed(), view=self.custom_view)

class ResetButton(Button):
    def __init__(self, view, creator_id):
        super().__init__(label="모집 데이터 삭제", style=discord.ButtonStyle.danger)
        self.custom_view = view
        self.creator_id = creator_id

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.creator_id:
            await interaction.response.send_message("이 버튼은 모집을 시작한 사람만 사용할 수 있습니다.", ephemeral=True)
            return

        try:
            await interaction.message.delete()
        except discord.NotFound:
            await interaction.response.send_message("메시지를 찾을 수 없어 삭제할 수 없습니다. 이미 삭제되었을 수 있습니다.", ephemeral=True)

class PartyRecruitView(View):
    def __init__(self, dungeon_name, dungeon_time, creator_id):
        super().__init__(timeout=None)
        self.dungeon_name = dungeon_name
        self.dungeon_time = dungeon_time
        self.slots = {pos: [] for pos in POSITION_SLOTS}
        self.user_position = {}
        self.creator_id = creator_id
        self.add_item(KickButton(self, creator_id))

        for pos in POSITION_SLOTS:
            btn = Button(label=pos, style=discord.ButtonStyle.primary)
            btn.callback = self.make_callback(pos)
            self.add_item(btn)

        self.add_item(CancelButton(self))
        self.add_item(ResetButton(self, creator_id))
        self.add_item(discord.ui.Button(
            label="장비 정보 보기",
            url="https://docs.google.com/spreadsheets/d/1HAuQhxa0bKJOc8pVFCorcjRpsi3o1mRGARHTA8dW_sE/edit?gid=292933521",
            style=discord.ButtonStyle.success
        ))

    def make_callback(self, position):
        async def callback(interaction: discord.Interaction):
            if len(self.slots[position]) >= POSITION_SLOTS[position] and interaction.user.id not in [p['id'] for p in self.slots[position]]:
                await interaction.response.send_message("이 포지션은 이미 정원이 찼습니다.", ephemeral=True)
                return
            await interaction.response.send_modal(RegisterModal(self, position))

        return callback

    def make_embed(self):
        embed = discord.Embed(
            title=f"🏰 풀클 파티 모집 - {self.dungeon_name}",
            description=f"🕒 시간: {self.dungeon_time.strftime('%H:%M')} (오늘)\n\n참가자는 버튼을 눌러 등록해 주세요!",
            color=discord.Color.green()
        )

        mandatory_missing = []
        for pos in MANDATORY_POSITIONS:
            if len(self.slots[pos]) < POSITION_SLOTS[pos]:
                mandatory_missing.append(pos)

        for pos in POSITION_SLOTS:
            entries = self.slots[pos]
            color = POSITION_COLORS.get(pos, "⚪")
            if entries:
                field_val = "\n".join([f"**{e['name']}** | 무기: {e['ip']} | 방어구: {e['gear']}" for e in entries])
            else:
                field_val = f"{color} *빈 슬롯*"
            embed.add_field(name=f"{color} {pos} ({len(entries)}/{POSITION_SLOTS[pos]})", value=field_val, inline=False)

        embed.add_field(name="\u200b", value="\u200b", inline=False)

        if mandatory_missing:
            embed.add_field(name="⚠️ 필수 포지션 부족", value=f"다음 포지션이 부족합니다: {', '.join(mandatory_missing)}", inline=False)

        total_participants = sum(len(players) for players in self.slots.values())
        embed.add_field(name="👥 총 참가자 수", value=str(total_participants), inline=False)

        return embed

@bot.command(name="풀클")
async def 풀클(ctx, time: str):
    try:
        hour, minute = map(int, time.split(":"))
        now = datetime.datetime.now()
        dt = datetime.datetime(year=now.year, month=now.month, day=now.day, hour=hour, minute=minute)
    except ValueError:
        await ctx.send("시간 형식은 HH:MM 이어야 합니다.")
        return

    dungeon_name = "풀클"
    view = PartyRecruitView(dungeon_name, dt, ctx.author.id)
    embed = view.make_embed()

    role_id = 1135695004942217378 
    await ctx.send(f"<@&{role_id}> 풀클인원 모집중 {self.dungeon_time.strftime('%H:%M')}에 시작합니다!")


class KickSelect(discord.ui.Select):
    def __init__(self, view):
        self.custom_view = view
        options = [
            discord.SelectOption(label=p["name"], value=str(p["id"]))
            for plist in view.slots.values() for p in plist
        ]
        super().__init__(placeholder="강제 취소할 유저 선택", options=options)

    async def callback(self, interaction: discord.Interaction):
        user_id = int(self.values[0])
        found = False
        for pos, plist in self.custom_view.slots.items():
            for p in plist:
                if p['id'] == user_id:
                    plist.remove(p)
                    found = True
                    break
            if found:
                break
        if user_id in self.custom_view.user_position:
            del self.custom_view.user_position[user_id]

        await interaction.response.edit_message(embed=self.custom_view.make_embed(), view=self.custom_view)

class KickButton(Button):
    def __init__(self, view, creator_id):
        super().__init__(label="지원자 강제 취소", style=discord.ButtonStyle.danger)
        self.custom_view = view
        self.creator_id = creator_id

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.creator_id:
            await interaction.response.send_message("이 버튼은 모집 생성자만 사용할 수 있습니다.", ephemeral=True)
            return

        select = KickSelect(self.custom_view)
        kick_view = View(timeout=60)
        kick_view.add_item(select)
        await interaction.response.send_message("강제 취소할 유저를 선택하세요:", view=kick_view, ephemeral=True)

@풀클.error
async def 풀클_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("사용법: !풀클[시간: HH:MM]")


from dotenv import load_dotenv
import os

load_dotenv()
bot.run(os.getenv("DISCORD_TOKEN"))

