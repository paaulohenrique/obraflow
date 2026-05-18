from django.core.validators import MinValueValidator
from django.db import models

from apps.core.models import BaseModel


class Empresa(BaseModel):
    PLANO_BASICO = "basico"
    PLANO_PROFISSIONAL = "profissional"
    PLANO_ENTERPRISE = "enterprise"
    PLANOS = [
        (PLANO_BASICO, "Básico"),
        (PLANO_PROFISSIONAL, "Profissional"),
        (PLANO_ENTERPRISE, "Enterprise"),
    ]

    razao_social = models.CharField("Razão Social", max_length=300)
    nome_fantasia = models.CharField("Nome Fantasia", max_length=300, blank=True)
    cnpj = models.CharField("CNPJ", max_length=14, unique=True)
    telefone = models.CharField(max_length=15, blank=True)
    email = models.EmailField(blank=True)
    plano = models.CharField(max_length=20, choices=PLANOS, default=PLANO_BASICO)
    limite_usuarios = models.PositiveIntegerField(
        "Limite de Usuários",
        default=10,
        validators=[MinValueValidator(1)],
    )

    class Meta(BaseModel.Meta):
        verbose_name = "Empresa"
        verbose_name_plural = "Empresas"
        indexes = [
            models.Index(fields=["cnpj"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        return self.razao_social
