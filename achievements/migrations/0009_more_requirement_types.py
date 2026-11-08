from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('achievements', '0008_playerstat_more_requirements'),
    ]

    operations = [
        migrations.AddField(
            model_name='playerstat',
            name='slowest_catch',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='playerstat',
            name='best_redemption',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='playerstat',
            name='late_attempts',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='playerstat',
            name='active_days',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='playerstat',
            name='weekend_catches',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='achievement',
            name='requirement_type',
            field=models.CharField(choices=[('manual', 'Manual'), ('catch_balls', 'catch balls'), ('specific_balls', 'catch balls but you specify them'), ('unique_balls', 'catch different balls'), ('catch_special', 'own special balls'), ('duplicate_balls', 'own copies of the same ball'), ('dex_percent', 'complete a percent of the dex'), ('attack_bonus', 'own a ball with an attack bonus'), ('health_bonus', 'own a ball with a health bonus'), ('money', 'have currency'), ('servers', 'catch balls in different servers'), ('total_catches', 'catch balls (all time)'), ('catch_streak', 'catch balls in a row without a wrong guess'), ('daily_streak', 'catch a ball every day'), ('catches_today', 'catch balls in one day'), ('fast_catch', 'catch a ball fast'), ('wrong_streak', 'get a name wrong in a row'), ('wrong_total', 'get names wrong in total'), ('special_variety', 'own balls from different specials'), ('regimes', 'own balls from different regimes'), ('economies', 'own balls from different economies'), ('combined_bonus', 'own a ball with a combined bonus'), ('bad_bonus', 'own a ball with a bad bonus'), ('slow_catch', 'catch a ball slowly'), ('redemption', 'catch a ball after wrong guesses'), ('too_slow', 'be too slow to catch'), ('active_days', 'catch balls on different days'), ('weekend_catches', 'catch balls on weekends'), ('traded_balls', 'own balls from other players')], default='manual', max_length=50),
        ),
    ]
