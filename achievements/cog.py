import os
import re
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
    @app_commands.describe(
        title="Achievement title",
        caption="Description shown to players",
        requirement_type="How players complete it",
        requirement_amount="Number required for the chosen requirement",
        required_ball_ids="Comma-separated Ball database IDs for specific_balls",
        image="Optional achievement image",
        enabled="Whether the achievement is active",
        rewards="Semicolon-separated rewards: currency:100; ball:BALL_ID:2; both:100:BALL_ID:2",
    )
    @app_commands.choices(requirement_type=[
        app_commands.Choice(name="Manual", value="manual"),
        app_commands.Choice(name="Catch a number of balls", value="catch_balls"),
        app_commands.Choice(name="Own specific balls", value="specific_balls"),
        app_commands.Choice(name="Catch unique balls", value="unique_balls"),
        app_commands.Choice(name="Catch special balls", value="catch_special"),
    ])
    async def imtotallynotaddingachievements(
        self,
        interaction: discord.Interaction,
        title: str,
        caption: str,
        requirement_type: app_commands.Choice[str],
        requirement_amount: app_commands.Range[int, 1, 1000000] = 1,
        required_ball_ids: str = "",
        image: discord.Attachment | None = None,
        enabled: bool = True,
        rewards: str = "",
    ):
        if not await self._can_create_achievements(interaction):
            await interaction.response.send_message(
                "You do not have permission to create achievements. Ask a bot administrator to grant the achievements add permission in the admin panel.",
                ephemeral=True,
            )
            return

        from bd_models.models import Ball
        from .models import Achievement, AchievementReward

        title = title.strip()
        if not title:
            await interaction.response.send_message("The achievement title cannot be empty.", ephemeral=True)
            return

        ball_ids: list[int] = []
        if required_ball_ids.strip():
            try:
                ball_ids = [int(value.strip()) for value in required_ball_ids.split(",") if value.strip()]
            except ValueError:
                await interaction.response.send_message(
                    "Required ball IDs must be comma-separated database IDs, such as 12,34.", ephemeral=True
                )
                return

        if requirement_type.value == "specific_balls" and not ball_ids:
            await interaction.response.send_message(
                "For the specific-balls requirement, provide at least one required ball ID.", ephemeral=True
            )
            return

        parsed_rewards: list[tuple[str, int, int | None, int]] = []
        for item in filter(None, (part.strip() for part in rewards.split(";"))):
            parts = [part.strip() for part in item.split(":")]
            try:
                kind = parts[0].lower()
                if kind == "currency" and len(parts) == 2:
                    amount = int(parts[1])
                    if amount < 0:
                        raise ValueError
                    parsed_rewards.append(("currency", amount, None, 1))
                elif kind == "ball" and len(parts) == 3:
                    ball_id, amount = int(parts[1]), int(parts[2])
                    if amount < 1:
                        raise ValueError
                    parsed_rewards.append(("ball", 0, ball_id, amount))
                elif kind == "both" and len(parts) == 4:
                    currency_amount, ball_id, amount = int(parts[1]), int(parts[2]), int(parts[3])
                    if currency_amount < 0 or amount < 1:
                        raise ValueError
                    parsed_rewards.append(("both", currency_amount, ball_id, amount))
                else:
                    raise ValueError
            except ValueError:
                await interaction.response.send_message(
                    "Invalid rewards format. Use currency:100; ball:BALL_ID:2; both:100:BALL_ID:2. Separate multiple rewards with semicolons.",
                    ephemeral=True,
                )
                return

        all_ball_ids = set(ball_ids)
        all_ball_ids.update(ball_id for _, _, ball_id, _ in parsed_rewards if ball_id is not None)
        balls = await sync_to_async(list)(Ball.objects.filter(pk__in=all_ball_ids)) if all_ball_ids else []
        balls_by_id = {ball.pk: ball for ball in balls}
        missing = sorted(all_ball_ids - set(balls_by_id))
        if missing:
            await interaction.response.send_message(
                f"These Ball database IDs do not exist: {', '.join(map(str, missing))}.", ephemeral=True
            )
            return

        if image is not None and not image.content_type.startswith("image/"):
            await interaction.response.send_message("The uploaded attachment must be an image.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True, thinking=True)
        achievement = await Achievement.objects.acreate(
            title=title[:100],
            caption=caption,
            enabled=enabled,
            requirement_type=requirement_type.value,
            requirement_amount=requirement_amount,
        )
        if ball_ids:
            await achievement.required_balls.aset([balls_by_id[ball_id] for ball_id in ball_ids])

        if image is not None:
            try:
                image_bytes = await image.read()
                suffix = Path(image.filename or "achievement.png").suffix.lower()
                if suffix not in {".png", ".jpg", ".jpeg", ".webp", ".gif"}:
                    suffix = ".png"
                await sync_to_async(achievement.image.save)(
                    f"achievement_{achievement.pk}{suffix}", ContentFile(image_bytes), save=True
                )
            except Exception:
                await achievement.adelete()
                await interaction.followup.send(
                    "I couldn't save that image, so the achievement was not created. Please try again with a standard image file.",
                    ephemeral=True,
                )
                return

        for kind, currency_amount, ball_id, ball_amount in parsed_rewards:
            await AchievementReward.objects.acreate(
                achievement=achievement,
                reward_type=kind,
                currency_amount=currency_amount,
                ball=balls_by_id.get(ball_id) if ball_id is not None else None,
                ball_amount=ball_amount,
            )

        await interaction.followup.send(
            f"Achievement created: **{achievement.title}** (ID {achievement.pk}). "
            f"Configured {len(parsed_rewards)} reward(s).",
            ephemeral=True,
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
