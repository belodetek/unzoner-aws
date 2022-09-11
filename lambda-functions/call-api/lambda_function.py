#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import boto3
import requests
from base64 import b64decode

urls = os.getenv('URLS').split()
auth_token = os.getenv('AUTH_TOKEN')


def decrypt_secret(encrypted=None):
    try:
        return boto3.client('kms').decrypt(
            CiphertextBlob=b64decode(encrypted)
        )['Plaintext']
    except Exception as e:
        return encrypted


def lambda_handler(event=None, context=None, args=None):
    print('lambda: event={} context={}'.format(event, context))
    for url in urls:
        request = requests.get(
            url,
            headers={'X-Auth-Token': decrypt_secret(encrypted=auth_token)}
        )
        print('url={} status_code={} content={}'.format(
            url,
            request.status_code,
            request.content
        ))
    return True


if __name__ == '__main__':
    lambda_handler()
