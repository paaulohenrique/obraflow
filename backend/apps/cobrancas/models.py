from django.db import models

from apps.core.models import BaseModel


class ConfiguracaoCobranca(BaseModel):
    company = models.OneToOneField(
        "empresas.Empresa",
        on_delete=models.PROTECT,
        related_name="configuracao_cobranca",
    )
    ativo = models.BooleanField(default=True)
    enviar_1_dia_antes = models.BooleanField(default=False)
    enviar_no_vencimento = models.BooleanField(default=True)
    enviar_7_dias_apos = models.BooleanField(default=True)
    enviar_15_dias_apos = models.BooleanField(default=True)
    enviar_30_dias_apos = models.BooleanField(default=False)
    updated_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        related_name="configuracoes_cobranca_atualizadas",
        null=True,
        blank=True,
    )

    class Meta(BaseModel.Meta):
        verbose_name = "Configuração de Cobrança"
        verbose_name_plural = "Configurações de Cobrança"
        indexes = [
            models.Index(fields=["company", "ativo"]),
        ]

    def __str__(self):
        return f"Configuração de cobrança - {self.company_id}"
