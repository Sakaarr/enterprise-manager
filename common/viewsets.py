# common/viewsets.py
from rest_framework import viewsets, status
from common.response import success_response, error_response

class StandardizedModelViewSet(viewsets.ModelViewSet):
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            paginated_response = self.get_paginated_response(serializer.data)
            return success_response(
                status_code=200,
                message="Success",
                description="Paginated list fetched successfully.",
                data=paginated_response.data
            )

        serializer = self.get_serializer(queryset, many=True)
        return success_response(
            status_code=200,
            message="Success",
            description="List fetched successfully.",
            data=serializer.data
        )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return success_response(
            status_code=200,
            message="Success",
            description="Resource fetched successfully.",
            data=serializer.data
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return success_response(
            status_code=status.HTTP_201_CREATED,
            message="Created",
            description="Resource created successfully.",
            data=serializer.data
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return success_response(
            status_code=200,
            message="Updated",
            description="Resource updated successfully.",
            data=serializer.data
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return success_response(
            status_code=204,
            message="Deleted",
            description="Resource deleted successfully.",
            data=None
        )
