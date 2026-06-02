from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import models

from apps.core.models import BaseModel
from apps.empresas.validators import clean_cnpj, is_valid_cnpj

from .validators import validate_cep, validate_cnae, validate_municipio_ibge


class ConfiguracaoFiscalEmpresa(BaseModel):
    REGIME_SIMPLES = "SIMPLES_NACIONAL"
    REGIME_LUCRO_PRESUMIDO = "LUCRO_PRESUMIDO"
    REGIME_LUCRO_REAL = "LUCRO_REAL"
    REGIME_CHOICES = [
        (REGIME_SIMPLES, "Simples Nacional"),
        (REGIME_LUCRO_PRESUMIDO, "Lucro Presumido"),
        (REGIME_LUCRO_REAL, "Lucro Real"),
    ]

    CRT_SIMPLES = "1"
    CRT_SIMPLES_EXCESSO = "2"
    CRT_NORMAL = "3"
    CRT_CHOICES = [
        (CRT_SIMPLES, "Simples Nacional"),
        (CRT_SIMPLES_EXCESSO, "Simples Nacional - excesso sublimite"),
        (CRT_NORMAL, "Regime Normal"),
    ]

    AMBIENTE_HOMOLOGACAO = "HOMOLOGACAO"
    AMBIENTE_PRODUCAO = "PRODUCAO"
    AMBIENTE_CHOICES = [
        (AMBIENTE_HOMOLOGACAO, "Homologação"),
        (AMBIENTE_PRODUCAO, "Produção"),
    ]

    PROVIDER_FAKE = "FAKE"
    PROVIDER_NFEIO = "NFEIO"
    PROVIDER_FOCUS = "FOCUS_NFE"
    PROVIDER_PLUGNOTAS = "PLUGNOTAS"
    PROVIDER_CHOICES = [
        (PROVIDER_FAKE, "Fake"),
        (PROVIDER_NFEIO, "NFE.io"),
        (PROVIDER_FOCUS, "Focus NFe"),
        (PROVIDER_PLUGNOTAS, "PlugNotas"),
    ]

    company = models.OneToOneField(
        "empresas.Empresa",
        on_delete=models.PROTECT,
        related_name="configuracao_fiscal",
    )
    cnpj = models.CharField(max_length=14, blank=True)
    razao_social = models.CharField(max_length=300, blank=True)
    nome_fantasia = models.CharField(max_length=300, blank=True)
    inscricao_estadual = models.CharField(max_length=30, blank=True)
    inscricao_municipal = models.CharField(max_length=30, blank=True)
    regime_tributario = models.CharField(max_length=30, choices=REGIME_CHOICES, blank=True)
    crt = models.CharField(max_length=1, choices=CRT_CHOICES, blank=True)
    cnae = models.CharField(max_length=7, blank=True)
    uf = models.CharField(max_length=2, blank=True)
    municipio = models.CharField(max_length=200, blank=True)
    municipio_ibge = models.CharField(max_length=7, blank=True)
    logradouro = models.CharField(max_length=300, blank=True)
    numero = models.CharField(max_length=20, blank=True)
    complemento = models.CharField(max_length=200, blank=True)
    bairro = models.CharField(max_length=200, blank=True)
    cep = models.CharField(max_length=8, blank=True)
    ambiente_fiscal = models.CharField(
        max_length=20,
        choices=AMBIENTE_CHOICES,
        default=AMBIENTE_HOMOLOGACAO,
    )
    provider_fiscal = models.CharField(
        max_length=20,
        choices=PROVIDER_CHOICES,
        default=PROVIDER_FAKE,
    )
    provider_company_id = models.CharField(max_length=120, blank=True)
    ativo = models.BooleanField(default=False)

    class Meta(BaseModel.Meta):
        verbose_name = "Configuração Fiscal da Empresa"
        verbose_name_plural = "Configurações Fiscais das Empresas"
        indexes = [
            models.Index(fields=["company", "ativo"]),
            models.Index(fields=["company", "ambiente_fiscal"]),
            models.Index(fields=["company", "provider_fiscal"]),
        ]

    @property
    def cadastro_fiscal_pronto(self) -> bool:
        required = [
            self.cnpj,
            self.razao_social,
            self.inscricao_estadual,
            self.regime_tributario,
            self.crt,
            self.cnae,
            self.uf,
            self.municipio,
            self.municipio_ibge,
            self.logradouro,
            self.numero,
            self.bairro,
            self.cep,
            self.ambiente_fiscal,
            self.provider_fiscal,
        ]
        return all(bool(str(value).strip()) for value in required)

    def clean(self):
        super().clean()
        self.cnpj = clean_cnpj(self.cnpj or "")
        if self.cnpj and not is_valid_cnpj(self.cnpj):
            raise DjangoValidationError({"cnpj": "CNPJ inválido."})
        self.razao_social = (self.razao_social or "").strip()
        self.nome_fantasia = (self.nome_fantasia or "").strip()
        self.inscricao_estadual = (self.inscricao_estadual or "").strip()
        self.inscricao_municipal = (self.inscricao_municipal or "").strip()
        self.cnae = validate_cnae(self.cnae)
        self.uf = (self.uf or "").strip().upper()
        self.municipio = (self.municipio or "").strip()
        self.municipio_ibge = validate_municipio_ibge(self.municipio_ibge)
        self.logradouro = (self.logradouro or "").strip()
        self.numero = (self.numero or "").strip()
        self.complemento = (self.complemento or "").strip()
        self.bairro = (self.bairro or "").strip()
        self.cep = validate_cep(self.cep)
        self.provider_company_id = (self.provider_company_id or "").strip()

        if self.uf and len(self.uf) != 2:
            raise DjangoValidationError({"uf": "UF deve conter 2 caracteres."})
        if self.ativo and not self.cadastro_fiscal_pronto:
            raise DjangoValidationError({
                "ativo": "Configuração fiscal só pode ser ativada com cadastro fiscal pronto para NF-e."
            })

# TODO fiscal seguro:
# certificado A1, senha e token de provider devem ser armazenados apenas com
# criptografia/secret manager e nunca retornados por serializers.
