import os
from pathlib import Path

from django.core.files.base import ContentFile

import discord
from asgiref.sync import sync_to_async
from discord import app_commands
from discord.ext import commands


class AchievementPages(discord.ui.View):
    def __init__(self, achievements, currency_name, owner_id, completed_ids):
        super().__init__(timeout=180)
        self.achievements = achievements
        self.currency_name = currency_name
        self.owner_id = owner_id
        self.completed_ids = completed_ids
        self.page = 0
        self.message = None
        self._update_buttons()

    def _update_buttons(self):
        self.previous_button.disabled = self.page <= 0
        self.next_button.disabled = self.page >= len(self.achievements) - 1

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "https://www.youtube.com/watch?v=hiRacdl02w4",
                ephemeral=True,
            )
            return False
        return True

    def make_page(self):
        achievement = self.achievements[self.page]
        value = achievement.caption or "No description."
        if achievement.id in self.completed_ids:
            value = "**Status:** ✅ Its Done.\n\n" + value
        else:
            value = "**Status:** ⏳ Im waitin.\n\n" + value

        rewards = list(achievement.rewards.all())
        if rewards:
            reward_text = []
            for reward in rewards:
                if reward.reward_type == "currency":
                    reward_text.append(
                        f"{reward.currency_amount} {self.currency_name}"
                    )
                elif reward.reward_type == "ball":
                    if reward.ball:
                        reward_text.append(
                            f"{reward.ball} x{reward.ball_amount}"
                        )
                elif reward.reward_type == "both":
                    parts = []
                    if reward.currency_amount:
                        parts.append(
                            f"{reward.currency_amount} {self.currency_name}"
                        )
                    if reward.ball:
                        parts.append(
                            f"{reward.ball} x{reward.ball_amount}"
                        )
                    if parts:
                        reward_text.append(" + ".join(parts))

            if reward_text:
                value += "\n\n**FREE!! Reward:**\n" + "\n".join(reward_text)

        embed = discord.Embed(
            title="Achievements",
            description="I WANT FREE REWARDS",
        )
        file = None
        if achievement.image:
            image_path = achievement.image.path
            if os.path.exists(image_path):
                extension = os.path.splitext(image_path)[1] or ".png"
                filename = f"achievement_{achievement.id}{extension}"
                file = discord.File(image_path, filename=filename)
                # Attach the image to the embed as a thumbnail so Discord places
                # it beside the achievement text instead of rendering it separately.
                embed.set_thumbnail(url=f"attachment://{filename}")

        embed.add_field(
            name=f"**🏆 {achievement.title}**",
            value=value,
            inline=False,
        )
        embed.set_footer(
            text=f"Page {self.page + 1}/{len(self.achievements)}"
        )

        return embed, file

    async def show_page(self, interaction: discord.Interaction):
        self._update_buttons()
        embed, file = self.make_page()
        await interaction.response.edit_message(
            embed=embed,
            attachments=[file] if file else [],
            view=self,
        )

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.secondary)
    async def previous_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        if self.page > 0:
            self.page -= 1
        await self.show_page(interaction)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.primary)
    async def next_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
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


class RewardAmountModal(discord.ui.Modal, title="Reward amounts"):
    currency_amount = discord.ui.TextInput(label="Currency amount (0 if none)", default="0", max_length=9)
    ball_amount = discord.ui.TextInput(label="Ball quantity (0 if none)", default="0", max_length=7)

    def __init__(self, view):
        super().__init__()
        self.creator_view = view

    async def on_submit(self, interaction: discord.Interaction):
        try:
            currency = int(str(self.currency_amount.value))
            quantity = int(str(self.ball_amount.value))
            if currency < 0 or quantity < 0 or (currency == 0 and quantity == 0):
                raise ValueError
            if quantity and self.creator_view.reward_ball is None:
                await interaction.response.send_message("Select a reward ball before setting a ball quantity.", ephemeral=True)
                return
        except ValueError:
            await interaction.response.send_message("Enter non-negative amounts, and make at least one reward amount greater than zero.", ephemeral=True)
            return
        if currency and quantity:
            kind = "both"
        elif currency:
            kind = "currency"
        else:
            kind = "ball"
        self.creator_view.rewards.append((kind, currency, self.creator_view.reward_ball if quantity else None, quantity or 1))
        await interaction.response.send_message(f"Reward added. Total rewards: {len(self.creator_view.rewards)}.", ephemeral=True)


