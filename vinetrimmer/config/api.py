import base64
import logging
from typing import Union

import m3u8
import requests
from construct import Container
from m3u8 import parse as m3u8parser

from vinetrimmer.objects.titles import Title
from vinetrimmer.objects.tracks import AudioTrack, VideoTrack
from vinetrimmer.services.amazon import Amazon
from vinetrimmer.services.appletvplus import AppleTVPlus
from vinetrimmer.services.BaseService import BaseService
from vinetrimmer.services.max import Max
from vinetrimmer.vendor.pymp4.parser import Box

logger = logging.getLogger("API")

class PlayReadyAPI:

    URL_HOST_API = 'https://ltpowerkeys.streamlt.xyz'
    URL_HOST_CACHE = f'{URL_HOST_API}/cache'
    URL_HOST_CHALLENGE = f'{URL_HOST_API}/challenge'
    URL_HOST_LICENSE = f'{URL_HOST_API}/keys'
    API_USERNAME = 'any_username'
    API_KEY = '11223344556677889900'
    DEVICE_NAME = 'pussy3'
    DEVICE_DSNP = 'd4k'
    DEVICE_ATVP = 'pck'
    
    def __init__(self, title: Title, track: Union[VideoTrack, AudioTrack], service: Union[BaseService, Amazon, AppleTVPlus, Max]) -> None:
        self.title = title
        self.track = track
        self.service = service
        self.session = requests.Session()
        self.session.headers.update(
            {
                'x-api-key': self.API_KEY,
                'x-api-username': self.API_USERNAME
            }
        )

    def get_keys(self):
        if self.title.source == "DSNP":
            master = m3u8parser(requests.get(self.track.extra.absolute_uri).text)
            for keys in master['keys']:
                if keys['keyformat'] == 'com.microsoft.playready':
                    self.track.pssh_playready = keys['uri'].split(",")[-1] #.replace('data:text/plain;base64,', '')

        if self.title.source == "ATVP":
            playlist = m3u8.load(self.track.extra["manifest"].absolute_uri)
            pr_pssh = None
            for key in playlist.keys:
                if key and key.keyformat == "com.microsoft.playready":
                    pr_keys = key.absolute_uri
                    pr_pssh = pr_keys.split(";")[2].split(",")[1]
                    self.track.pssh_playready = pr_pssh
                    break

        if self.title.source == "HULU":
            if isinstance(self.track.pssh_playready, Container):
               pssh_playready = Box.build(self.track.pssh_playready)
               self.track.pssh_playready = base64.b64encode(pssh_playready).decode()

        # Paso 1: Solicitar cache keys
        resp = requests.post(
            self.URL_HOST_CACHE,
            json={
                "pssh": self.track.pssh_playready,
                "device_name": (
                    self.DEVICE_DSNP if self.title.source in {"DSNP"} 
                    else self.DEVICE_ATVP if self.title.source in {"ATVP"} 
                    else self.DEVICE_NAME
                )
            },
            headers={'x-api-key': self.API_KEY, 'x-api-username': self.API_USERNAME}
        )

        if resp.status_code == 200:
            key = resp.json()["keys"]
            if key:
                logger.warning("API got cached keys!")
                cached_keys = key.split()
                keys = [
                    (key.split(":")[0], key.split(":")[1]) for key in cached_keys
                ]
                return keys

        # get challenge
        req = self.session.post(
            url=self.URL_HOST_CHALLENGE,
            json={
                "pssh": self.track.pssh_playready,
                "device_name": (
                    self.DEVICE_DSNP if self.title.source in {"DSNP"} 
                    else self.DEVICE_ATVP if self.title.source in {"ATVP"} 
                    else self.DEVICE_NAME
                )
            }
        )
        response = req.json()
 
        # streaming license
        license_data = self.service.license_playready(
            challenge=response['challenge'],
            title=self.title,
            track=self.track
        )

        # parse license
        req = self.session.post(
            url=self.URL_HOST_LICENSE,
            json={
                'license': license_data,
                "pssh": self.track.pssh_playready,
                "device_name": (
                    self.DEVICE_DSNP if self.title.source in {"DSNP"}
                    else self.DEVICE_ATVP if self.title.source in {"ATVP"}
                    else self.DEVICE_NAME
                )
            }
        )
        response = req.json()
        key = response['keys']

        if key:
            logger.warning("API got keys!")

            api_keys = key.split()
            keys = [
                (key.split(":")[0], key.split(":")[1]) for key in api_keys
            ]
            return keys
