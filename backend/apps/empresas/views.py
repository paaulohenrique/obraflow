from rest_framework import status, viewsets
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, extend_schema_view

from .permissions import EmpresaPermission
from .selectors import get_empresa_by_id, get_all_empresas
from .serializers import (
    EmpresaCreateSerializer,
    EmpresaDetailSerializer,
    EmpresaListSerializer,
    EmpresaUpdateSerializer,
)
from .services import create_empresa, update_empresa, soft_delete_empresa
from apps.core.pagination import StandardResultsSetPagination


@extend_schema_view(
    list=extend_schema(summary="Listar empresas", tags=["Empresas"]),
    create=extend_schema(summary="Criar empresa", tags=["Empresas"]),
    retrieve=extend_schema(summary="Detalhar empresa", tags=["Empresas"]),
    partial_update=extend_schema(summary="Atualizar empresa", tags=["Empresas"]),
    destroy=extend_schema(summary="Remover empresa (soft delete)", tags=["Empresas"]),
)
class EmpresaViewSet(viewsets.ViewSet):
    permission_classes = [EmpresaPermission]

    def list(self, request):
        qs = get_all_empresas()
        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(qs, request, view=self)
        return paginator.get_paginated_response(EmpresaListSerializer(page, many=True).data)

    def create(self, request):
        serializer = EmpresaCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        empresa = create_empresa(user=request.user, data=serializer.validated_data, request=request)
        return Response(EmpresaDetailSerializer(empresa).data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, pk=None):
        empresa = get_empresa_by_id(empresa_id=pk)
        self.check_object_permissions(request, empresa)
        return Response(EmpresaDetailSerializer(empresa).data)

    def partial_update(self, request, pk=None):
        empresa = get_empresa_by_id(empresa_id=pk)
        self.check_object_permissions(request, empresa)
        serializer = EmpresaUpdateSerializer(empresa, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        empresa = update_empresa(user=request.user, empresa=empresa, data=serializer.validated_data, request=request)
        return Response(EmpresaDetailSerializer(empresa).data)

    def destroy(self, request, pk=None):
        empresa = get_empresa_by_id(empresa_id=pk)
        self.check_object_permissions(request, empresa)
        soft_delete_empresa(user=request.user, empresa=empresa, request=request)
        return Response(status=status.HTTP_204_NO_CONTENT)