class RequirementSelect(discord.ui.Select):
    def __init__(self, parent):
        self.parent_view = parent
        options = [
            discord.SelectOption(label="Manual", value="manual"),
            discord.SelectOption(label="Catch a number of balls", value="catch_balls"),
            discord.SelectOption(label="Own specific balls", value="specific_balls"),
            discord.SelectOption(label="Catch unique balls", value="unique_balls"),
            discord.SelectOption(label="Catch special balls", value="catch_special"),
        ]
        super().__init__(placeholder="Choose requirement type", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        self.parent_view.requirement_type = self.values[0]
        await interaction.response.edit_message(content=self.parent_view.summary(), view=self.parent_view)


class RequiredBallsSelect(discord.ui.Select):
    def __init__(self, parent, balls):
        self.parent_view = parent
        self.ball_lookup = {str(ball.pk): ball for ball in balls}
        options = [discord.SelectOption(label=str(getattr(ball, "country", ball))[:100], value=str(ball.pk)) for ball in balls[:25]]
        if not options:
            options = [discord.SelectOption(label="No configured balls found", value="none", default=True)]
            disabled = True
        else:
            disabled = False
        super().__init__(placeholder="Choose required balls (up to 25 shown)", min_values=0, max_values=len(options), options=options, disabled=disabled)

    async def callback(self, interaction: discord.Interaction):
        self.parent_view.required_balls = [self.ball_lookup[v] for v in self.values if v in self.ball_lookup]
        await interaction.response.edit_message(content=self.parent_view.summary(), view=self.parent_view)


class RewardBallSelect(discord.ui.Select):
    def __init__(self, parent, balls):
        self.parent_view = parent
        self.ball_lookup = {str(ball.pk): ball for ball in balls}
        options = [discord.SelectOption(label=str(getattr(ball, "country", ball))[:100], value=str(ball.pk)) for ball in balls[:25]]
        if not options:
            options = [discord.SelectOption(label="No configured balls found", value="none", default=True)]
        super().__init__(placeholder="Choose a ball to include in a reward", min_values=1, max_values=1, options=options, disabled=not bool(self.ball_lookup))

    async def callback(self, interaction: discord.Interaction):
        self.parent_view.reward_ball = self.ball_lookup.get(self.values[0])
        await interaction.response.edit_message(content=self.parent_view.summary(), view=self.parent_view)


class AchievementCreatorView(discord.ui.View):
    def __init__(self, cog, owner_id, balls):
        super().__init__(timeout=600)
        self.cog = cog
        self.owner_id = owner_id
        self.balls = balls
        self.requirement_type = "manual"
        self.requirement_amount = 1
        self.required_balls = []
        self.reward_ball = None
        self.rewards = []
        self.title_value = None
        self.caption_value = ""
        self.image = None
        self.enabled = True
        self.add_item(RequirementSelect(self))
        self.add_item(RequiredBallsSelect(self, balls))
        self.add_item(RewardBallSelect(self, balls))

    async def interaction_check(self, interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("This achievement setup belongs to someone else.", ephemeral=True)
            return False
        return True

    def summary(self):
        req = ", ".join(str(getattr(b, "country", b)) for b in self.required_balls) or "None selected"
        reward_lines = []
        for kind, currency, ball, quantity in self.rewards:
            bits = []
            if currency:
                bits.append(f"{currency} currency")
            if ball:
                bits.append(f"{getattr(ball, 'country', ball)} x{quantity}")
            reward_lines.append(" + ".join(bits))
        rewards = "\n".join(reward_lines) if reward_lines else "No rewards added yet"
        title = self.title_value or "Not set"
        return f"Configure the achievement using the menus below.\n**Title:** {title}\n**Requirement:** {self.requirement_type} (amount {self.requirement_amount})\n**Required balls:** {req}\n**Rewards:**\n{rewards}"

    @discord.ui.button(label="Set title and details", style=discord.ButtonStyle.primary, row=3)
    async def details_button(self, interaction, button):
        await interaction.response.send_modal(AchievementDetailsModal(self))

    @discord.ui.button(label="Add reward", style=discord.ButtonStyle.secondary, row=3)
    async def add_reward_button(self, interaction, button):
        await interaction.response.send_modal(RewardAmountModal(self))

    @discord.ui.button(label="Toggle enabled", style=discord.ButtonStyle.secondary, row=3)
    async def toggle_enabled_button(self, interaction, button):
        self.enabled = not self.enabled
        await interaction.response.edit_message(content=self.summary() + f"\n**Enabled:** {self.enabled}", view=self)

    @discord.ui.button(label="Create achievement", style=discord.ButtonStyle.success, row=4)
    async def create_button(self, interaction, button):
        from .models import Achievement, AchievementReward
        if not self.title_value:
            await interaction.response.send_message("Set the achievement title and details first.", ephemeral=True)
            return
        if self.requirement_type == "specific_balls" and not self.required_balls:
            await interaction.response.send_message("For the specific-balls requirement, provide at least one required ball.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        achievement = await Achievement.objects.acreate(
            title=self.title_value[:100], caption=self.caption_value, enabled=self.enabled,
            requirement_type=self.requirement_type, requirement_amount=self.requirement_amount,
        )
        if self.required_balls:
            await achievement.required_balls.aset(self.required_balls)
        for kind, currency, ball, quantity in self.rewards:
            await AchievementReward.objects.acreate(
                achievement=achievement, reward_type=kind, currency_amount=currency,
                ball=ball, ball_amount=quantity,
            )
        await interaction.followup.send(
            f"Achievement created: **{achievement.title}** (ID {achievement.pk}). Configured {len(self.rewards)} reward(s).",
            ephemeral=True,
        )
        for child in self.children:
            child.disabled = True
        try:
            await interaction.message.edit(view=self)
        except discord.HTTPException:
            pass


class AchievementCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def on_ballsdex_ball_caught(self, event):
        """Check achievement progress after BallsDex reports a successful catch."""
        from .achievement_service import check_achievements

        await check_achievements(event.player, None)

    async def _currency_name(self):
        """Read the currency label configured in BallsDex's settings."""
        try:
            from django.apps import apps

            for model in apps.get_models():
                field_names = {field.name for field in model._meta.get_fields()}
                if "currency_name" not in field_names:
                    continue
                settings = await sync_to_async(model.objects.first)()
                if settings:
                    name = getattr(settings, "currency_name", None)
                    if name:
                        return str(name)
        except (ImportError, AttributeError, RuntimeError):
            pass
        return "currency"

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

    async def _can_create_achievements(self, interaction: discord.Interaction) -> bool:
        """Use the bot owner or the Django permissions configured in the admin panel."""
        try:
            if await self.bot.is_owner(interaction.user):
                return True
        except (AttributeError, discord.DiscordException):
            pass

        # BallsDex admin-panel Discord OAuth users are linked through UserSocialAuth.
        # Requiring the model permission means a panel administrator must explicitly
        # grant this permission (directly or through a Django group).
        try:
            from social_django.models import UserSocialAuth

            auth_link = await UserSocialAuth.objects.select_related("user").filter(
                provider="discord", uid=str(interaction.user.id), user__is_active=True
            ).afirst()
            if auth_link is None:
                return False
            return await sync_to_async(auth_link.user.has_perm)(
                "achievements.add_achievement"
            )
        except (ImportError, AttributeError, RuntimeError):
            return False

    @app_commands.command(
        name="imtotallynotaddingachievements",
        description="Create an achievement using the admin-panel permissions.",
    )
    async def imtotallynotaddingachievements(self, interaction: discord.Interaction):
        if not await self._can_create_achievements(interaction):
            await interaction.response.send_message(
                "You do not have permission to create achievements. Ask a bot administrator to grant the achievements add permission in the admin panel.",
                ephemeral=True,
            )
            return
        from bd_models.models import Ball
        balls = await sync_to_async(list)(Ball.objects.all().order_by("country"))
        view = AchievementCreatorView(self, interaction.user.id, balls)
        await interaction.response.send_message(
            "Configure the achievement using the menus below.", view=view, ephemeral=True
        )

    @app_commands.command(
        name="achievements",
        description="i want reward for progressing in the dex.",
    )
    async def achievements(self, interaction: discord.Interaction):
        from .models import Achievement, AchievementCompletion

        achievements = await sync_to_async(list)(
            Achievement.objects.filter(enabled=True)
            .prefetch_related("rewards__ball", "required_balls")
            .order_by("id")
        )

        if not achievements:
            await interaction.response.send_message("out of stock")
            return

        currency_name = await self._currency_name()
        completed_ids = set(await sync_to_async(list)(
            AchievementCompletion.objects.filter(
                discord_id=interaction.user.id,
                achievement__in=achievements,
            ).values_list("achievement_id", flat=True)
        ))
        view = AchievementPages(
            achievements=achievements,
            currency_name=currency_name,
            owner_id=interaction.user.id,
            completed_ids=completed_ids,
        )
        embed, file = view.make_page()

        if file:
            await interaction.response.send_message(
                embed=embed,
                file=file,
                view=view,
            )
        else:
            await interaction.response.send_message(
                embed=embed,
                view=view,
            )

        view.message = await interaction.original_response()


async def setup(bot):
    await bot.add_cog(AchievementCog(bot))
