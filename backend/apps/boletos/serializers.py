from decimal import Decimal

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from apps.core.serializers import BaseModelSerializer
from apps.estoque.models import Fornecedor
from apps.financeiro.models import CategoriaFinanceira

from .models import BoletoOCR, HistoricoBoleto, OCRProcessamento
from .services.extracao import (
    converter_linha_digitavel_para_codigo_barras,
    normalizar_linha_digitavel,
    validar_linha_digitavel,
)


class RejectCompanyPayloadMixin:
    def run_validation(self, data=serializers.empty):
        if isinstance(data, dict) and {"company", "company_id"} & set(data):
            raise ValidationError({
                "company": "Empresa é definida pelo usuário autenticado e não deve ser enviada."
            })
        return super().run_validation(data)


class TenantScopedSerializerMixin(RejectCompanyPayloadMixin):
    tenant_scoped_fields: dict[str, type] = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        company_id = getattr(getattr(request, "user", None), "company_id", None)
        if not company_id:
            return
        for field_name, model in self.tenant_scoped_fields.items():
            if field_name in self.fields:
                self.fields[field_name].queryset = model.objects.filter(
                    company_id=company_id,
                    deleted_at__isnull=True,
                )


class BoletoUploadSerializer(RejectCompanyPayloadMixin, serializers.Serializer):
    arquivo = serializers.FileField()
    observacao = serializers.CharField(required=False, allow_blank=True)
    idempotency_key = serializers.CharField(max_length=140, required=False, allow_blank=True)


