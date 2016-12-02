import time
import hmac
import base64
import hashlib
import string
import random

import six
import requests
from requests.adapters import HTTPAdapter

__all__ = ['Client']


SIGNATURE_LEN = 32
API_URL = 'https://api.productai.cn'
API_VERSION = '1'


class Client(object):

    def __init__(self, access_key_id, access_key_secret, session=None):
        self.access_key_id = access_key_id
        self.access_key_secret = access_key_secret
        if not session:
            session = get_default_session()
        self.session = session

    def get_api(self, type_, id_):
        return API(self, type_, id_)

    def get_image_search_api(self, id_):
        return API(self, 'search', id_)

    def get_image_set_api(self, image_set_id):
        return ImageSetAPI(self, image_set_id)

    def post(self, api_url, data=None, files=None):
        headers = self.get_auth_headers(data)
        resp = self.session.post(
            api_url,
            data=data,
            headers=headers,
            files=files,
            timeout=30,
        )
        return resp

    def get_auth_headers(self, data):
        headers = make_auth_headers(self.access_key_id, 'POST')
        headers['x-ca-signature'] = calc_signature(
            headers,
            data,
            self.access_key_secret
        )
        return headers


class API(object):

    def __init__(self, client, type_, id_):
        self.client = client
        self.type_ = type_
        self.id_ = id_

    def query(self, image, loc='0-0-1-1'):
        # TODO add support for uploading image file
        data = {
            'url': image,
            'loc': loc
        }
        return self.client.post(self.base_url, data=data)

    @property
    def base_url(self):
        return '/'.join([API_URL, self.type_, self.id_])


class ImageSetAPI(API):

    def __init__(self, client, image_set_id):
        super(ImageSetAPI, self).__init__(
            client, 'image_sets', '_0000014'
        )
        self.image_set_id = image_set_id

    def query(self, image, loc='0-0-1-1'):
        raise NotImplementedError()

    @property
    def base_url(self):
        return '%s/%s' % (
            super(ImageSetAPI, self).base_url,
            self.image_set_id
        )

    def add_image(self, image_url, meta=None):
        form = {'image_url': image_url, 'meta': meta}
        return self.client.post(self.base_url, data=form)

    def delete_images(self, f_urls_to_delete):
        urls_to_delete = {'urls_to_delete': f_urls_to_delete}
        return self.client.post(self.base_url, files=urls_to_delete)


def short_uuid(length):
    charset = string.ascii_lowercase + string.digits
    return ''.join([random.choice(charset) for i in range(length)])


def make_auth_headers(access_key_id, method='POST'):
    timestamp = int(time.time())
    headers = {
        'x-ca-accesskeyid': access_key_id,
        'x-ca-version': API_VERSION,
        'x-ca-timestamp': str(timestamp),
        'x-ca-signaturenonce': short_uuid(SIGNATURE_LEN),
        'requestmethod': method,
    }
    return headers


def calc_signature(headers, form, secret_key):
    secret_key = to_bytes(secret_key)
    payload = get_payload_as_str(headers, form)
    signature = hmac.new(
        secret_key,
        payload,
        hashlib.sha1
    )
    return base64.b64encode(signature.digest())


def get_payload_as_str(headers, form):
    payload = dict(headers)

    if form:
        payload.update(form)

    sort_value = []
    for k in sorted(payload):
        v = to_bytes(payload.get(k, ''))
        v = v.strip()
        sort_value.append(b'%s=%s' % (to_bytes(k), v))

    return b'&'.join(sort_value)


def to_bytes(v):
    if not isinstance(v, six.binary_type):
        if six.PY2:
            v = unicode(v)
        v = v.encode('utf8')
    return v


def get_default_session():
    s = requests.Session()
    # remount http and https adapters to config max_retries
    adapter = HTTPAdapter(
        max_retries=3,
        pool_connections=5,
        pool_maxsize=50,
        pool_block=True,
    )
    s.mount('http://', adapter)
    s.mount('https://', adapter)
    return s
