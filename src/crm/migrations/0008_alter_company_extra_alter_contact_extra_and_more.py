# Generated by Django 4.1.4 on 2022-12-18 12:30

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("contenttypes", "0002_remove_content_type_name"),
        ("sites", "0002_alter_domain_unique"),
        ("crm", "0007_company_extra_contact_extra"),
    ]

    operations = [
        migrations.AlterField(
            model_name="company",
            name="extra",
            field=models.JSONField(default={}),
        ),
        migrations.AlterField(
            model_name="contact",
            name="extra",
            field=models.JSONField(default={}),
        ),
        migrations.CreateModel(
            name="ExtraFieldSchema",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("schema", models.JSONField()),
                ("object_id", models.UUIDField()),
                (
                    "content_type",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="contenttypes.contenttype",
                    ),
                ),
                ("portals", models.ManyToManyField(to="sites.site")),
            ],
        ),
        migrations.AddIndex(
            model_name="extrafieldschema",
            index=models.Index(
                fields=["content_type", "object_id"],
                name="crm_extrafi_content_72095b_idx",
            ),
        ),
    ]
