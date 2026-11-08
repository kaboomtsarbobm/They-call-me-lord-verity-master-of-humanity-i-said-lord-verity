import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('achievements', '0009_more_requirement_types'),
        ('bd_models', '0019_guildconfig_tips_enabled'),
    ]

    operations = [
        migrations.RemoveField(model_name='playerstat', name='daily_streak'),
        migrations.RemoveField(model_name='playerstat', name='best_daily_streak'),
        migrations.RemoveField(model_name='playerstat', name='last_catch_day'),
        migrations.RemoveField(model_name='playerstat', name='catches_today'),
        migrations.RemoveField(model_name='playerstat', name='best_catches_in_day'),
        migrations.RemoveField(model_name='playerstat', name='active_days'),
        migrations.RemoveField(model_name='playerstat', name='weekend_catches'),
        migrations.AddField(
            model_name='playerstat',
            name='special_catches',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='playerstat',
            name='quick_catches',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='playerstat',
            name='first_try_catches',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AlterModelOptions(
            name='achievement',
            options={'ordering': ['sort_order', 'id']},
        ),
        migrations.AddField(
            model_name='achievement',
            name='emoji',
            field=models.CharField(blank=True, help_text='Shown before the title. Leave empty for the trophy.', max_length=32),
        ),
        migrations.AddField(
            model_name='achievement',
            name='color',
            field=models.CharField(blank=True, help_text='Embed color as hex, like #FFAA00. Leave empty for the default.', max_length=7),
        ),
        migrations.AddField(
            model_name='achievement',
            name='category',
            field=models.CharField(blank=True, help_text='Small label shown at the bottom of the embed.', max_length=50),
        ),
        migrations.AddField(
            model_name='achievement',
            name='sort_order',
            field=models.IntegerField(default=0, help_text='Lower numbers show first in /achievements.'),
        ),
        migrations.AddField(
            model_name='achievement',
            name='hidden',
            field=models.BooleanField(default=False, help_text='Players only see ??? until they complete it.'),
        ),
        migrations.AddField(
            model_name='achievement',
            name='announce',
            field=models.BooleanField(default=True, help_text='Send the completion message to the player.'),
        ),
        migrations.AddField(
            model_name='achievement',
            name='completion_message',
            field=models.TextField(blank=True, help_text='Extra text shown in the completion message.'),
        ),
        migrations.AddField(
            model_name='achievement',
            name='requires',
            field=models.ForeignKey(blank=True, help_text='Players must complete this achievement first.', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='unlocks', to='achievements.achievement'),
        ),
        migrations.AddField(
            model_name='achievement',
            name='max_winners',
            field=models.PositiveIntegerField(default=0, help_text='Only the first players can complete it. 0 means no limit.'),
        ),
        migrations.AddField(
            model_name='achievement',
            name='required_special',
            field=models.ForeignKey(blank=True, help_text='Only used by the special balls type: count just this special.', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='required_for_achievements', to='bd_models.special'),
        ),
        migrations.AddField(
            model_name='achievementreward',
            name='special',
            field=models.ForeignKey(blank=True, help_text='Give the ball with this special.', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='achievement_rewards', to='bd_models.special'),
        ),
        migrations.AddField(
            model_name='achievementreward',
            name='attack_bonus',
            field=models.IntegerField(default=0, help_text='Attack bonus of the ball given, in percent.'),
        ),
        migrations.AddField(
            model_name='achievementreward',
            name='health_bonus',
            field=models.IntegerField(default=0, help_text='Health bonus of the ball given, in percent.'),
        ),
        migrations.AlterField(
            model_name='achievement',
            name='requirement_type',
            field=models.CharField(choices=[('manual', 'Manual'), ('catch_balls', 'catch balls'), ('specific_balls', 'catch balls but you specify them'), ('unique_balls', 'catch different balls'), ('catch_special', 'own special balls'), ('duplicate_balls', 'own copies of the same ball'), ('dex_percent', 'complete a percent of the dex'), ('attack_bonus', 'own a ball with an attack bonus'), ('health_bonus', 'own a ball with a health bonus'), ('money', 'have currency'), ('servers', 'catch balls in different servers'), ('total_catches', 'catch balls (all time)'), ('catch_streak', 'catch balls in a row without a wrong guess'), ('fast_catch', 'catch a ball fast'), ('wrong_streak', 'get a name wrong in a row'), ('wrong_total', 'get names wrong in total'), ('special_variety', 'own balls from different specials'), ('regimes', 'own balls from different regimes'), ('economies', 'own balls from different economies'), ('combined_bonus', 'own a ball with a combined bonus'), ('bad_bonus', 'own a ball with a bad bonus'), ('slow_catch', 'catch a ball slowly'), ('redemption', 'catch a ball after wrong guesses'), ('too_slow', 'be too slow to catch'), ('traded_balls', 'own balls from other players'), ('special_catches', 'catch special balls (all time)'), ('rare_balls', 'own one of the rarest balls'), ('server_balls', 'own balls caught in the same server'), ('quick_catches', 'catch balls within 10 seconds'), ('first_try_catches', 'catch balls on the first try'), ('achievements_done', 'complete achievements'), ('same_regime', 'own balls from the same regime'), ('same_economy', 'own balls from the same economy')], default='manual', max_length=50),
        ),
    ]
