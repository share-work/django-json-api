from rest_framework.exceptions import ValidationError
from rest_framework.status import HTTP_404_NOT_FOUND
from rest_framework_json_api import serializers
from rest_framework_json_api.relations import ResourceRelatedField
from rest_framework_json_api.utils import get_included_resources, get_resource_type_from_serializer

from django_json_api import django, fields
from django_json_api.client import JSONAPIClientError

MAPPING = {
    fields.DateTimeAttribute: serializers.DateTimeField,
}


class SparseFieldsetsMixin(serializers.SparseFieldsetsMixin):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        context = kwargs.get("context")
        request = context.get("request") if context else None
        data = kwargs.get("data", {})
        _fields = list(data.keys())
        if request:
            resource_type = get_resource_type_from_serializer(self)
            requested_fields = request.query_params.get(f"fields[{resource_type}]")
            if requested_fields:
                _fields.extend(requested_fields.split(","))
            _fields.extend(get_included_resources(request))
        # To manually include certain fields without having to make a http request:
        include_fields = context.get("include_fields") if context else None
        if include_fields:
            _fields.extend(include_fields)
        for fieldname in getattr(self.Meta, "exclude_by_default", []):
            if fieldname not in _fields:
                self.fields.pop(fieldname, None)


def get_default_relation_serializer(json_api_model, only_fields=None):
    class _Metaclass(serializers.SerializerMetaclass):
        def __new__(cls, name, bases, attrs):
            new_class = super().__new__(cls, name, bases, attrs)
            new_class._declared_fields["id"] = serializers.IntegerField(read_only=True)
            for fieldname, field in json_api_model._meta.fields.items():
                if (
                    isinstance(field, fields.Attribute)
                    and not isinstance(field, fields.Relationship)
                    and (only_fields is None or fieldname in only_fields)
                ):
                    new_class._declared_fields[fieldname] = MAPPING.get(
                        field.__class__,
                        serializers.ReadOnlyField,
                    )(read_only=True)
            return new_class

    class _Serializer(serializers.Serializer, metaclass=_Metaclass):
        class JSONAPIMeta:
            resource_name = json_api_model._meta.resource_type
            model = json_api_model

        def create(self, validated_data):
            raise NotImplementedError()

        def update(self, instance, validated_data):
            raise NotImplementedError()

    return _Serializer


class ModelSerializerMetaclass(serializers.SerializerMetaclass):
    def __new__(cls, name, bases, attrs):
        if "Meta" in attrs:
            meta = attrs["Meta"]
            incl_serializers = attrs.get("included_serializers", {})
            for field in meta.model._meta.fields:
                if isinstance(field, django.RelatedJSONAPIField) and field.name in meta.fields:
                    incl_serializers[field.name] = incl_serializers.get(
                        field.name, get_default_relation_serializer(field.json_api_model)
                    )
            attrs["included_serializers"] = incl_serializers
        return super().__new__(cls, name, bases, attrs)


class ModelSerializer(
    SparseFieldsetsMixin, serializers.ModelSerializer, metaclass=ModelSerializerMetaclass
):
    def build_field(self, field_name, info, model_class, nested_depth):
        model_field = getattr(model_class, field_name)
        if isinstance(model_field, django.RelatedJSONAPIDescriptor):
            return (
                ResourceRelatedField,
                {
                    "read_only": True,
                    "required": False,
                    "model": model_field.field.json_api_model,
                },
            )
        return super().build_field(field_name, info, model_class, nested_depth)

    def is_valid(self, raise_exception=False):
        try:
            return super().is_valid(raise_exception)
        except JSONAPIClientError as exception:
            if exception.response.status_code == HTTP_404_NOT_FOUND:
                raise ValidationError("Failed to fetch RelatedJSONAPIField")
            raise exception
