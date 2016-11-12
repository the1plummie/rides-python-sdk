# Copyright (c) 2016 Uber Technologies, Inc.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

"""Initializes an UberRidesClient with OAuth 2.0 Credentials.

This example demonstrates how to get an access token through the
OAuth 2.0 Authorization Code Grant and use credentials to create
an UberRidesClient.

To run this example:

    (1) Set your app credentials in config.yaml
    (2) Run `python authorization_code_grant.py`
    (3) A success message will print, 'Hello {YOUR_NAME}'
    (4) User OAuth 2.0 credentials are recorded in
        'oauth2_session_store.yaml'
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from builtins import input

from yaml import safe_dump, safe_load

from example import utils
from example.utils import fail_print
from example.utils import response_print
from example.utils import success_print
from example.utils import import_app_credentials

from uber_rides.auth import AuthorizationCodeGrant
from uber_rides.client import UberRidesClient
from uber_rides.errors import ClientError
from uber_rides.errors import ServerError
from uber_rides.errors import UberIllegalState

from uber_rides.session import Session, OAuth2Credential
import time, pprint, os.path, sys

pp = pprint.PrettyPrinter(indent=2)


def authorization_code_grant_flow(credentials, storage_filename):
    """Get an access token through Authorization Code Grant.

    Parameters
        credentials (dict)
            All your app credentials and information
            imported from the configuration file.
        storage_filename (str)
            Filename to store OAuth 2.0 Credentials.

    Returns
        (UberRidesClient)
            An UberRidesClient with OAuth 2.0 Credentials.
    """
    auth_flow = AuthorizationCodeGrant(
        credentials.get('client_id'),
        credentials.get('scopes'),
        credentials.get('client_secret'),
        credentials.get('redirect_url'),
    )

    auth_url = auth_flow.get_authorization_url()
    login_message = 'Login and grant access by going to:\n{}\n'
    login_message = login_message.format(auth_url)
    response_print(login_message)

    redirect_url = 'Copy the URL you are redirected to and paste here: \n'
    result = input(redirect_url).strip()

    try:
        session = auth_flow.get_session(result)

    except (ClientError, UberIllegalState) as error:
        fail_print(error)
        return

    credential = session.oauth2credential

    credential_data = {
        'client_id': credential.client_id,
        'redirect_url': credential.redirect_url,
        'access_token': credential.access_token,
        'expires_in_seconds': credential.expires_in_seconds,
        'scopes': list(credential.scopes),
        'grant_type': credential.grant_type,
        'client_secret': credential.client_secret,
        'refresh_token': credential.refresh_token,
    }

    with open(storage_filename, 'w') as yaml_file:
        yaml_file.write(safe_dump(credential_data, default_flow_style=False))

    return UberRidesClient(session, sandbox_mode=True)


places = {
    'home': { 'lat': 34.051876, 'long': -118.461077 },
    'work': { 'lat': 33.992140, 'long': -118.473471 },
}

def get_estimate(name_orig='home', name_dest='work', detail=False):
    if name_orig not in places or name_dest not in places:
        sys.exit('one or both unknown place names')

    orig = places[name_orig]
    dest = places[name_dest]
    storage = None

    if os.path.exists(utils.STORAGE_FILENAME):
        with open(utils.STORAGE_FILENAME, 'r') as storage_file:
            storage = safe_load(storage_file)

    api_client = None

    if storage and 'expires_in_seconds' in storage and int(time.time()) < storage['expires_in_seconds']:
        api_client = UberRidesClient(Session(oauth2credential=OAuth2Credential(**storage)), sandbox_mode=True)
    else:
        credentials = import_app_credentials()
        api_client = authorization_code_grant_flow(
            credentials,
            utils.STORAGE_FILENAME,
        )

    products1, response1 = _get_estimate_response(api_client, orig, dest)
    products2, response2 = _get_estimate_response(api_client, dest, orig)


    print('{time}: {place1}->{place2}: {price1}, {place2}->{place1}: {price2}'.format(
        time=time.strftime("%x %X"),
        place1=name_orig,
        place2=name_dest,
        price1=response1.json.get('fare').get('display'),
        price2=response2.json.get('fare').get('display')
    ))

    if detail:
        _print_detail(products1, response1)
        _print_detail(products2, response2)


def _get_estimate_response(api_client, orig, dest):
    resp = api_client.get_products(*orig.values())
    products = resp.json.get('products')
    response = api_client.estimate_ride(
        product_id=products[0].get('product_id'),
        start_latitude=orig['lat'],
        start_longitude=orig['long'],
        end_latitude=dest['lat'],
        end_longitude=dest['long'],
        seat_count=1
    )
    return products, response


def _print_detail(products, response):
    pp.pprint('products[0]')
    pp.pprint(products[0])
    pp.pprint('response')
    pp.pprint(response.json)


if __name__ == '__main__':
    while True:
        try:
            get_estimate(name_orig='home', name_dest='work', detail=False)
            time.sleep(300)
        except KeyboardInterrupt:
            sys.exit('exiting by user')

