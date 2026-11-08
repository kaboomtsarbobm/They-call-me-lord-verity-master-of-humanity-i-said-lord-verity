from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('achievements', '0006_achievementcompletion'),
    ]

    operations = [
        migrations.AlterField(
            model_name='achievement',
            name='requirement_type',
            field=models.CharField(choices=[('manual', 'Manual'), ('catch_balls', 'catch balls'), ('specific_balls', 'catch balls but you specify them'), ('unique_balls', 'catch different balls')], default='manual', max_length=50),
        ),
        migrations.AlterField(
            model_name='achievementreward',
            name='reward_type',
            field=models.CharField(choices=[('currency', 'Money'), ('ball', 'Ball(s)'), ('both', 'Wowie Zowie!! How About Both!!')], default='currency', max_length=20),
        ),
        migrations.AlterField(
            model_name='achievementcompletion',
            name='discord_id',
            field=models.BigIntegerField(db_index=True),
        ),
    ]
