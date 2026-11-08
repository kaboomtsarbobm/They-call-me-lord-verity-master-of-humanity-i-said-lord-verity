import logging

from asgiref.sync import async_to_sync
from django.contrib import admin, messages
from django.db.models import Count
from django.utils.html import format_html

try:
    from unfold.admin import ModelAdmin, TabularInline
except ImportError:
    from django.contrib.admin import ModelAdmin, TabularInline

from .models import Achievement, AchievementCompletion, AchievementReward

log = logging.getLogger("ballsdex.packages.achievements")


class AchievementRewardInline(TabularInline):
    model = AchievementReward
    fields = ("currency_amount", "ball", "ball_amount", "special", "attack_bonus", "health_bonus")
    extra = 1
    verbose_name = "reward"
    verbose_name_plural = "Rewards (fill in money, a ball, or both)"


@admin.register(Achievement)
class AchievementAdmin(ModelAdmin):
    list_display = (
        "preview",
        "title",
        "category",
        "requirement_summary",
        "reward_summary",
        "completed_by",
        "enabled",
    )
    list_display_links = ("preview", "title")
    list_editable = ("enabled",)
    list_filter = ("enabled", "hidden", "requirement_type", "category")
    search_fields = ("title", "caption", "category")
    filter_horizontal = ("required_balls",)
    readonly_fields = ("image_preview",)
    inlines = (AchievementRewardInline,)
    fieldsets = (
        (None, {"fields": ("title", "caption", "image", "image_preview", "enabled")}),
        (
            "Requirement",
            {
                "fields": ("requirement_type", "requirement_amount", "required_balls", "required_special"),
                "description": (
                    "The amount is how many for most types. "
                    "Dex percent: 1 to 100. Attack, health and combined bonus: the minimum bonus. "
                    "Bad bonus: how far below zero. Fast catch: at most this many seconds after the spawn. "
                    "Slow catch: at least this many seconds after the spawn. Wrong guesses: how many times. "
                    "Rare balls: how many of the rarest balls count (1 means only the rarest). "
                    "Special balls: pick a special below to count only that one. "
                    "Specific balls: how many of each ball picked below (1 means just own each one). "
                    "Manual never completes by itself, give it from Achievement completions."
                ),
            },
        ),
        (
            "Customize",
            {
                "fields": (
                    "emoji",
                    "color",
                    "category",
                    "sort_order",
                    "hidden",
                    "announce",
                    "completion_message",
                    "requires",
                    "max_winners",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .annotate(_completed=Count("completions", distinct=True))
            .select_related("required_special")
            .prefetch_related("rewards__ball", "rewards__special", "required_balls")
        )

    @admin.display(description="")
    def preview(self, obj):
        return self._thumbnail(obj, 36)

    @admin.display(description="Current image")
    def image_preview(self, obj):
        return self._thumbnail(obj, 96)

    @admin.display(description="Requirement")
    def requirement_summary(self, obj):
        return obj.requirement_text()

    @admin.display(description="Rewards")
    def reward_summary(self, obj):
        texts = [text for text in (r.describe() for r in obj.rewards.all()) if text]
        return ", ".join(texts) or "-"

    @admin.display(description="Completed by", ordering="_completed")
    def completed_by(self, obj):
        return getattr(obj, "_completed", 0)

    @staticmethod
    def _thumbnail(obj, size):
        if not obj or not obj.image:
            return "-"
        try:
            url = obj.image.url
        except ValueError:
            return "-"
        return format_html(
            '<img src="{}" style="height:{}px;border-radius:6px" onerror="this.style.display=\'none\'">',
            url,
            size,
        )


@admin.register(AchievementCompletion)
class AchievementCompletionAdmin(ModelAdmin):
    list_display = ("discord_id", "achievement", "completed_at")
    list_filter = ("achievement",)
    search_fields = ("discord_id",)
    fieldsets = (
        (
            None,
            {
                "fields": ("achievement", "discord_id"),
                "description": (
                    "Adding a completion gives that player the achievement and its rewards. "
                    "Deleting one lets the player earn the achievement again."
                ),
            },
        ),
    )

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if change:
            return

        from .achievement_service import give_rewards, load_achievement

        async def give():
            achievement = await load_achievement(obj.achievement_id)
            await give_rewards(obj.discord_id, achievement)

        try:
            async_to_sync(give)()
        except Exception:
            log.exception("Could not give the rewards for completion %s", obj.pk)
            self.message_user(
                request,
                "The completion was saved but the rewards could not be given. Check the logs.",
                messages.ERROR,
            )
        else:
            self.message_user(request, f"Rewards given to {obj.discord_id}.", messages.SUCCESS)
