import os

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
