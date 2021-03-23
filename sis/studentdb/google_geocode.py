# -*- coding: utf-8 -*-
"""Interface with Google Geocoder API."""
import logging

import requests
from django.conf import settings
from requests import HTTPError


def geocode(contact):
    if contact.lat is not None:
        return float(contact.lat), float(contact.long)

    addr = ",".join([part for part in [contact.street, contact.city, contact.state, contact.zip] if part])
    resp = requests.get("https://maps.googleapis.com/maps/api/geocode/json",
                        params={
                            "address": addr,
                            "key": settings.GOOGLE_GEOCODER_KEY
                        }
                        )

    try:
        resp.raise_for_status()
    except HTTPError as e:
        logging.getLogger(__name__).error("Geocoder error: %s", str(e))
        return None

    resp = resp.json()
    if resp['status'] == 'OK':
        try:
            contact.lat = resp['results'][0]['geometry']['location']['lat']
            contact.long = resp['results'][0]['geometry']['location']['lng']
            contact.save()
        except KeyError:
            return None

        return float(contact.lat), float(contact.long)
    elif resp['status'] == 'ZERO_RESULTS':
        return 0, 0
    else:
        logging.getLogger(__name__).error("Geocoder error: %s: %s", resp['status'], resp.get('error_message', None))

    return None
