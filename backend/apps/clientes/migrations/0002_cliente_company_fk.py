"""Replace the loose company_id UUIDField on Cliente with a FK to Empresa.

Migration steps:
1. Rename old company_id UUID column to _legacy_company_id
2. Add company ForeignKey (nullable)
3. Data-migrate: link each client to the Empresa that was already created
   during the accounts migration (same UUID re-used as Empresa pk)
4. Remove _legacy_company_id
"""
import uuid as uuid_module
from django.db import migrations, models
import django.db.models.deletion

_DEFAULT_EMPRESA_ID = uuid_module.UUID("00000000-0000-0000-0000-000000000001")


def _migrate_forward(apps, schema_editor):
    Cliente = apps.get_model("clientes", "Cliente")
    Empresa = apps.get_model("empresas", "Empresa")

    # Collect legacy UUIDs not yet covered by Empresa
    legacy_ids = set(
        Cliente.objects.exclude(_legacy_company_id__isnull=True)
        .values_list("_legacy_company_id", flat=True)
        .distinct()
    )

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

    # Clients without legacy company_id go to the default placeholder
    clients_without = Cliente.objects.filter(_legacy_company_id__isnull=True)
    if clients_without.exists():
        default_empresa, _ = Empresa.objects.get_or_create(
            id=_DEFAULT_EMPRESA_ID,
            defaults={
                "razao_social": "Empresa Padrão",
                "cnpj": "00000000000191",
                "is_active": True,
                "plano": "basico",
                "limite_usuarios": 50,
            },
        )
        clients_without.update(company=default_empresa)

    for cliente in Cliente.objects.filter(_legacy_company_id__isnull=False):
        empresa = Empresa.objects.get(id=cliente._legacy_company_id)
        cliente.company = empresa
        cliente.save(update_fields=["company"])


def _migrate_backward(apps, schema_editor):
    Cliente = apps.get_model("clientes", "Cliente")
    for cliente in Cliente.objects.all():
        if cliente.company_id:
            cliente._legacy_company_id = cliente.company_id
            cliente.save(update_fields=["_legacy_company_id"])


class Migration(migrations.Migration):

    dependencies = [
        ("clientes", "0001_initial"),
        ("empresas", "0001_initial"),
        ("accounts", "0003_user_company_fk"),
    ]

    operations = [
        # 1. Rename the old UUID field
        migrations.RenameField(
            model_name="cliente",
            old_name="company_id",
            new_name="_legacy_company_id",
        ),

        # 2. Add FK (nullable for data migration)
        migrations.AddField(
            model_name="cliente",
            name="company",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="clientes",
                to="empresas.empresa",
            ),
        ),

        # 3. Data migration
        migrations.RunPython(_migrate_forward, _migrate_backward),

        # 4. Remove legacy field
        migrations.RemoveField(
            model_name="cliente",
            name="_legacy_company_id",
        ),

        # 5. Update the unique constraint to use the FK column (company_id = FK column)
        migrations.RemoveConstraint(
            model_name="cliente",
            name="unique_cpf_cnpj_per_company_active",
        ),
        migrations.AddConstraint(
            model_name="cliente",
            constraint=models.UniqueConstraint(
                fields=["company_id", "cpf_cnpj"],
                condition=models.Q(deleted_at__isnull=True),
                name="unique_cpf_cnpj_per_company_active",
            ),
        ),

        # 6. Update indexes
        migrations.RemoveIndex(model_name="cliente", name="clientes_cl_company_b7e5dc_idx"),
        migrations.RemoveIndex(model_name="cliente", name="clientes_cl_company_ce8612_idx"),
        migrations.RemoveIndex(model_name="cliente", name="clientes_cl_company_dedcb1_idx"),
        migrations.AddIndex(
            model_name="cliente",
            index=models.Index(fields=["company_id", "bloqueado"], name="clientes_cl_company_bloq_idx"),
        ),
        migrations.AddIndex(
            model_name="cliente",
            index=models.Index(fields=["company_id", "saldo_devedor"], name="clientes_cl_company_saldo_idx"),
        ),
        migrations.AddIndex(
            model_name="cliente",
            index=models.Index(fields=["company_id", "nome"], name="clientes_cl_company_nome_idx"),
        ),
    ]
