from io import BytesIO

import pytest

from pro_documents import R2DocumentStore


class FakeS3:
    def __init__(self):
        self.objects = {}

    def put_object(self, Bucket, Key, Body, ContentType):
        self.objects[(Bucket, Key)] = (bytes(Body), ContentType)

    def get_object(self, Bucket, Key):
        raw, _ = self.objects[(Bucket, Key)]
        return {'Body': BytesIO(raw)}

    def delete_object(self, Bucket, Key):
        self.objects.pop((Bucket, Key), None)


@pytest.fixture
def store():
    value = R2DocumentStore.__new__(R2DocumentStore)
    value.bucket = 'invoices'
    value.prefix = 'documents'
    value.client = FakeS3()
    return value


def test_r2_store_round_trip_and_delete(store):
    key = store.put(b'<invoice/>', '.xml')

    assert key.endswith('.xml')
    assert store.read(key) == b'<invoice/>'
    assert store.client.objects[('invoices', f'documents/{key}')][1] == 'application/xml'

    store.delete(key)
    assert ('invoices', f'documents/{key}') not in store.client.objects


@pytest.mark.parametrize('key', ['../secret', '/absolute.pdf', 'bad key.pdf', ''])
def test_r2_store_rejects_unsafe_keys(store, key):
    with pytest.raises(ValueError):
        store.object_key(key)
