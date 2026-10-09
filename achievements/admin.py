from django.contrib import admin

from .models import Achievement, AchievementReward


class AchievementRewardInline(admin.StackedInline):
    model = AchievementReward
    extra = 1


@admin.register(Achievement)
class AchievementAdmin(admin.ModelAdmin):
    list_display = ("title", "requirement_type", "requirement_amount", "enabled")
    list_filter = ("enabled", "requirement_type")
    search_fields = ("title", "caption")
    filter_horizontal = ("required_balls",)
    inlines = (AchievementRewardInline,)