class OCRProcessamentoSerializer(BaseModelSerializer):
    class Meta:
        model = OCRProcessamento
        fields = [
            "id",
            "provider",
            "status",
            "tentativa",
            "task_id",
            "started_at",
            "finished_at",
            "duration_ms",
            "erro_codigo",
            "erro_mensagem",
            "confianca_ocr",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class BoletoOCRListSerializer(BaseModelSerializer):
    company_id = serializers.UUIDField(read_only=True)
    fornecedor_nome_final = serializers.SerializerMethodField()
    created_by_nome = serializers.CharField(source="created_by.name", read_only=True)

    class Meta:
        model = BoletoOCR
        fields = [
            "id",
            "company_id",
            "arquivo_nome_original",
            "tipo_arquivo",
            "content_type",
            "tamanho_bytes",
            "status",
            "fornecedor",
            "fornecedor_nome",
            "fornecedor_nome_final",
            "banco_codigo",
            "banco_nome",
            "valor",
            "vencimento",
            "linha_digitavel",
            "codigo_barras",
            "confianca_ocr",
            "conta_pagar",
            "created_by",
            "created_by_nome",
            "erro_codigo",
            "erro_mensagem",
            "tentativas_ocr",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_fornecedor_nome_final(self, obj) -> str:
        return str(obj.fornecedor) if obj.fornecedor else obj.fornecedor_nome


class BoletoOCRDetailSerializer(BoletoOCRListSerializer):
    processado_por_nome = serializers.CharField(source="processado_por.name", read_only=True)
    confirmado_por_nome = serializers.CharField(source="confirmado_por.name", read_only=True)
    rejeitado_por_nome = serializers.CharField(source="rejeitado_por.name", read_only=True)

    class Meta(BoletoOCRListSerializer.Meta):
        fields = BoletoOCRListSerializer.Meta.fields + [
            "arquivo",
            "preview_image",
            "preview_pages",
            "sha256",
            "documento_beneficiario",
            "documento_pagador",
            "data_emissao",
            "texto_ocr",
            "payload_ocr",
            "raw_provider_response",
            "campos_extraidos",
            "campos_confianca",
            "processado_por",
            "processado_por_nome",
            "confirmado_por",
            "confirmado_por_nome",
            "rejeitado_por",
            "rejeitado_por_nome",
            "ocr_started_at",
            "ocr_finished_at",
            "confirmado_at",
            "rejeitado_at",
            "motivo_rejeicao",
            "observacao",
            "idempotency_key",
        ]
        read_only_fields = fields


class BoletoConfirmarSerializer(TenantScopedSerializerMixin, serializers.Serializer):
    tenant_scoped_fields = {"categoria": CategoriaFinanceira, "fornecedor": Fornecedor}

    beneficiario_nome = serializers.CharField(max_length=300, required=False, allow_blank=True)
    beneficiario_documento = serializers.CharField(max_length=20, required=False, allow_blank=True)
    banco_codigo = serializers.CharField(max_length=10, required=False, allow_blank=True)
    banco_nome = serializers.CharField(max_length=120, required=False, allow_blank=True)
    valor = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal("0.01"))
    vencimento = serializers.DateField()
    data_emissao = serializers.DateField(required=False)
    linha_digitavel = serializers.CharField(max_length=80, required=False, allow_blank=True)
    codigo_barras = serializers.CharField(max_length=60, required=False, allow_blank=True)
    categoria = serializers.PrimaryKeyRelatedField(queryset=CategoriaFinanceira.objects.none())
    fornecedor = serializers.PrimaryKeyRelatedField(
        queryset=Fornecedor.objects.none(),
        required=False,
        allow_null=True,
    )
    observacao = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        if attrs["categoria"].tipo != CategoriaFinanceira.TIPO_DESPESA:
            raise ValidationError({"categoria": "Conta a pagar exige categoria de despesa."})
        data_emissao = attrs.get("data_emissao")
        if data_emissao and data_emissao > attrs["vencimento"]:
            raise ValidationError({"data_emissao": "Emissão não pode ser após o vencimento."})
        if linha := attrs.get("linha_digitavel"):
            linha = normalizar_linha_digitavel(linha)
            if not linha or not validar_linha_digitavel(linha):
                raise ValidationError({"linha_digitavel": "Linha digitável inválida."})
            attrs["linha_digitavel"] = linha
            attrs["codigo_barras"] = attrs.get("codigo_barras") or converter_linha_digitavel_para_codigo_barras(linha)
        if codigo := attrs.get("codigo_barras"):
            digits = "".join(char for char in codigo if char.isdigit())
            if len(digits) != 44:
                raise ValidationError({"codigo_barras": "Código de barras deve ter 44 dígitos."})
            attrs["codigo_barras"] = digits
        return attrs


class BoletoRejeitarSerializer(RejectCompanyPayloadMixin, serializers.Serializer):
    motivo = serializers.CharField(max_length=500, allow_blank=False)


class BoletoReprocessarSerializer(RejectCompanyPayloadMixin, serializers.Serializer):
    idempotency_key = serializers.CharField(max_length=140, required=False, allow_blank=True)


class HistoricoBoletoSerializer(BaseModelSerializer):
    created_by_nome = serializers.CharField(source="created_by.name", read_only=True)

    class Meta:
        model = HistoricoBoleto
        fields = [
            "id",
            "evento",
            "descricao",
            "before",
            "after",
            "metadata",
            "request_id",
            "created_by",
            "created_by_nome",
            "created_at",
        ]
        read_only_fields = fields


class DashboardBoletosSerializer(serializers.Serializer):
    boletos_enviados_hoje = serializers.IntegerField()
    boletos_processados_hoje = serializers.IntegerField()
    pendentes_revisao = serializers.IntegerField()
    ocrs_com_erro = serializers.IntegerField()
    contas_pagar_geradas = serializers.IntegerField()
    valor_total_identificado = serializers.DecimalField(max_digits=14, decimal_places=2)
    valor_total_confirmado = serializers.DecimalField(max_digits=14, decimal_places=2)
    taxa_sucesso_ocr = serializers.DecimalField(max_digits=5, decimal_places=2)
    confianca_media = serializers.DecimalField(max_digits=5, decimal_places=2)
    vencimentos_7_dias = serializers.IntegerField()
    vencimentos_30_dias = serializers.IntegerField()
