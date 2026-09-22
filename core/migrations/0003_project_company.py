from django.db import migrations, models
import django.db.models.deletion


def backfill_company(apps, schema_editor):
    Company = apps.get_model('accounts', 'Company')
    Project = apps.get_model('core', 'Project')

    orphaned = Project.objects.filter(company__isnull=True)
    if not orphaned.exists():
        return

    demo_company, _ = Company.objects.get_or_create(name='Demo Company')
    orphaned.update(company=demo_company, is_public=True)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
        ('core', '0002_jurisdiction'),
    ]

    operations = [
        migrations.AddField(
            model_name='project',
            name='is_public',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='project',
            name='company',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='projects',
                to='accounts.company',
            ),
        ),
        migrations.RunPython(backfill_company, noop_reverse),
        migrations.AlterField(
            model_name='project',
            name='company',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='projects',
                to='accounts.company',
            ),
        ),
    ]
