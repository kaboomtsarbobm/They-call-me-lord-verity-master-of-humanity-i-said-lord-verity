import discord
from asgiref.sync import sync_to_async
from discord import app_commands
from discord.ext import commands

from . import ui


class AchievementPages(discord.ui.View):
    def __init__(self, achievements, currency_name, owner_id, completed_ids, stats):
        super().__init__(timeout=180)
        self.achievements = achievements
        self.currency_name = currency_name
        self.owner_id = owner_id
        self.completed_ids = completed_ids
        self.stats = stats
        self.page = 0
        self.message = None
        self._update_buttons()

    def _update_buttons(self):
        self.previous_button.disabled = self.page <= 0
        self.next_button.disabled = self.page >= len(self.achievements) - 1
        self.page_button.label = f"{self.page + 1}/{len(self.achievements)}"

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "https://www.youtube.com/watch?v=hiRacdl02w4",
                ephemeral=True,
            )
            return False
        return True

    def make_page(self):
        from .achievement_service import get_progress

        achievement = self.achievements[self.page]
        return ui.achievement_embed(
            achievement,
            currency_name=self.currency_name,
            done=achievement.pk in self.completed_ids,
            progress=get_progress(achievement, self.stats),
            number=self.page + 1,
            total=len(self.achievements),
            completed=len(self.completed_ids),
        )

    async def show_page(self, interaction: discord.Interaction):
        self._update_buttons()
        embed, file = self.make_page()
        await interaction.response.edit_message(
            embed=embed,
            attachments=[file] if file else [],
            view=self,
        )

    @discord.ui.button(label="Previous", emoji="◀️", style=discord.ButtonStyle.secondary)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page > 0:
            self.page -= 1
        await self.show_page(interaction)

    @discord.ui.button(label="1/1", style=discord.ButtonStyle.secondary, disabled=True)
    async def page_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        pass

    @discord.ui.button(label="Next", emoji="▶️", style=discord.ButtonStyle.primary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page < len(self.achievements) - 1:
            self.page += 1
        await self.show_page(interaction)

    async def on_timeout(self):
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except (discord.HTTPException, discord.NotFound):
                pass


async def find_balls(names):
    from bd_models.models import Ball

    found, missing = [], []
    for name in names:
        ball = await Ball.objects.filter(country__iexact=name).afirst()
        if ball is None:
            missing.append(name)
        elif ball not in found:
            found.append(ball)
    return found, missing


class AchievementDetailsModal(discord.ui.Modal, title="Achievement details"):
    title_input = discord.ui.TextInput(label="Achievement title", max_length=100)
    caption_input = discord.ui.TextInput(label="Caption", style=discord.TextStyle.paragraph, required=False, max_length=2000)
    amount_input = discord.ui.TextInput(label="Requirement amount", default="1", max_length=7)

    def __init__(self, view):
        super().__init__()
        self.creator_view = view

    async def on_submit(self, interaction: discord.Interaction):
        try:
            amount = int(str(self.amount_input.value))
            if amount < 1:
                raise ValueError
        except ValueError:
            await interaction.response.send_message("Requirement amount must be a positive number.", ephemeral=True)
            return
        self.creator_view.title_value = str(self.title_input.value).strip()
        self.creator_view.caption_value = str(self.caption_input.value)
        self.creator_view.requirement_amount = amount
        await interaction.response.send_message("Achievement details saved.", ephemeral=True)


class RequiredBallsModal(discord.ui.Modal, title="Required balls"):
    names_input = discord.ui.TextInput(
        label="Ball names, one per line",
        style=discord.TextStyle.paragraph,
        max_length=1500,
    )

    def __init__(self, view):
        super().__init__()
        self.creator_view = view

    async def on_submit(self, interaction: discord.Interaction):
        names = [line.strip() for line in str(self.names_input.value).splitlines() if line.strip()]
        found, missing = await find_balls(names)
        self.creator_view.required_balls = found
        message = f"Saved {len(found)} required ball(s)."
        if missing:
            message += f"\nCouldn't find: {', '.join(missing)}"
        await interaction.response.send_message(message, ephemeral=True)


class RewardModal(discord.ui.Modal, title="Add reward"):
    currency_amount = discord.ui.TextInput(label="Currency amount (0 if none)", default="0", max_length=9)
    ball_name = discord.ui.TextInput(label="Ball name (leave empty if none)", required=False, max_length=100)
    ball_amount = discord.ui.TextInput(label="Ball quantity", default="1", max_length=7)

    def __init__(self, view):
        super().__init__()
        self.creator_view = view

    async def on_submit(self, interaction: discord.Interaction):
        try:
            currency = int(str(self.currency_amount.value))
            quantity = int(str(self.ball_amount.value))
            if currency < 0 or quantity < 1:
                raise ValueError
        except ValueError:
            await interaction.response.send_message("Currency must be 0 or more and the ball quantity at least 1.", ephemeral=True)
            return

        ball = None
        name = str(self.ball_name.value).strip()
        if name:
            found, _ = await find_balls([name])
            if not found:
                await interaction.response.send_message(f"Couldn't find a ball called **{name}**.", ephemeral=True)
                return
            ball = found[0]

        if not currency and ball is None:
            await interaction.response.send_message("Add some currency, a ball, or both.", ephemeral=True)
            return

        if currency and ball:
            kind = "both"
        elif ball:
            kind = "ball"
        else:
            kind = "currency"
        self.creator_view.rewards.append((kind, currency, ball, quantity))
        await interaction.response.send_message(f"Reward added. Total rewards: {len(self.creator_view.rewards)}.", ephemeral=True)


class RequirementSelect(discord.ui.Select):
    def __init__(self, parent, types, row):
        self.parent_view = parent
        options = [discord.SelectOption(label=label, value=value) for value, label in types]
        placeholder = "Choose requirement type" if row == 0 else "More requirement types"
        super().__init__(placeholder=placeholder, min_values=1, max_values=1, options=options, row=row)

    async def callback(self, interaction: discord.Interaction):
        self.parent_view.requirement_type = self.values[0]
        await interaction.response.edit_message(content=self.parent_view.summary(), view=self.parent_view)


class AchievementCreatorView(discord.ui.View):
    def __init__(self, cog, owner_id, currency_name):
        super().__init__(timeout=600)
        self.cog = cog
        self.owner_id = owner_id
        self.currency_name = currency_name
        self.requirement_type = "manual"
        self.requirement_amount = 1
        self.required_balls = []
        self.rewards = []
        self.title_value = None
        self.caption_value = ""
        self.enabled = True
        from .models import Achievement

        types = list(Achievement.REQUIREMENT_TYPES)
        for row, start in enumerate(range(0, len(types), 25)):
            self.add_item(RequirementSelect(self, types[start:start + 25], row))

    async def interaction_check(self, interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("This achievement setup belongs to someone else.", ephemeral=True)
            return False
        return True

    def summary(self):
        from .models import Achievement

        labels = dict(Achievement.REQUIREMENT_TYPES)
        req = ", ".join(str(ball) for ball in self.required_balls) or "None selected"
        reward_lines = []
        for kind, currency, ball, quantity in self.rewards:
            bits = []
            if currency:
                bits.append(f"{currency} {self.currency_name}")
            if ball:
                bits.append(f"{ball} x{quantity}")
            reward_lines.append(" + ".join(bits))
        rewards = "\n".join(reward_lines) if reward_lines else "No rewards added yet"
        title = self.title_value or "Not set"
        return (
            "Configure the achievement using the menu and buttons below.\n"
            f"**Title:** {title}\n"
            f"**Requirement:** {labels.get(self.requirement_type, self.requirement_type)} (amount {self.requirement_amount})\n"
            f"**Required balls:** {req}\n"
            f"**Enabled:** {self.enabled}\n"
            f"**Rewards:**\n{rewards}"
        )

    @discord.ui.button(label="Set title and details", style=discord.ButtonStyle.primary, row=2)
    async def details_button(self, interaction, button):
        await interaction.response.send_modal(AchievementDetailsModal(self))

    @discord.ui.button(label="Required balls", style=discord.ButtonStyle.secondary, row=2)
    async def required_balls_button(self, interaction, button):
        await interaction.response.send_modal(RequiredBallsModal(self))

    @discord.ui.button(label="Add reward", style=discord.ButtonStyle.secondary, row=2)
    async def add_reward_button(self, interaction, button):
        await interaction.response.send_modal(RewardModal(self))

    @discord.ui.button(label="Toggle enabled", style=discord.ButtonStyle.secondary, row=2)
    async def toggle_enabled_button(self, interaction, button):
        self.enabled = not self.enabled
        await interaction.response.edit_message(content=self.summary(), view=self)

    @discord.ui.button(label="Create achievement", style=discord.ButtonStyle.success, row=3)
    async def create_button(self, interaction, button):
        from .models import Achievement, AchievementReward

        if not self.title_value:
            await interaction.response.send_message("Set the achievement title and details first.", ephemeral=True)
            return
        if self.requirement_type == "specific_balls" and not self.required_balls:
            await interaction.response.send_message("For the specific-balls requirement, provide at least one required ball.", ephemeral=True)
            return
        await interaction.response.defer()
        achievement = await Achievement.objects.acreate(
            title=self.title_value[:100],
            caption=self.caption_value,
            enabled=self.enabled,
            requirement_type=self.requirement_type,
            requirement_amount=self.requirement_amount,
        )
        if self.requirement_type == "specific_balls":
            await achievement.required_balls.aset(self.required_balls)
        for kind, currency, ball, quantity in self.rewards:
            await AchievementReward.objects.acreate(
                achievement=achievement,
                reward_type=kind,
                currency_amount=currency,
                ball=ball,
                ball_amount=quantity,
            )
        for child in self.children:
            child.disabled = True
        self.stop()
        await interaction.edit_original_response(
            content=f"Achievement created: **{achievement.title}** (ID {achievement.pk}). Configured {len(self.rewards)} reward(s).",
            view=self,
        )


class AchievementCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    add_group = app_commands.Group(
        name="add",
        description="Add things",
    )

    @add_group.command(
        name="achievement",
        description="Add an achievement",
    )
    async def add_achievement(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            "Hello, if you see this, you are a fuckgin idiot hahahahah 😂😂😂😂😂😂😂😂😂😂😂😂😂😂😂 "
            "https://tenor.com/view/you-are-an-idiot-gif-17637615161490421290 "
            "https://www.youtube.com/watch?v=hiRacdl02w4 "
            "https://www.youtube.com/watch?v=rYDbgQGtBF8 "
            "https://www.youtube.com/watch?v=48rz8udZBmQ",
            ephemeral=True,
        )

    async def _has_permission(self, interaction: discord.Interaction, permission: str) -> bool:
        try:
            if await self.bot.is_owner(interaction.user):
                return True
        except (AttributeError, discord.DiscordException):
            pass

        try:
            from social_django.models import UserSocialAuth

            auth_link = await UserSocialAuth.objects.select_related("user").filter(
                provider="discord", uid=str(interaction.user.id), user__is_active=True
            ).afirst()
            if auth_link is None:
                return False
            return await sync_to_async(auth_link.user.has_perm)(permission)
        except (ImportError, AttributeError, RuntimeError):
            return False

    @app_commands.command(
        name="imtotallynotaddingachievements",
        description="Create an achievement using the admin-panel permissions.",
    )
    async def imtotallynotaddingachievements(self, interaction: discord.Interaction):
        if not await self._has_permission(interaction, "achievements.add_achievement"):
            await interaction.response.send_message(
                "You do not have permission to create achievements. Ask a bot administrator to grant the achievements add permission in the admin panel.",
                ephemeral=True,
            )
            return
        from .achievement_service import get_currency_name

        view = AchievementCreatorView(self, interaction.user.id, await get_currency_name())
        await interaction.response.send_message(view.summary(), view=view, ephemeral=True)

    @app_commands.command(
        name="awardachievement",
        description="Give a player an achievement and its rewards.",
    )
    @app_commands.describe(user="The player to reward", achievement="The achievement to give")
    async def awardachievement(self, interaction: discord.Interaction, user: discord.User, achievement: str):
        if not await self._has_permission(interaction, "achievements.add_achievementcompletion"):
            await interaction.response.send_message(
                "You do not have permission to award achievements.",
                ephemeral=True,
            )
            return
        from .achievement_service import award_achievement, load_achievement

        try:
            achievement_id = int(achievement)
        except ValueError:
            await interaction.response.send_message("Pick an achievement from the list.", ephemeral=True)
            return

        found = await load_achievement(achievement_id)
        if found is None:
            await interaction.response.send_message("That achievement doesn't exist.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        given = await award_achievement(user.id, found, recipient=user)
        if given:
            await interaction.followup.send(f"Gave **{found.title}** to {user.mention}.", ephemeral=True)
        else:
            await interaction.followup.send(f"{user.mention} already has **{found.title}**.", ephemeral=True)

    @awardachievement.autocomplete("achievement")
    async def awardachievement_autocomplete(self, interaction: discord.Interaction, current: str):
        if not await self._has_permission(interaction, "achievements.add_achievementcompletion"):
            return []
        from .models import Achievement

        matches = Achievement.objects.filter(title__icontains=current).order_by("id")[:25]
        return [app_commands.Choice(name=a.title[:100], value=str(a.pk)) async for a in matches]

    @app_commands.command(
        name="achievements",
        description="i want reward for progressing in the dex.",
    )
    async def achievements(self, interaction: discord.Interaction):
        from .achievement_service import get_currency_name, load_stats
        from .models import Achievement, AchievementCompletion

        achievements = await sync_to_async(list)(
            Achievement.objects.filter(enabled=True)
            .prefetch_related("rewards__ball", "required_balls")
            .order_by("id")
        )

        if not achievements:
            await interaction.response.send_message("out of stock")
            return

        await interaction.response.defer()

        currency_name = await get_currency_name()
        stats = await load_stats(interaction.user.id)
        completed_ids = {
            achievement_id
            async for achievement_id in AchievementCompletion.objects.filter(
                discord_id=interaction.user.id,
                achievement_id__in=[a.pk for a in achievements],
            ).values_list("achievement_id", flat=True)
        }
        view = AchievementPages(
            achievements=achievements,
            currency_name=currency_name,
            owner_id=interaction.user.id,
            completed_ids=completed_ids,
            stats=stats,
        )
        embed, file = view.make_page()

        kwargs = {"embed": embed, "view": view}
        if file:
            kwargs["file"] = file
        view.message = await interaction.followup.send(wait=True, **kwargs)
