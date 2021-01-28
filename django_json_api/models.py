from collections import defaultdict
from typing import Any, List, Dict, Optional, Type, Union

from django.core.cache import cache

from django_json_api.base import JSONAPIModelBase


# pylint: disable=no-member


def _find_model_class(resource_type: str) -> Type:
    for cls in JSONAPIModel.__subclasses__():
        if resource_type == cls._meta.resource_type:
            return cls
    return None


class JSONAPIModel(metaclass=JSONAPIModelBase):
    def __init__(self, **kwargs):
        self.pk = kwargs.pop('pk', None) or kwargs.pop('id', None)
        if self.pk is not None:
            self.pk = int(self.pk)
        for key, value in kwargs.items():
            if key not in self._meta.fields:
                raise TypeError(
                    f'{self.__class__.__name__} got an unexpected keyword argument "{key}"')
            setattr(self, key, value)
        super().__init__()

    def __eq__(self, other: Any) -> bool:
        if self.__class__ != other.__class__:
            return False
        my_pk = self.pk
        if my_pk is None:
            return self is other
        return int(my_pk) == int(other.pk)

    @property
    def id(self) -> int:  # pylint: disable=invalid-name
        return self.pk

    @staticmethod
    def from_resource(resource_dict: dict, persist: Optional[bool] = True) -> 'JSONAPIModel':
        cls = _find_model_class(resource_dict['type'])
        if cls:
            kwargs = {}
            data = {
                **resource_dict.get('attributes', {}),
                **{
                    name: value['data']
                    for name, value in resource_dict.get('relationships', {}).items()
                    if 'data' in value
                },
            }
            existing_cache = cls.from_cache(resource_dict['id'])
            for name, field in cls._meta.fields.items():
                try:
                    kwargs[name] = field.clean(data[name])
                except KeyError:
                    if existing_cache and hasattr(existing_cache, f'{name}_identifiers'):
                        kwargs[name] = getattr(existing_cache, f'{name}_identifiers')
                    elif existing_cache and hasattr(existing_cache, f'{name}_identifier'):
                        kwargs[name] = getattr(existing_cache, f'{name}_identifier')
            record = cls(id=resource_dict['id'], **kwargs)
            if persist:
                record.cache()
            return record
        return None

    @staticmethod
    def from_resources(resource_dicts: List[Dict]) -> List['JSONAPIModel']:
        grouped_records = defaultdict(list)
        for record in resource_dicts:
            grouped_records[record['type']].append(record)

        records = []
        for resource_type, resources in grouped_records.items():
            cls = _find_model_class(resource_type)
            if cls:
                records.extend(
                    cls.cache_many([
                        cls.from_resource(item, persist=False)
                        for item in resources
                    ])
                )
        return records

    @classmethod
    def cache_key(cls, pk: Union[str, int]) -> str:
        resource_type = cls._meta.resource_type
        return f'jsonapi:{resource_type}:{pk}'

    @classmethod
    def from_cache(cls, pk: Union[str, int]) -> 'JSONAPIModel':
        return cache.get(cls.cache_key(pk))

    @classmethod
    def get_many(cls, record_ids: List[Union[str, int]]) -> Dict:
        cache_keys = [cls.cache_key(pk) for pk in record_ids]
        records = {
            record.id: record
            for record in cache.get_many(cache_keys).values()
        }
        missing = set(map(int, filter(bool, record_ids))) - set(records)
        if missing:
            many_id_lookup = getattr(cls._meta, 'many_id_lookup', None)
            if many_id_lookup:
                for item in cls.objects.filter(**{many_id_lookup: ','.join(map(str, missing))}):
                    records[item.id] = item
            else:
                for missing_id in missing:
                    records[missing_id] = cls.objects.get(pk=missing_id)
        return records

    def cache(self) -> 'JSONAPIModel':
        cache_expiration = getattr(self._meta, 'cache_expiration', 24 * 60 * 60)
        cache.set(
            self.cache_key(self.pk),
            self,
            timeout=cache_expiration,
        )
        return self

    @classmethod
    def cache_many(cls, instances: List['JSONAPIModel']) -> List['JSONAPIModel']:
        cache_expiration = getattr(cls._meta, 'cache_expiration', 24 * 60 * 60)
        cache.set_many({
            instance.cache_key(instance.pk): instance
            for instance in instances
        }, cache_expiration)
        return instances

    def refresh_from_api(self) -> None:
        fresh = self.objects.get(pk=self.pk, ignore_cache=True)
        self.__dict__ = fresh.__dict__
        self.cache()