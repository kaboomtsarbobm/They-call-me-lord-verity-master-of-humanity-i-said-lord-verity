from django.contrib import admin
from django.db.models import Count
from django.utils.html import format_html

try:
    from unfold.admin import ModelAdmin, TabularInline
except ImportError:
    from django.contrib.admin import ModelAdmin, TabularInline

from .models import Achievement, AchievementReward


class AchievementRewardInline(TabularInline):
    model = AchievementReward
    fields = ("currency_amount", "ball", "ball_amount")
    extra = 1
    verbose_name = "reward"
    verbose_name_plural = "Rewards (fill in money, a ball, or both)"


@admin.register(Achievement)
class AchievementAdmin(ModelAdmin):
    list_display = (
        "preview",
        "title",
        "requirement_summary",
        "reward_summary",
        "completed_by",
        "enabled",
    )
    list_display_links = ("preview", "title")
    list_editable = ("enabled",)
    list_filter = ("enabled", "requirement_type")
    search_fields = ("title", "caption")
    filter_horizontal = ("required_balls",)
    readonly_fields = ("image_preview",)
    inlines = (AchievementRewardInline,)
    fieldsets = (
        (None, {"fields": ("title", "caption", "image", "image_preview", "enabled")}),
        (
            "Requirement",
            {
                "fields": ("requirement_type", "requirement_amount", "required_balls"),
                "description": (
                    "Manual: you give it to them yay (wip)"
                    "Catch balls/ different balls: self explanatory"
                    "Catch specific balls: catch my objects"
                ),
            },
        ),
    )

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .annotate(_completed=Count("completions", distinct=True))
            .prefetch_related("rewards__ball", "required_balls")
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
