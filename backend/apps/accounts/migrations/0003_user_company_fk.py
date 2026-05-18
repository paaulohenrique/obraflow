"""Replace the loose company_id UUIDField on User with a proper FK to Empresa.

Migration steps:
1. Rename old company_id UUID column to _legacy_company_id
2. Add company ForeignKey (nullable)
3. Data-migrate: create one Empresa per unique _legacy_company_id, link users
4. Remove _legacy_company_id
"""
import uuid as uuid_module
from django.db import migrations, models
import django.db.models.deletion


_DEFAULT_EMPRESA_ID = uuid_module.UUID("00000000-0000-0000-0000-000000000001")
_DEFAULT_CNPJ = "00000000000191"  # placeholder Fazenda Nacional CNPJ (valid checksum)


def _migrate_forward(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    Empresa = apps.get_model("empresas", "Empresa")

    # Collect all unique legacy company UUIDs (excluding None)
    legacy_ids = set(
        User.objects.exclude(_legacy_company_id__isnull=True)
        .values_list("_legacy_company_id", flat=True)
        .distinct()
    )

    # Create one Empresa per unique UUID, reusing the same UUID as pk
    for cid in legacy_ids:
        Empresa.objects.get_or_create(
            id=cid,
            defaults={
                "razao_social": f"Empresa Migrada {str(cid)[:8].upper()}",
                "cnpj": str(cid).replace("-", "")[:14].ljust(14, "0"),
                "is_active": True,
                "plano": "basico",
                "limite_usuarios": 50,
            },
        )

    # Users without a company_id get a shared default placeholder Empresa
    users_without_company = User.objects.filter(_legacy_company_id__isnull=True)
    if users_without_company.exists():
        default_empresa, _ = Empresa.objects.get_or_create(
            id=_DEFAULT_EMPRESA_ID,
            defaults={
                "razao_social": "Empresa Padrão",
                "cnpj": _DEFAULT_CNPJ,
                "is_active": True,
                "plano": "basico",
                "limite_usuarios": 50,
            },
        )
        users_without_company.update(company=default_empresa)

    # Link every user that had a legacy company_id
    for user in User.objects.filter(_legacy_company_id__isnull=False):
        empresa = Empresa.objects.get(id=user._legacy_company_id)
        user.company = empresa
        user.save(update_fields=["company"])


def _migrate_backward(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    for user in User.objects.select_related("company").all():
        if user.company_id:
            user._legacy_company_id = user.company_id
            user.save(update_fields=["_legacy_company_id"])


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0002_user_deleted_at"),
        ("empresas", "0001_initial"),
    ]

    operations = [
        # 1. Rename old UUID field so Django can reuse the company_id column name for the FK
        migrations.RenameField(
            model_name="user",
            old_name="company_id",
            new_name="_legacy_company_id",
        ),

        # 2. Add FK (nullable for the data migration step)
        migrations.AddField(
            model_name="user",
            name="company",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="usuarios",
                to="empresas.empresa",
            ),
        ),

        # 3. Data migration
        migrations.RunPython(_migrate_forward, _migrate_backward),

        # 4. Remove legacy field
        migrations.RemoveField(
            model_name="user",
            name="_legacy_company_id",
        ),
    ]
