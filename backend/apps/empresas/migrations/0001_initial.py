import uuid
import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Empresa",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("is_active", models.BooleanField(default=True)),
                ("razao_social", models.CharField(max_length=300, verbose_name="Razão Social")),
                ("nome_fantasia", models.CharField(blank=True, max_length=300, verbose_name="Nome Fantasia")),
                ("cnpj", models.CharField(max_length=14, unique=True, verbose_name="CNPJ")),
                ("telefone", models.CharField(blank=True, max_length=15)),
                ("email", models.EmailField(blank=True, max_length=254)),
                ("plano", models.CharField(
                    choices=[("basico", "Básico"), ("profissional", "Profissional"), ("enterprise", "Enterprise")],
                    default="basico",
                    max_length=20,
                )),
                ("limite_usuarios", models.PositiveIntegerField(
                    default=10,
                    validators=[django.core.validators.MinValueValidator(1)],
                    verbose_name="Limite de Usuários",
                )),
            ],
            options={
                "verbose_name": "Empresa",
                "verbose_name_plural": "Empresas",
                "ordering": ["-created_at"],
                "abstract": False,
                "indexes": [
                    models.Index(fields=["cnpj"], name="empresas_em_cnpj_idx"),
                    models.Index(fields=["is_active"], name="empresas_em_is_acti_idx"),
                ],
            },
        ),
    ]
