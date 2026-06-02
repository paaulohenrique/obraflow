from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

from apps.core.models import BaseModel
from apps.fiscal.validators import (
    validate_cep,
    validate_ie_required,
    validate_municipio_ibge,
)

ESTADOS_BRASIL = [
    ("AC", "Acre"), ("AL", "Alagoas"), ("AP", "Amapá"), ("AM", "Amazonas"),
    ("BA", "Bahia"), ("CE", "Ceará"), ("DF", "Distrito Federal"),
    ("ES", "Espírito Santo"), ("GO", "Goiás"), ("MA", "Maranhão"),
    ("MT", "Mato Grosso"), ("MS", "Mato Grosso do Sul"), ("MG", "Minas Gerais"),
    ("PA", "Pará"), ("PB", "Paraíba"), ("PR", "Paraná"), ("PE", "Pernambuco"),
    ("PI", "Piauí"), ("RJ", "Rio de Janeiro"), ("RN", "Rio Grande do Norte"),
    ("RS", "Rio Grande do Sul"), ("RO", "Rondônia"), ("RR", "Roraima"),
    ("SC", "Santa Catarina"), ("SP", "São Paulo"), ("SE", "Sergipe"),
    ("TO", "Tocantins"),
]


class Cliente(BaseModel):
    TIPO_PF = "PF"
    TIPO_PJ = "PJ"
    TIPO_CHOICES = [
        (TIPO_PF, "Pessoa Física"),
        (TIPO_PJ, "Pessoa Jurídica"),
    ]
    INDICADOR_IE_CONTRIBUINTE = "CONTRIBUINTE"
    INDICADOR_IE_ISENTO = "ISENTO"
    INDICADOR_IE_NAO_CONTRIBUINTE = "NAO_CONTRIBUINTE"
    INDICADOR_IE_CHOICES = [
        (INDICADOR_IE_CONTRIBUINTE, "Contribuinte ICMS"),
        (INDICADOR_IE_ISENTO, "Isento"),
        (INDICADOR_IE_NAO_CONTRIBUINTE, "Não contribuinte"),
    ]

    # Multi-tenant: client belongs to exactly one Empresa.
    # company_id Django attribute gives the Empresa UUID directly.
    company = models.ForeignKey(
        "empresas.Empresa",
        on_delete=models.PROTECT,
        related_name="clientes",
        null=True,   # nullable during migration; enforced NOT NULL after data migration
        blank=True,
    )

    # Identificação
    nome = models.CharField("Nome / Razão Social", max_length=300)
    tipo_pessoa = models.CharField(max_length=2, choices=TIPO_CHOICES, default=TIPO_PF)
    cpf_cnpj = models.CharField("CPF / CNPJ", max_length=14)

    # Contato
    telefone = models.CharField(max_length=15, blank=True)
    whatsapp = models.CharField(max_length=15, blank=True)
    email = models.EmailField(blank=True)

    # Endereço
    cep = models.CharField(max_length=9, blank=True)
    rua = models.CharField("Logradouro", max_length=300, blank=True)
    numero = models.CharField("Número", max_length=10, blank=True)
    bairro = models.CharField(max_length=200, blank=True)
    cidade = models.CharField(max_length=200, blank=True)
    estado = models.CharField(max_length=2, choices=ESTADOS_BRASIL, blank=True)
    complemento = models.CharField(max_length=200, blank=True)

    # Fiscal NF-e
    inscricao_estadual = models.CharField(max_length=30, blank=True)
    indicador_ie = models.CharField(
        max_length=20,
        choices=INDICADOR_IE_CHOICES,
        default=INDICADOR_IE_NAO_CONTRIBUINTE,
    )
    contribuinte_icms = models.BooleanField(default=False)
    municipio_ibge = models.CharField(max_length=7, blank=True)
    codigo_pais = models.CharField(max_length=4, default="1058", blank=True)
    pais = models.CharField(max_length=80, default="BRASIL", blank=True)

    # Financeiro e controle
    observacao = models.TextField("Observação", blank=True)
    limite_credito = models.DecimalField(
        "Limite de Crédito",
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    saldo_devedor = models.DecimalField(
        "Saldo Devedor",
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    bloqueado = models.BooleanField(default=False)
    data_ultimo_pagamento = models.DateField(null=True, blank=True)

    class Meta(BaseModel.Meta):
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"
        constraints = [
            models.UniqueConstraint(
                fields=["company_id", "cpf_cnpj"],
                condition=models.Q(deleted_at__isnull=True),
                name="unique_cpf_cnpj_per_company_active",
            )
        ]
        indexes = [
            models.Index(fields=["company_id", "bloqueado"]),
            models.Index(fields=["company_id", "saldo_devedor"]),
            models.Index(fields=["company_id", "nome"]),
            models.Index(fields=["cpf_cnpj"]),
        ]

    def __str__(self):
        return f"{self.nome} ({self.cpf_cnpj})"

    def clean(self):
        super().clean()
        self.inscricao_estadual = (self.inscricao_estadual or "").strip()
        self.municipio_ibge = validate_municipio_ibge(self.municipio_ibge)
        self.cep = validate_cep(self.cep)
        self.codigo_pais = (self.codigo_pais or "1058").strip()
        self.pais = (self.pais or "BRASIL").strip().upper()

        if (
            self.tipo_pessoa == self.TIPO_PF
            and self.indicador_ie == self.INDICADOR_IE_CONTRIBUINTE
        ):
            raise ValidationError({"indicador_ie": "Pessoa física deve ser não contribuinte para NF-e."})

        validate_ie_required(
            indicador_ie=self.indicador_ie,
            inscricao_estadual=self.inscricao_estadual,
        )
        self.contribuinte_icms = self.indicador_ie == self.INDICADOR_IE_CONTRIBUINTE

    @property
    def cadastro_fiscal_pronto(self) -> bool:
        endereco_ok = all([
            self.cep,
            self.rua,
            self.numero,
            self.bairro,
            self.cidade,
            self.estado,
            self.municipio_ibge,
            self.codigo_pais,
            self.pais,
        ])
        ie_ok = (
            self.indicador_ie != self.INDICADOR_IE_CONTRIBUINTE
            or bool(self.inscricao_estadual)
        )
        return bool(self.cpf_cnpj and endereco_ok and ie_ok)

    @property
    def credito_disponivel(self) -> Decimal:
        return max(Decimal("0.00"), self.limite_credito - self.saldo_devedor)

    @property
    def inadimplente(self) -> bool:
        return self.saldo_devedor > Decimal("0.00")
