import requests
import re
import discord
import asyncio
from discord.ext import commands
import discord
from discord import app_commands
from Crypto.Cipher import AES
import codecs
import hashlib
from Crypto.Util.Padding import pad
from Crypto.Util.Padding import unpad
import os 
import sys
#import riot_auth
# region 平台問題 https://stackoverflow.com/questions/45600579/asyncio-event-loop-is-closed-when-getting-loop
import platform
if platform.system()=='Windows':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
# endregion
import time
import traceback
from typing import Optional

###BEGUN
import ctypes
import json
import ssl
import sys
import warnings
from base64 import urlsafe_b64decode
from secrets import token_urlsafe
from typing import Dict, List, Optional, Sequence, Tuple, Union
from urllib.parse import parse_qsl, urlsplit

import aiohttp

from auth_exceptions import (
    RiotAuthenticationError,
    RiotAuthError,
    RiotMultifactorError,
    RiotRatelimitError,
    RiotUnknownErrorTypeError,
    RiotUnknownResponseTypeError,
)

__all__ = (
    "RiotAuthenticationError",
    "RiotAuthError",
    "RiotMultifactorError",
    "RiotRatelimitError",
    "RiotUnknownErrorTypeError",
    "RiotUnknownResponseTypeError",
    "RiotAuth",
)



class RiotAuth:
    RIOT_CLIENT_USER_AGENT = (
        "RiotClient/58.0.0 %s"
    )
    CIPHERS13 = ":".join(  # https://docs.python.org/3/library/ssl.html#tls-1-3
        (
            "TLS_CHACHA20_POLY1305_SHA256",
            "TLS_AES_128_GCM_SHA256",
            "TLS_AES_256_GCM_SHA384",
        )
    )
    CIPHERS = ":".join(
        (
            "ECDHE-ECDSA-CHACHA20-POLY1305",
            "ECDHE-RSA-CHACHA20-POLY1305",
            "ECDHE-ECDSA-AES128-GCM-SHA256",
            "ECDHE-RSA-AES128-GCM-SHA256",
            "ECDHE-ECDSA-AES256-GCM-SHA384",
            "ECDHE-RSA-AES256-GCM-SHA384",
            "ECDHE-ECDSA-AES128-SHA",
            "ECDHE-RSA-AES128-SHA",
            "ECDHE-ECDSA-AES256-SHA",
            "ECDHE-RSA-AES256-SHA",
            "AES128-GCM-SHA256",
            "AES256-GCM-SHA384",
            "AES128-SHA",
            "AES256-SHA",
            "DES-CBC3-SHA",  
        )
    )
    SIGALGS = ":".join(
        (
            "ecdsa_secp256r1_sha256",
            "rsa_pss_rsae_sha256",
            "rsa_pkcs1_sha256",
            "ecdsa_secp384r1_sha384",
            "rsa_pss_rsae_sha384",
            "rsa_pkcs1_sha384",
            "rsa_pss_rsae_sha512",
            "rsa_pkcs1_sha512",
            "rsa_pkcs1_sha1",  
        )
    )

    def __init__(self) -> None:
        self._auth_ssl_ctx = RiotAuth.create_riot_auth_ssl_ctx()
        self._cookie_jar = aiohttp.CookieJar()
        self.access_token: Optional[str] = None
        self.scope: Optional[str] = None
        self.id_token: Optional[str] = None
        self.token_type: Optional[str] = None
        self.expires_at: int = 0
        self.user_id: Optional[str] = None
        self.entitlements_token: Optional[str] = None

    @staticmethod
    def create_riot_auth_ssl_ctx() -> ssl.SSLContext:
        ssl_ctx = ssl.create_default_context()
        addr = id(ssl_ctx) + sys.getsizeof(object())
        ssl_ctx_addr = ctypes.cast(addr, ctypes.POINTER(ctypes.c_void_p)).contents

        if sys.platform.startswith("win32"):
            libssl = ctypes.CDLL("libssl-1_1.dll")
        elif sys.platform.startswith(("linux", "darwin")):
            libssl = ctypes.CDLL(ssl._ssl.__file__)
        else:
            raise NotImplementedError(
                "不支援的平台"
            )

        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=DeprecationWarning)
            ssl_ctx.minimum_version = ssl.TLSVersion.TLSv1
        ssl_ctx.set_alpn_protocols(["http/1.1"])
        ssl_ctx.options |= 1 << 19 
        libssl.SSL_CTX_set_ciphersuites(ssl_ctx_addr, RiotAuth.CIPHERS13.encode())
        libssl.SSL_CTX_set_cipher_list(ssl_ctx_addr, RiotAuth.CIPHERS.encode())
        libssl.SSL_CTX_ctrl(ssl_ctx_addr, 98, 0, RiotAuth.SIGALGS.encode())
        # print([cipher["name"] for cipher in ssl_ctx.get_ciphers()])
        return ssl_ctx

    def __update(
        self,
        extract_jwt: bool = False,
        key_attr_pairs: Sequence[Tuple[str, str]] = (
            ("sub", "user_id"),
            ("exp", "expires_at"),
        ),
        **kwargs,
    ) -> None:

        predefined_keys = [key for key in self.__dict__.keys() if key[0] != "_"]

        self.__dict__.update(
            (key, val) for key, val in kwargs.items() if key in predefined_keys
        )

        if extract_jwt: 
            additional_data = self.__get_keys_from_access_token(key_attr_pairs)
            self.__dict__.update(
                (key, val) for key, val in additional_data if key in predefined_keys
            )

    def __get_keys_from_access_token(
        self, key_attr_pairs: Sequence[Tuple[str, str]]
    ) -> List[
        Tuple[str, Union[str, int, List, Dict, None]]
    ]:  # List[Tuple[str, JSONType]]
        payload = self.access_token.split(".")[1]
        decoded = urlsafe_b64decode(f"{payload}===")
        temp_dict: Dict = json.loads(decoded)
        return [(attr, temp_dict.get(key)) for key, attr in key_attr_pairs]

    def __set_tokens_from_uri(self, data: Dict) -> None:
        mode = data["response"]["mode"]
        uri = data["response"]["parameters"]["uri"]

        result = getattr(urlsplit(uri), mode)
        data = dict(parse_qsl(result))
        self.__update(extract_jwt=True, **data)

    async def authorize(
        self, username: str, password: str, use_query_response_mode: bool = False
    ) -> None:
        """
        Authenticate username & password.
        """
        if username and password:
            self._cookie_jar.clear()

        conn = aiohttp.TCPConnector(ssl=self._auth_ssl_ctx)
        async with aiohttp.ClientSession(
            connector=conn, raise_for_status=True, cookie_jar=self._cookie_jar
        ) as session:
            headers = {
                "Accept-Encoding": "deflate, gzip, zstd",
                "user-agent": RiotAuth.RIOT_CLIENT_USER_AGENT % "rso-auth",
                "Cache-Control": "no-cache",
                "Accept": "application/json",
            }


            body = {
                "acr_values": "",
                "claims": "",
                "client_id": "riot-client",
                "code_challenge": "",
                "code_challenge_method": "",
                "nonce": token_urlsafe(16),
                "redirect_uri": "http://localhost/redirect",
                "response_type": "token id_token",
                "scope": "openid link ban lol_region account",
            }
            if use_query_response_mode:
                body["response_mode"] = "query"
            async with session.post(
                "https://auth.riotgames.com/api/v1/authorization",
                json=body,
                headers=headers,
            ) as r:
                data: Dict = await r.json()
                resp_type = data["type"]


            if resp_type != "response":  # not reauth
                # region Authenticate
                body = {
                    "language": "en_US",
                    "password": password,
                    "region": None,
                    "remember": False,
                    "type": "auth",
                    "username": username,
                }
                async with session.put(
                    "https://auth.riotgames.com/api/v1/authorization",
                    json=body,
                    headers=headers,
                ) as r:
                    data: Dict = await r.json()
                    resp_type = data["type"]
                    if resp_type == "response":
                        ...
                    elif resp_type == "auth":
                        err = data.get("error")
                        if err == "auth_failure":
                            raise RiotAuthenticationError(
                                f"認證失敗。帳密不匹配 `{err}`."
                            )
                        elif err == "rate_limited":
                            raise RiotRatelimitError()
                        else:
                            raise RiotUnknownErrorTypeError(
                                f"Got unknown error `{err}` during authentication."
                            )
                    elif resp_type == "multifactor":
                        raise RiotMultifactorError(
                            "目前不支持2auth"
                        )
                    else:
                        raise RiotUnknownResponseTypeError(
                            f"Got unknown response type `{resp_type}` during authentication."
                        )
                # endregion

            self._cookie_jar = session.cookie_jar
            self.__set_tokens_from_uri(data)

            # region Get new entitlements token
            headers["Authorization"] = f"{self.token_type} {self.access_token}"
            async with session.post(
                "https://entitlements.auth.riotgames.com/api/token/v1",
                headers=headers,
                json={},
                # json={"urn": "urn:entitlement:%"},
            ) as r:
                self.entitlements_token = (await r.json())["entitlements_token"]
            # endregion

    async def reauthorize(self) -> bool:
        """
        Reauthenticate using cookies.

        Returns a ``bool`` indicating success or failure.
        """
        try:
            await self.authorize("", "")
            return True
        except RiotAuthenticationError:  # because credentials are empty
            return False

###END
DataPath = 'data/valorant/'
valorant_ShopData=f"{DataPath}/valorant_ShopData2.json"
valorant_UserData=f"{DataPath}/valorant_UserData.json"
valorant_AgentsData=f"{DataPath}/valorant_AgentsData.json"
class ValorantCog(commands.Cog):

    
    def __init__(self, bot):
        self.bot = bot
        self.Valorant_KEY='50CC9BCCB7CDA275D289D289CCB7D289'
    def AES_CBC_encrypt(self,data, key, iv):
        cipher = AES.new(key, AES.MODE_CBC, iv)
        padding=pad(data,16,style='pkcs7')
        encrypt_data = cipher.encrypt(padding)
       # encrypt_data = codecs.encode(encrypt_data, 'hex')
        #print(padding)
        return encrypt_data
    def AES_CBC_decrypt(self,data, key, iv):
        cipher = AES.new(key, AES.MODE_CBC, iv)
        decrypt_data = cipher.decrypt(data)
        decrypt_data=unpad(decrypt_data,16,'pkcs7')
        #decrypt_data = codecs.encode(unpadraw, 'hex')
        return decrypt_data

    @app_commands.command(name="valorat_updatedb",description="dev用 更新db")
    async def valorat_updatedb(self, interaction: discord.Interaction):
       if interaction.user.id == 429640904463351818:
            await interaction.response.defer()
            with open(valorant_UserData, "rb") as f:
                tmp=f.read()
                data=self.AES_CBC_decrypt(tmp, bytes.fromhex(self.Valorant_KEY), bytes.fromhex(hashlib.md5("valorant_UserData.json".encode('utf-8')).hexdigest()))
                dictInfo = json.loads(data.decode("utf-8"))
                print(dictInfo)
                username=dictInfo[str(interaction.user.id)]['username']
                pw=dictInfo[str(interaction.user.id)]['pw']

            CREDS = username, pw
            REGION="ap"
            auth = RiotAuth()
            
            try:
                await auth.authorize(*CREDS)
                Access_Token_Type= auth.token_type
                Access_Token= auth.access_token
                Entitlements_Token= auth.entitlements_token
                User_ID= auth.user_id
                await auth.reauthorize()
            except :
                await auth.reauthorize()
                CREDS = username, pw
                REGION="ap"
                await auth.authorize(*CREDS)
                Access_Token_Type= auth.token_type
                Access_Token= auth.access_token
                Entitlements_Token= auth.entitlements_token
                User_ID= auth.user_id
                await auth.reauthorize()

           #獲取價目表
            headers = {
                'X-Riot-Entitlements-JWT': Entitlements_Token,
                'Authorization': f'Bearer {Access_Token}',
                "X-Riot-ClientPlatform": "ew0KCSJwbGF0Zm9ybVR5cGUiOiAiUEMiLA0KCSJwbGF0Zm9ybU9TIjogIldpbmRvd3MiLA0KCSJwbGF0Zm9ybU9TVmVyc2lvbiI6ICIxMC4wLjE5MDQyLjEuMjU2LjY0Yml0IiwNCgkicGxhdGZvcm1DaGlwc2V0IjogIlVua25vd24iDQp9"
            }
            data = requests.get(f"https://pd.{REGION}.a.pvp.net/store/v1/offers/", headers=headers)
            priceData = data.json()
            Dict_Price={}
            Dict_weaponInfos={}
            await auth.reauthorize()
            #獲取價目表END

            #獲取skin資料
            Dict_weaponInfos={}
            all_weapons = requests.get("https://valorant-api.com/v1/weapons?language=zh-TW")
            data_weapons = all_weapons.json()
            #Dict_Price創建 UUID:i價格
            #for i in range(len(priceData['Offers'])):
            #    ipric=int(*priceData['Offers'][i]['Cost'].values())
            #    Dict_Price.update({priceData['Offers'][i]['OfferID']:ipric})
           # print(Dict_Price)
            #Dict_Price創建END
            for i in range(len(data_weapons['data'])):
                for ii in range(len(data_weapons['data'][i]["skins"])):
                  itotalLevel=len(data_weapons['data'][i]["skins"][ii]["levels"])
                  try:
                     Dict_weaponInfos.update({data_weapons['data'][i]["skins"][ii]["levels"][0]["uuid"]:
                     {
                    "sz_weaponName":data_weapons['data'][i]["displayName"],
                    "sz_skinName":data_weapons['data'][i]["skins"][ii]["displayName"],
                     "sz_skinIcon":"",
                     "ilevels":itotalLevel,
                     "szfullLevelPreview":data_weapons['data'][i]["skins"][ii]["levels"][itotalLevel-1]["streamedVideo"],
                     "iprice":Dict_Price[data_weapons['data'][i]["skins"][ii]["levels"][0]["uuid"]]
                     }})
                  except KeyError: #data_weapons['data'][i]["skins"][ii]["displayIcon"][0]["displayIcon"]
                     Dict_weaponInfos.update({data_weapons['data'][i]["skins"][ii]["levels"][0]["uuid"]:
                     {
                    "sz_weaponName":data_weapons['data'][i]["displayName"],
                    "sz_skinName":data_weapons['data'][i]["skins"][ii]["displayName"],
                     "sz_skinIcon":"",
                     "ilevels":itotalLevel,
                     "szfullLevelPreview":data_weapons['data'][i]["skins"][ii]["levels"][itotalLevel-1]["streamedVideo"],
                     "iprice":0
                     }})
            data = requests.get(f"https://valorant-api.com/v1/agents?language=zh-TW")
            dictAgents = data.json()
            Dict_AgentsInfos={}
            for i in range(len(dictAgents['data'])):
                     Dict_AgentsInfos.update({dictAgents['data'][i]["uuid"]:
                     {
                    "sz_AgentName":dictAgents['data'][i]["displayName"],
                    "sz_AgentIcon":dictAgents['data'][i]["displayIcon"]
                     }})
            with open(valorant_ShopData, "w") as f:
                json.dump(Dict_weaponInfos, f)
            with open(valorant_AgentsData, "w") as f:
                json.dump(Dict_AgentsInfos, f)
            await interaction.followup.send('db更新完成')
#在這


    @app_commands.command(name="valorat_shop",description="查看本日商城造型(若尚未綁定riot帳號,或想要查其他帳號的商城,請填滿以下參數:username,pw")
    @app_commands.describe(username="riot帳號",pw="riot密碼")
    @app_commands.describe(bonlydisplayself="該指令回響是否只對自己顯示")
    async def valorat_updatedata(self, interaction: discord.Interaction,username: Optional[str] = None, pw: Optional[str] = None , bonlydisplayself: Optional[bool] = False):
            await interaction.response.defer()
            with open(valorant_UserData, "rb") as f:
                tmp=f.read()
                data=self.AES_CBC_decrypt(tmp, bytes.fromhex(self.Valorant_KEY), bytes.fromhex(hashlib.md5("valorant_UserData.json".encode('utf-8')).hexdigest()))
                dictInfo = json.loads(data.decode("utf-8"))

            if pw == None :
             try:
                username=dictInfo[str(interaction.user.id)]['username']
                pw=dictInfo[str(interaction.user.id)]['pw']
                CREDS = username, pw
                REGION="ap"
                auth = RiotAuth()
                try:
                
                    await auth.authorize(*CREDS)
                    Access_Token_Type= auth.token_type
                    Access_Token= auth.access_token
                    Entitlements_Token= auth.entitlements_token
                    User_ID= auth.user_id
                    await auth.reauthorize()
                except :
                    await auth.reauthorize()
                    await auth.authorize(*CREDS)
                    Access_Token_Type= auth.token_type
                    Access_Token= auth.access_token
                    Entitlements_Token= auth.entitlements_token
                    User_ID= auth.user_id
                    await auth.reauthorize()
    
                headers = {
                    'X-Riot-Entitlements-JWT': Entitlements_Token,
                    'Authorization': f'Bearer {Access_Token}',
                }
                r = requests.get(f'https://pd.{REGION}.a.pvp.net/store/v2/storefront/{User_ID}', headers=headers)
                skins_data = r.json()
                list_ShopUUID = skins_data["SkinsPanelLayout"]["SingleItemOffers"]
                shopResetTime = skins_data["SkinsPanelLayout"]["SingleItemOffersRemainingDurationInSeconds"]

                await auth.reauthorize()
                with open(valorant_ShopData, "r") as f:
                    Dict_weaponInfos = json.load(f)
                for UUID in list_ShopUUID:
                    print(UUID)
                    sz_weaponName=Dict_weaponInfos[UUID]['sz_weaponName']
                    sz_skinName=Dict_weaponInfos[UUID]['sz_skinName']
                    sz_skinIcon=Dict_weaponInfos[UUID]['sz_skinIcon']
                    ilevels=str(Dict_weaponInfos[UUID]['ilevels'])
                    szfullLevelPreview=Dict_weaponInfos[UUID]['szfullLevelPreview']
                    iprice=str(Dict_weaponInfos[UUID]['iprice'])
    
                    embed = discord.Embed(title=f"{sz_skinName}")
                   # print(UUID)
                   # if sz_skinIcon == None:
                   #     sz_skinIcon=f"https://media.valorant-api.com/weaponskinlevels/{UUID}/displayicon.png"
                   # else:
                   #     pass
                    embed.set_image(url=f"https://media.valorant-api.com/weaponskinlevels/{UUID}/displayicon.png")
                    embed.add_field(name="價格", value=iprice, inline=True)  
                    embed.add_field(name="最大等級", value=ilevels, inline=True)
                    embed.add_field(name="造型展示影片(最高等級)", value=szfullLevelPreview, inline=True)
                    await interaction.followup.send(embed=embed,ephemeral = bonlydisplayself)
                #await message.channel.send("valorant測試測試")
             except KeyError:
                await interaction.followup.send("尚未綁定帳號,請輸入shop <riot帳號> <riot密碼>查詢,或使用[setValorant <riot帳號> <riot密碼>]綁定(請用私訊的)")
             except RiotAuthenticationError:
                 await interaction.followup.send("錯誤:找不到帳號資料,請確認帳號資料是否正確,或是否更動過")
             except RiotMultifactorError:
                  await interaction.followup.send(f'[二次驗證錯誤]:不支援有使用二次驗證的帳戶,目前正在開發中')
            else:
             try:
                CREDS = username, pw
                REGION="ap"
                auth = RiotAuth()
                try:

                    await auth.authorize(*CREDS)
                    Access_Token_Type= auth.token_type
                    Access_Token= auth.access_token
                    Entitlements_Token= auth.entitlements_token
                    User_ID= auth.user_id
                    await auth.reauthorize()
                except :
                    await auth.reauthorize()
                    await auth.authorize(*CREDS)
                    Access_Token_Type= auth.token_type
                    Access_Token= auth.access_token
                    Entitlements_Token= auth.entitlements_token
                    User_ID= auth.user_id
                    await auth.reauthorize()

                headers = {
                    'X-Riot-Entitlements-JWT': Entitlements_Token,
                    'Authorization': f'Bearer {Access_Token}',
                }
                r = requests.get(f'https://pd.{REGION}.a.pvp.net/store/v2/storefront/{User_ID}', headers=headers)
                skins_data = r.json()
                list_ShopUUID = skins_data["SkinsPanelLayout"]["SingleItemOffers"]
                shopResetTime = skins_data["SkinsPanelLayout"]["SingleItemOffersRemainingDurationInSeconds"]

                await auth.reauthorize()
                with open(valorant_ShopData, "r") as f:
                    Dict_weaponInfos = json.load(f)
                for UUID in list_ShopUUID:
                    print(UUID)
                    sz_weaponName=Dict_weaponInfos[UUID]['sz_weaponName']
                    sz_skinName=Dict_weaponInfos[UUID]['sz_skinName']
                    sz_skinIcon=Dict_weaponInfos[UUID]['sz_skinIcon']
                    ilevels=str(Dict_weaponInfos[UUID]['ilevels'])
                    szfullLevelPreview=Dict_weaponInfos[UUID]['szfullLevelPreview']
                    iprice=str(Dict_weaponInfos[UUID]['iprice'])

                    embed = discord.Embed(title=f"{sz_skinName}")
                    embed.set_image(url=f"https://media.valorant-api.com/weaponskinlevels/{UUID}/displayicon.png")
                    embed.add_field(name="價格", value=iprice, inline=True)  
                    embed.add_field(name="最大等級", value=ilevels, inline=True)
                    embed.add_field(name="造型展示影片(最高等級)", value=szfullLevelPreview, inline=True)
                    await interaction.followup.send(embed=embed,ephemeral = bonlydisplayself)
             except RiotAuthenticationError:
                 await interaction.followup.send("錯誤:找不到帳號資料,請確認帳號資料是否正確")
             except RiotMultifactorError:
                  await interaction.followup.send(f'[二次驗證錯誤]:不支援有使用二次驗證的帳戶,目前正在開發中')
             except:
               await interaction.followup.send("請稍等重新嘗試(可能塞車了),或確認帳號資料是否正確")


    @app_commands.command(name="valorant_matchinfo",description="稽查當前對局所有人的資訊(進入讀取畫面後才可使用)")
    @app_commands.describe(username="riot帳號",pw="riot密碼")
    @app_commands.describe(bonlydisplayself="該指令回響是否只對自己顯示")
    async def valorant_matchinfo(self, interaction: discord.Interaction,username: Optional[str] = None, pw: Optional[str] = None , bonlydisplayself: Optional[bool] = False):
        def getVersion():
            versionData = requests.get("https://valorant-api.com/v1/version")
            versionDataJson = versionData.json()['data']
            final = f"{versionDataJson['branch']}-shipping-{versionDataJson['buildVersion']}-{versionDataJson['version'][-6:]}"
            return final

        def getmatchInfo(entitlements_token, access_token, user_id,matchid):
            headers = {
                'X-Riot-Entitlements-JWT': entitlements_token,
                'Authorization': f'Bearer {access_token}',
                "X-Riot-ClientPlatform": "ew0KCSJwbGF0Zm9ybVR5cGUiOiAiUEMiLA0KCSJwbGF0Zm9ybU9TIjogIldpbmRvd3MiLA0KCSJwbGF0Zm9ybU9TVmVyc2lvbiI6ICIxMC4wLjE5MDQyLjEuMjU2LjY0Yml0IiwNCgkicGxhdGZvcm1DaGlwc2V0IjogIlVua25vd24iDQp9"
            }
            data = requests.get(f"https://glz-ap-1.ap.a.pvp.net/core-game/v1/matches/{matchid}", headers=headers)  #"/core-game/v1/matches/{match_id}" #https://glz-ap-1.ap.a.pvp.net/core-game/v1/players/{user_id}
            tmp = data.json()
            #print(tmp)
            sz_status=tmp["State"]
            list_status=tmp["Players"]
            dict_blueTeam={}
            dict_redTeam={}
            seasonID=get_latest_season_id(entitlements_token, access_token, user_id)

            for i in range(len(list_status)):
                if list_status[i]["TeamID"] in "Blue":
                
                    playerPuid=list_status[i]["PlayerIdentity"]["Subject"]
                    other=get_rank(entitlements_token, access_token, user_id,playerPuid,seasonID) #[sz_rank,iNumberOfWins,iNumberOfGames,iRankedPoint]
                    dict_blueTeam.update({list_status[i]["CharacterID"]:{
                        "playerLevel":list_status[i]["PlayerIdentity"]["AccountLevel"],
                        "playeruid":list_status[i]["PlayerIdentity"]["Subject"],
                        "sz_rank":other[0],
                        "iNumberOfWins":other[1],
                        "iNumberOfGames":other[2],
                        "iRankedPoint":other[3]
                        }
                    })
                elif list_status[i]["TeamID"] in "Red":
                    playerPuid=list_status[i]["PlayerIdentity"]["Subject"]
                    other=get_rank(entitlements_token, access_token, user_id,playerPuid,seasonID) #[sz_rank,iNumberOfWins,iNumberOfGames,iRankedPoint]
                    dict_redTeam.update({list_status[i]["CharacterID"]:{
                        "playerLevel":list_status[i]["PlayerIdentity"]["AccountLevel"],
                        "playeruid":list_status[i]["PlayerIdentity"]["Subject"],
                        "sz_rank":other[0],
                        "iNumberOfWins":other[1],
                        "iNumberOfGames":other[2],
                        "iRankedPoint":other[3]
                        }
                    })

            return dict_blueTeam,dict_redTeam

        def getmatchId(entitlements_token, access_token, user_id):
            headers = {
                'X-Riot-Entitlements-JWT': entitlements_token,
                'Authorization': f'Bearer {access_token}',
                "X-Riot-ClientPlatform": "ew0KCSJwbGF0Zm9ybVR5cGUiOiAiUEMiLA0KCSJwbGF0Zm9ybU9TIjogIldpbmRvd3MiLA0KCSJwbGF0Zm9ybU9TVmVyc2lvbiI6ICIxMC4wLjE5MDQyLjEuMjU2LjY0Yml0IiwNCgkicGxhdGZvcm1DaGlwc2V0IjogIlVua25vd24iDQp9"
            }
            data = requests.get(f"https://glz-ap-1.ap.a.pvp.net/core-game/v1/players/{user_id}", headers=headers)  #"https://pd.{REGION}.a.pvp.net/core-game/v1/matches/{match_id}"
            #Data = data.text.json()
            #print(data.text)
            #return getmatchInfo(entitlements_token, access_token, user_id, data.json()["MatchID"])
            try:
                #data.json()["MatchID"]
                return getmatchInfo(entitlements_token, access_token, user_id, data.json()["MatchID"])
            except:
                return 0


        def get_content(entitlements_token, access_token, user_id):
            headers = {
                'X-Riot-Entitlements-JWT': entitlements_token,
                'Authorization': f'Bearer {access_token}',
                "X-Riot-ClientVersion": getVersion(),
                "X-Riot-ClientPlatform": "ew0KCSJwbGF0Zm9ybVR5cGUiOiAiUEMiLA0KCSJwbGF0Zm9ybU9TIjogIldpbmRvd3MiLA0KCSJwbGF0Zm9ybU9TVmVyc2lvbiI6ICIxMC4wLjE5MDQyLjEuMjU2LjY0Yml0IiwNCgkicGxhdGZvcm1DaGlwc2V0IjogIlVua25vd24iDQp9"
            }
            tmp = requests.get(f"https://shared.{REGION}.a.pvp.net/content-service/v3/content", headers=headers) 
            return tmp.json()

            #return content.text
        def get_latest_season_id(entitlements_token, access_token, user_id):
            content=get_content(entitlements_token, access_token, user_id)
            for season in content["Seasons"]:
                if season["IsActive"]:
                    return season["ID"]

        def get_rank(entitlements_token, access_token, user_id,puuid,seasonID):
            #puuid="c6d387d8-f1dc-5e54-a68d-7d6d7e9d71ef"
            headers = {
                'X-Riot-Entitlements-JWT': entitlements_token,
                'Authorization': f'Bearer {access_token}',
                "X-Riot-ClientVersion": getVersion(),
                "X-Riot-ClientPlatform": "ew0KCSJwbGF0Zm9ybVR5cGUiOiAiUEMiLA0KCSJwbGF0Zm9ybU9TIjogIldpbmRvd3MiLA0KCSJwbGF0Zm9ybU9TVmVyc2lvbiI6ICIxMC4wLjE5MDQyLjEuMjU2LjY0Yml0IiwNCgkicGxhdGZvcm1DaGlwc2V0IjogIlVua25vd24iDQp9"
            }

            dt = requests.get(f"https://pd.{REGION}.a.pvp.net/mmr/v1/players/{puuid}", headers=headers)  

            r=dt.json()
            dictRankT={
                3:'鐵牌1',
                4:'鐵牌2',
                5:'鐵牌3',
                6:'青銅1',
                7:'青銅2',
                8:'青銅3',
                9:'白銀1',
                10:'白銀2',
                11:'白銀3',
                12:'金牌1',
                13:'金牌2',
                14:'金牌3',
                15:'白金1',
                16:'白金2',
                17:'白金3',
                18:'鑽石1',
                19:'鑽石2',
                20:'鑽石3',
                21:'超凡入聖1',
                22:'超凡入聖2',
                23:'超凡入聖3',
                24:'神話1',
                25:'神話2',
                26:'神話3'}
            try:
                rankTIER = r["QueueSkills"]["competitive"]["SeasonalInfoBySeasonID"][seasonID]["CompetitiveTier"] #7
                iNumberOfWins = r["QueueSkills"]["competitive"]["SeasonalInfoBySeasonID"][seasonID]["NumberOfWinsWithPlacements"] #包括定階賽
                iNumberOfGames = r["QueueSkills"]["competitive"]["SeasonalInfoBySeasonID"][seasonID]["NumberOfGames"]
                iRankedPoint = r["QueueSkills"]["competitive"]["SeasonalInfoBySeasonID"][seasonID]["RankedRating"]
                if int(rankTIER) >= 27:
                    sz_rank = "輻能戰魂"
                elif int(rankTIER) in (0, 1, 2, 3):
                    sz_rank="鐵牌1"
                else:
                    try:
                        sz_rank=dictRankT[rankTIER]
                    except:
                        sz_rank="未知"+str(rankTIER)
            except :
                sz_rank="無"
                iNumberOfWins=0
                iNumberOfGames=-1
                iRankedPoint=0
            return [sz_rank,iNumberOfWins,iNumberOfGames,iRankedPoint]
        await interaction.response.defer()
        await interaction.followup.send('正在搜尋中(可能需要10~15秒)...', delete_after=10,ephemeral=True)
        #msgWaiting = await ctx.respond("正在搜尋中(可能需要10~15秒)...")
        with open(valorant_UserData, "rb") as f:
            tmp=f.read()
            data=self.AES_CBC_decrypt(tmp, bytes.fromhex(self.Valorant_KEY), bytes.fromhex(hashlib.md5("valorant_UserData.json".encode('utf-8')).hexdigest()))
            dictInfo = json.loads(data.decode("utf-8"))
        #with open(valorant_UserData, "r") as f:
        #    dictInfo = json.load(f)
        if pw == None :
         try:
            username=dictInfo[str(interaction.user.id)]['username']
            pw=dictInfo[str(interaction.user.id)]['pw']
            CREDS = username, pw
            REGION="ap"
            auth = RiotAuth()
            try:
               CREDS = username, pw
               REGION="ap"
               auth = RiotAuth()
               try:

                   await auth.authorize(*CREDS)
                   Access_Token_Type= auth.token_type
                   Access_Token= auth.access_token
                   Entitlements_Token= auth.entitlements_token
                   User_ID= auth.user_id
                   await auth.reauthorize()
               except :
                   await auth.reauthorize()
                   await auth.authorize(*CREDS)
                   Access_Token_Type= auth.token_type
                   Access_Token= auth.access_token
                   Entitlements_Token= auth.entitlements_token
                   User_ID= auth.user_id
                   await auth.reauthorize()


               with open(valorant_AgentsData, "r") as f:
                   Dict_AgentsInfos = json.load(f)

               tmp=getmatchId(Entitlements_Token,Access_Token,User_ID) #dict_blueTeam,dict_redTeam
               #embed = discord.Embed(title=f"對局訊息")
               embed = discord.Embed(color=discord.Color.blue())
               for key in tmp[0]:
                   #tmp[0][key]["playeruid"]
                   
                   level=str(tmp[0][key]["playerLevel"])
                   rank=tmp[0][key]["sz_rank"]+"("+str(tmp[0][key]["iRankedPoint"])+"點)"
                   WLandWin=str(tmp[0][key]["iNumberOfWins"])
                   rankmatchnum=str(tmp[0][key]["iNumberOfGames"])
                   winrate=str(round(tmp[0][key]["iNumberOfWins"]/tmp[0][key]["iNumberOfGames"], 2)*100)
                   #embed.add_field(name="等級:", value=level, inline=True) 
                   #embed.add_field(name="本季排位:", value=rank, inline=True) 
                   #embed.add_field(name="本季排位場次:", value=rankmatchnum+" (勝場:"+WLandWinrate+")", inline=True)  
                   #text="等級:`"+level+"` | 本季排位:`"+rank+"` | 本季排位場次:`"+rankmatchnum+"` (勝場:`"+WLandWinrate+"`)"
                   #embed.add_field(name="[藍方]"+Dict_AgentsInfos[key.lower()]["sz_AgentName"], value=text, inline=False) 
                   embed.add_field(name="[防守方]"+Dict_AgentsInfos[key.lower()]["sz_AgentName"], value=f"**➤ 等級:** `{level}`\n**➤ 本季排位:** ` {rank}`\n**➤ 本季排位賽勝場/總場次:** `{WLandWin}/{rankmatchnum} ({winrate}%)`", inline=False)
               await interaction.followup.send(embed=embed,ephemeral = bonlydisplayself)

               embed = discord.Embed(color=discord.Color.red())
               for key in tmp[1]:
                   level=str(tmp[1][key]["playerLevel"])
                   rank=tmp[1][key]["sz_rank"]+"("+str(tmp[1][key]["iRankedPoint"])+"點)"
                   WLandWin=str(tmp[1][key]["iNumberOfWins"])  #+"/敗:"+str(tmp[0][key]["iNumberOfGames"]-tmp[0][key]["iNumberOfWins"])
                   rankmatchnum=str(tmp[1][key]["iNumberOfGames"])
                   winrate=str(round(tmp[1][key]["iNumberOfWins"]/tmp[1][key]["iNumberOfGames"], 2)*100)
                   #embed.add_field(name="等級:", value=level, inline=True) 
                   #embed.add_field(name="本季排位:", value=rank, inline=True) 
                   #embed.add_field(name="本季排位場次:", value=rankmatchnum+" (勝場:"+WLandWinrate+")", inline=True)
                   embed.add_field(name="[攻擊方]"+Dict_AgentsInfos[key.lower()]["sz_AgentName"], value=f"**➤ 等級:** `{level}`\n**➤ 本季排位:** ` {rank}`\n**➤ 本季排位賽勝場/總場次:** `{WLandWin}/{rankmatchnum} ({winrate}%)`", inline=False)  
               await interaction.followup.send(embed=embed,ephemeral= bonlydisplayself)
            except TypeError:
                await interaction.followup.send("錯誤:對局尚未開始,請等待選角階段結束並確認是否已進入讀取介面",ephemeral= bonlydisplayself)


         except KeyError:
            await interaction.followup.send("尚未綁定帳號,請輸入shop <riot帳號> <riot密碼>查詢,或使用[setValorant <riot帳號> <riot密碼>]綁定(請用私訊的)",ephemeral= bonlydisplayself)
         except RiotAuthenticationError:
             await interaction.followup.send("錯誤:找不到帳號資料,請確認帳號資料是否正確,或是否更動過",ephemeral= bonlydisplayself)
         except RiotMultifactorError:
              await interaction.followup.send(f'[二次驗證錯誤]:不支援有使用二次驗證的帳戶,目前正在開發中',ephemeral= bonlydisplayself)
        else:
            try:
               CREDS = username, pw
               REGION="ap"
               auth = RiotAuth()
               try:

                   await auth.authorize(*CREDS)
                   Access_Token_Type= auth.token_type
                   Access_Token= auth.access_token
                   Entitlements_Token= auth.entitlements_token
                   User_ID= auth.user_id
                   await auth.reauthorize()
               except :
                   await auth.reauthorize()
                   await auth.authorize(*CREDS)
                   Access_Token_Type= auth.token_type
                   Access_Token= auth.access_token
                   Entitlements_Token= auth.entitlements_token
                   User_ID= auth.user_id
                   await auth.reauthorize()


               with open(valorant_AgentsData, "r") as f:
                   Dict_AgentsInfos = json.load(f)

               tmp=getmatchId(Entitlements_Token,Access_Token,User_ID) #dict_blueTeam,dict_redTeam
               #embed = discord.Embed(title=f"對局訊息")
               embed = discord.Embed(color=discord.Color.blue())
               for key in tmp[0]:
                   #tmp[0][key]["playeruid"]
                   
                   level=str(tmp[0][key]["playerLevel"])
                   rank=tmp[0][key]["sz_rank"]+"("+str(tmp[0][key]["iRankedPoint"])+"點)"
                   WLandWin=str(tmp[0][key]["iNumberOfWins"])
                   rankmatchnum=str(tmp[0][key]["iNumberOfGames"])
                   winrate=str(round(tmp[0][key]["iNumberOfWins"]/tmp[0][key]["iNumberOfGames"], 2)*100)
                   #embed.add_field(name="等級:", value=level, inline=True) 
                   #embed.add_field(name="本季排位:", value=rank, inline=True) 
                   #embed.add_field(name="本季排位場次:", value=rankmatchnum+" (勝場:"+WLandWinrate+")", inline=True)  
                   #text="等級:`"+level+"` | 本季排位:`"+rank+"` | 本季排位場次:`"+rankmatchnum+"` (勝場:`"+WLandWinrate+"`)"
                   #embed.add_field(name="[藍方]"+Dict_AgentsInfos[key.lower()]["sz_AgentName"], value=text, inline=False) 
                   embed.add_field(name="[防守方]"+Dict_AgentsInfos[key.lower()]["sz_AgentName"], value=f"**➤ 等級:** `{level}`\n**➤ 本季排位:** ` {rank}`\n**➤ 本季排位賽勝場/總場次:** `{WLandWin}/{rankmatchnum} ({winrate}%)`", inline=False)
               await interaction.followup.send(embed=embed,ephemeral = bonlydisplayself)

               embed = discord.Embed(color=discord.Color.red())
               for key in tmp[1]:
                   level=str(tmp[1][key]["playerLevel"])
                   rank=tmp[1][key]["sz_rank"]+"("+str(tmp[1][key]["iRankedPoint"])+"點)"
                   WLandWin=str(tmp[1][key]["iNumberOfWins"])  #+"/敗:"+str(tmp[0][key]["iNumberOfGames"]-tmp[0][key]["iNumberOfWins"])
                   rankmatchnum=str(tmp[1][key]["iNumberOfGames"])
                   winrate=str(round(tmp[1][key]["iNumberOfWins"]/tmp[1][key]["iNumberOfGames"], 2)*100)
                   #embed.add_field(name="等級:", value=level, inline=True) 
                   #embed.add_field(name="本季排位:", value=rank, inline=True) 
                   #embed.add_field(name="本季排位場次:", value=rankmatchnum+" (勝場:"+WLandWinrate+")", inline=True)
                   embed.add_field(name="[攻擊方]"+Dict_AgentsInfos[key.lower()]["sz_AgentName"], value=f"**➤ 等級:** `{level}`\n**➤ 本季排位:** ` {rank}`\n**➤ 本季排位賽勝場/總場次:** `{WLandWin}/{rankmatchnum} ({winrate}%)`", inline=False)  
               await interaction.followup.send(embed=embed,ephemeral = bonlydisplayself)


            except RiotAuthenticationError:
                await interaction.followup.send("錯誤:找不到帳號資料,請確認帳號資料是否正確",ephemeral= bonlydisplayself)
            except TypeError:
                await interaction.followup.send("錯誤:對局尚未開始,請等待選角階段結束並確認是否已進入讀取介面",ephemeral= bonlydisplayself)
            except RiotMultifactorError:
                 await interaction.followup.send(f'[二次驗證錯誤]:不支援有使用二次驗證的帳戶,目前正在開發中',ephemeral= bonlydisplayself)
            except:
                await interaction.followup.send("請稍等重新嘗試(可能塞車了),或確認帳號資料是否正確",ephemeral= bonlydisplayself)



    @app_commands.command(name="valorant_bind",description="綁定/切換特戰英豪riot帳號")
    @app_commands.describe(username="riot帳號",pw="riot密碼")
    @app_commands.describe(bonlydisplayself="該指令回響是否只對自己顯示")
    async def valorant_bind(self, interaction: discord.Interaction,username: Optional[str] = None, pw: Optional[str] = None , bonlydisplayself: Optional[bool] = False):
            try :
                CREDS = username, pw
                REGION="ap"
                auth = RiotAuth()
                await auth.authorize(*CREDS)
                User_ID= auth.user_id
                with open(valorant_UserData, "rb") as f:
                    tmp=f.read()
                    data=self.AES_CBC_decrypt(tmp, bytes.fromhex(self.Valorant_KEY), bytes.fromhex(hashlib.md5("valorant_UserData.json".encode('utf-8')).hexdigest()))
                    dictInfo = json.loads(data.decode("utf-8"))
                    dictInfo.update({str(interaction.user.id):{"username":username,"pw":pw,}})
                with open(valorant_UserData, "wb") as f:
                    dictInfo=json.dumps(dictInfo)
                    data=self.AES_CBC_encrypt(dictInfo.encode(), bytes.fromhex(self.Valorant_KEY), bytes.fromhex(hashlib.md5("valorant_UserData.json".encode('utf-8')).hexdigest()))
                    f.write(data)
                    #json.dump(dictInfo, f)
                    
                await interaction.response.send_message("綁定成功,puuid:"+User_ID,ephemeral = bonlydisplayself)
            except KeyError:
                 await interaction.response.send_message(f'獲取puuid失敗,請過幾分鐘後再試試,或是檢察帳戶資料是否錯誤(若是綁定google/fb/apple 則需填寫的資料為Riot帳號&密碼(riotclient->右上角帳號資訊->https://media.discordapp.net/attachments/976434681669091358/1003913083061809152/unknown.png?width=926&height=523)',ephemeral = bonlydisplayself)
            except RiotMultifactorError:
                 await interaction.response.send_message(f'[二次驗證錯誤]:不支援有使用二次驗證的帳戶,目前正在開發中',ephemeral = bonlydisplayself)


###稽查BEGIN###
    @app_commands.command(name="valorant_shop2",description="稽查他人商城造型")
    @app_commands.describe(user="user")
    @app_commands.describe(bonlydisplayself="該指令回響是否只對自己顯示")
    async def valorant_shop2(self, interaction: discord.Interaction,user: discord.Member, bonlydisplayself: Optional[bool] = False):
        try:
           userID=user.id
           await interaction.response.defer()
           with open(valorant_UserData, "rb") as f:
               tmp=f.read()
               data=self.AES_CBC_decrypt(tmp, bytes.fromhex(self.Valorant_KEY), bytes.fromhex(hashlib.md5("valorant_UserData.json".encode('utf-8')).hexdigest()))
               dictInfo = json.loads(data.decode("utf-8"))
        
           username=dictInfo[str(userID)]['username']
           pw=dictInfo[str(userID)]['pw']
           CREDS = username, pw
           REGION="ap"
           auth = RiotAuth()
           try:
           
               await auth.authorize(*CREDS)
               Access_Token_Type= auth.token_type
               Access_Token= auth.access_token
               Entitlements_Token= auth.entitlements_token
               User_ID= auth.user_id
               await auth.reauthorize()
           except :
               await auth.reauthorize()
               await auth.authorize(*CREDS)
               Access_Token_Type= auth.token_type
               Access_Token= auth.access_token
               Entitlements_Token= auth.entitlements_token
               User_ID= auth.user_id
               await auth.reauthorize()

           headers = {
               'X-Riot-Entitlements-JWT': Entitlements_Token,
               'Authorization': f'Bearer {Access_Token}',
           }
           r = requests.get(f'https://pd.{REGION}.a.pvp.net/store/v2/storefront/{User_ID}', headers=headers)
           skins_data = r.json()
           list_ShopUUID = skins_data["SkinsPanelLayout"]["SingleItemOffers"]
           shopResetTime = skins_data["SkinsPanelLayout"]["SingleItemOffersRemainingDurationInSeconds"]

           await auth.reauthorize()
           with open(valorant_ShopData, "r") as f:
               Dict_weaponInfos = json.load(f)
           for UUID in list_ShopUUID:
               print(UUID)
               sz_weaponName=Dict_weaponInfos[UUID]['sz_weaponName']
               sz_skinName=Dict_weaponInfos[UUID]['sz_skinName']
               sz_skinIcon=Dict_weaponInfos[UUID]['sz_skinIcon']
               ilevels=str(Dict_weaponInfos[UUID]['ilevels'])
               szfullLevelPreview=Dict_weaponInfos[UUID]['szfullLevelPreview']
               iprice=str(Dict_weaponInfos[UUID]['iprice'])

               embed = discord.Embed(title=f"{sz_skinName}")
              # print(UUID)
              # if sz_skinIcon == None:
              #     sz_skinIcon=f"https://media.valorant-api.com/weaponskinlevels/{UUID}/displayicon.png"
              # else:
              #     pass
               embed.set_image(url=f"https://media.valorant-api.com/weaponskinlevels/{UUID}/displayicon.png")
               embed.add_field(name="價格", value=iprice, inline=True)  
               embed.add_field(name="最大等級", value=ilevels, inline=True)
               embed.add_field(name="造型展示影片(最高等級)", value=szfullLevelPreview, inline=True)
               await interaction.followup.send(embed=embed, ephemeral = bonlydisplayself)
           #await message.channel.send("valorant測試測試")
        except KeyError:
           await interaction.response.send_message("對方尚未綁定帳號")
        except RiotAuthenticationError:
            await interaction.response.send_message("錯誤:找不到帳號資料,請確認帳號資料是否正確,或是否更動過", ephemeral = bonlydisplayself)
        except RiotMultifactorError:
            await interaction.response.send_message(f'[二次驗證錯誤]:不支援有使用二次驗證的帳戶,目前正在開發中', ephemeral = bonlydisplayself)
        except Exception as err:
            print("[valorant shop2 error]")
            print(err)
            ErrorEmbed = discord.Embed(color=0xFF0000)
            ErrorEmbed.set_author(name=f'[valorant shop2 error]\nFBI WARNING!!!:"{str(traceback.format_exc())}\n{str(err)}"\n遇到了預期外的操作或程式錯誤')
            print(traceback.format_exc())
            await interaction.response.send_message(embed=ErrorEmbed)


    """
    @commands.slash_command(description="稽查他人當前對局所有人的資訊(進入讀取畫面後才可使用)")
    @option("bonlydisplayself",bool, description="該指令回響是否只對自己顯示", required=False)
    async def valorant_matchinfo2(self, ctx,user : discord.Member,bonlydisplayself=False):
        userID=user.id
        def getVersion():
            versionData = requests.get("https://valorant-api.com/v1/version")
            versionDataJson = versionData.json()['data']
            final = f"{versionDataJson['branch']}-shipping-{versionDataJson['buildVersion']}-{versionDataJson['version'][-6:]}"
            return final

        def getmatchInfo(entitlements_token, access_token, user_id,matchid):
            headers = {
                'X-Riot-Entitlements-JWT': entitlements_token,
                'Authorization': f'Bearer {access_token}',
                "X-Riot-ClientPlatform": "ew0KCSJwbGF0Zm9ybVR5cGUiOiAiUEMiLA0KCSJwbGF0Zm9ybU9TIjogIldpbmRvd3MiLA0KCSJwbGF0Zm9ybU9TVmVyc2lvbiI6ICIxMC4wLjE5MDQyLjEuMjU2LjY0Yml0IiwNCgkicGxhdGZvcm1DaGlwc2V0IjogIlVua25vd24iDQp9"
            }
            data = requests.get(f"https://glz-ap-1.ap.a.pvp.net/core-game/v1/matches/{matchid}", headers=headers)  #"/core-game/v1/matches/{match_id}" #https://glz-ap-1.ap.a.pvp.net/core-game/v1/players/{user_id}
            tmp = data.json()
            #print(tmp)
            sz_status=tmp["State"]
            list_status=tmp["Players"]
            dict_blueTeam={}
            dict_redTeam={}
            seasonID=get_latest_season_id(entitlements_token, access_token, user_id)

            for i in range(len(list_status)):
                if list_status[i]["TeamID"] in "Blue":
                
                    playerPuid=list_status[i]["PlayerIdentity"]["Subject"]
                    other=get_rank(entitlements_token, access_token, user_id,playerPuid,seasonID) #[sz_rank,iNumberOfWins,iNumberOfGames,iRankedPoint]
                    dict_blueTeam.update({list_status[i]["CharacterID"]:{
                        "playerLevel":list_status[i]["PlayerIdentity"]["AccountLevel"],
                        "playeruid":list_status[i]["PlayerIdentity"]["Subject"],
                        "sz_rank":other[0],
                        "iNumberOfWins":other[1],
                        "iNumberOfGames":other[2],
                        "iRankedPoint":other[3]
                        }
                    })
                elif list_status[i]["TeamID"] in "Red":
                    playerPuid=list_status[i]["PlayerIdentity"]["Subject"]
                    other=get_rank(entitlements_token, access_token, user_id,playerPuid,seasonID) #[sz_rank,iNumberOfWins,iNumberOfGames,iRankedPoint]
                    dict_redTeam.update({list_status[i]["CharacterID"]:{
                        "playerLevel":list_status[i]["PlayerIdentity"]["AccountLevel"],
                        "playeruid":list_status[i]["PlayerIdentity"]["Subject"],
                        "sz_rank":other[0],
                        "iNumberOfWins":other[1],
                        "iNumberOfGames":other[2],
                        "iRankedPoint":other[3]
                        }
                    })

            return dict_blueTeam,dict_redTeam

        def getmatchId(entitlements_token, access_token, user_id):
            headers = {
                'X-Riot-Entitlements-JWT': entitlements_token,
                'Authorization': f'Bearer {access_token}',
                "X-Riot-ClientPlatform": "ew0KCSJwbGF0Zm9ybVR5cGUiOiAiUEMiLA0KCSJwbGF0Zm9ybU9TIjogIldpbmRvd3MiLA0KCSJwbGF0Zm9ybU9TVmVyc2lvbiI6ICIxMC4wLjE5MDQyLjEuMjU2LjY0Yml0IiwNCgkicGxhdGZvcm1DaGlwc2V0IjogIlVua25vd24iDQp9"
            }
            data = requests.get(f"https://glz-ap-1.ap.a.pvp.net/core-game/v1/players/{user_id}", headers=headers)  #"https://pd.{REGION}.a.pvp.net/core-game/v1/matches/{match_id}"
            #Data = data.text.json()
            #print(data.text)
            #return getmatchInfo(entitlements_token, access_token, user_id, data.json()["MatchID"])
            try:
                #data.json()["MatchID"]
                return getmatchInfo(entitlements_token, access_token, user_id, data.json()["MatchID"])
            except:
                return 0


        def get_content(entitlements_token, access_token, user_id):
            headers = {
                'X-Riot-Entitlements-JWT': entitlements_token,
                'Authorization': f'Bearer {access_token}',
                "X-Riot-ClientVersion": getVersion(),
                "X-Riot-ClientPlatform": "ew0KCSJwbGF0Zm9ybVR5cGUiOiAiUEMiLA0KCSJwbGF0Zm9ybU9TIjogIldpbmRvd3MiLA0KCSJwbGF0Zm9ybU9TVmVyc2lvbiI6ICIxMC4wLjE5MDQyLjEuMjU2LjY0Yml0IiwNCgkicGxhdGZvcm1DaGlwc2V0IjogIlVua25vd24iDQp9"
            }
            tmp = requests.get(f"https://shared.{REGION}.a.pvp.net/content-service/v3/content", headers=headers) 
            return tmp.json()

            #return content.text
        def get_latest_season_id(entitlements_token, access_token, user_id):
            content=get_content(entitlements_token, access_token, user_id)
            for season in content["Seasons"]:
                if season["IsActive"]:
                    return season["ID"]

        def get_rank(entitlements_token, access_token, user_id,puuid,seasonID):
            #puuid="c6d387d8-f1dc-5e54-a68d-7d6d7e9d71ef"
            headers = {
                'X-Riot-Entitlements-JWT': entitlements_token,
                'Authorization': f'Bearer {access_token}',
                "X-Riot-ClientVersion": getVersion(),
                "X-Riot-ClientPlatform": "ew0KCSJwbGF0Zm9ybVR5cGUiOiAiUEMiLA0KCSJwbGF0Zm9ybU9TIjogIldpbmRvd3MiLA0KCSJwbGF0Zm9ybU9TVmVyc2lvbiI6ICIxMC4wLjE5MDQyLjEuMjU2LjY0Yml0IiwNCgkicGxhdGZvcm1DaGlwc2V0IjogIlVua25vd24iDQp9"
            }

            dt = requests.get(f"https://pd.{REGION}.a.pvp.net/mmr/v1/players/{puuid}", headers=headers)  

            r=dt.json()
            dictRankT={
                3:'鐵牌1',
                4:'鐵牌2',
                5:'鐵牌3',
                6:'青銅1',
                7:'青銅2',
                8:'青銅3',
                9:'白銀1',
                10:'白銀2',
                11:'白銀3',
                12:'金牌1',
                13:'金牌2',
                14:'金牌3',
                15:'白金1',
                16:'白金2',
                17:'白金3',
                18:'鑽石1',
                19:'鑽石2',
                20:'鑽石3',
                21:'超凡入聖1',
                22:'超凡入聖2',
                23:'超凡入聖3',
                24:'神話1',
                25:'神話2',
                26:'神話3'}
            try:
                rankTIER = r["QueueSkills"]["competitive"]["SeasonalInfoBySeasonID"][seasonID]["CompetitiveTier"] #7
                iNumberOfWins = r["QueueSkills"]["competitive"]["SeasonalInfoBySeasonID"][seasonID]["NumberOfWinsWithPlacements"] #包括定階賽
                iNumberOfGames = r["QueueSkills"]["competitive"]["SeasonalInfoBySeasonID"][seasonID]["NumberOfGames"]
                iRankedPoint = r["QueueSkills"]["competitive"]["SeasonalInfoBySeasonID"][seasonID]["RankedRating"]
                if int(rankTIER) >= 27:
                    sz_rank = "輻能戰魂"
                elif int(rankTIER) in (0, 1, 2, 3):
                    sz_rank="鐵牌1"
                else:
                    try:
                        sz_rank=dictRankT[rankTIER]
                    except:
                        sz_rank="未知"+str(rankTIER)
            except :
                sz_rank="無"
                iNumberOfWins=0
                iNumberOfGames=-1
                iRankedPoint=0
            return [sz_rank,iNumberOfWins,iNumberOfGames,iRankedPoint]

        await interaction.response.defer()
        await ctx.respond('正在搜尋中(可能需要10~15秒)...', delete_after=10,ephemeral=True)
        with open(valorant_UserData, "rb") as f:
            tmp=f.read()
            data=self.AES_CBC_decrypt(tmp, bytes.fromhex(self.Valorant_KEY), bytes.fromhex(hashlib.md5(valorant_UserData.encode('utf-8')).hexdigest()))
            dictInfo = json.loads(data.decode("utf-8"))
        #with open(valorant_UserData, "r") as f:
        #    dictInfo = json.load(f)
        try:
           username=dictInfo[str(userID)]['username']
           pw=dictInfo[str(userID)]['pw']
           CREDS = username, pw
           REGION="ap"
           auth = RiotAuth()
           try:
              CREDS = username, pw
              REGION="ap"
              auth = RiotAuth()
              try:
                  await auth.authorize(*CREDS)
                  Access_Token_Type= auth.token_type
                  Access_Token= auth.access_token
                  Entitlements_Token= auth.entitlements_token
                  User_ID= auth.user_id
                  await auth.reauthorize()
              except :
                  await auth.reauthorize()
                  await auth.authorize(*CREDS)
                  Access_Token_Type= auth.token_type
                  Access_Token= auth.access_token
                  Entitlements_Token= auth.entitlements_token
                  User_ID= auth.user_id
                  await auth.reauthorize()
              with open(valorant_AgentsData, "r") as f:
                  Dict_AgentsInfos = json.load(f)
              tmp=getmatchId(Entitlements_Token,Access_Token,User_ID) #dict_blueTeam,dict_redTeam
              #embed = discord.Embed(title=f"對局訊息")
              embed = discord.Embed(color=discord.Color.blue())
              for key in tmp[0]:
                  
                  level=str(tmp[0][key]["playerLevel"])
                  rank=tmp[0][key]["sz_rank"]+"("+str(tmp[0][key]["iRankedPoint"])+"點)"
                  WLandWin=str(tmp[0][key]["iNumberOfWins"])
                  rankmatchnum=str(tmp[0][key]["iNumberOfGames"])
                  winrate=str(round(tmp[0][key]["iNumberOfWins"]/tmp[0][key]["iNumberOfGames"], 2)*100)
                  embed.add_field(name="[防守方]"+Dict_AgentsInfos[key.lower()]["sz_AgentName"], value=f"**➤ 等級:** `{level}`\n**➤ 本季排位:** ` {rank}`\n**➤ 本季排位賽勝場/總場次:** `{WLandWin}/{rankmatchnum} ({winrate}%)`", inline=False)
              await ctx.respond(embed=embed, ephemeral = bonlydisplayself)
              embed = discord.Embed(color=discord.Color.red())
              for key in tmp[1]:
                  level=str(tmp[1][key]["playerLevel"])
                  rank=tmp[1][key]["sz_rank"]+"("+str(tmp[1][key]["iRankedPoint"])+"點)"
                  WLandWin=str(tmp[1][key]["iNumberOfWins"])  #+"/敗:"+str(tmp[0][key]["iNumberOfGames"]-tmp[0][key]["iNumberOfWins"])
                  rankmatchnum=str(tmp[1][key]["iNumberOfGames"])
                  winrate=str(round(tmp[1][key]["iNumberOfWins"]/tmp[1][key]["iNumberOfGames"], 2)*100)
                  #embed.add_field(name="等級:", value=level, inline=True) 
                  #embed.add_field(name="本季排位:", value=rank, inline=True) 
                  #embed.add_field(name="本季排位場次:", value=rankmatchnum+" (勝場:"+WLandWinrate+")", inline=True)
                  embed.add_field(name="[攻擊方]"+Dict_AgentsInfos[key.lower()]["sz_AgentName"], value=f"**➤ 等級:** `{level}`\n**➤ 本季排位:** ` {rank}`\n**➤ 本季排位賽勝場/總場次:** `{WLandWin}/{rankmatchnum} ({winrate}%)`", inline=False)  
              await ctx.followup.send(embed=embed, ephemeral = bonlydisplayself)
           except TypeError:
              await ctx.followup.send("錯誤:對局尚未開始,請等待選角階段結束並確認是否已進入讀取介面", ephemeral = bonlydisplayself)
        except KeyError:
           await ctx.followup.send("對方尚未綁定帳號")
        except RiotAuthenticationError:
            await ctx.followup.send("錯誤:找不到帳號資料,請確認帳號資料是否正確,或是否更動過", ephemeral = bonlydisplayself)
        except RiotMultifactorError:
            await ctx.followup.send(f'[二次驗證錯誤]:不支援有使用二次驗證的帳戶,目前正在開發中', ephemeral = bonlydisplayself)
    """

async def setup(bot):
    # finally, adding the cog to the bot
    await bot.add_cog(ValorantCog(bot=bot))

async def cog_load(self):
    print(f"{self.__class__.__name__} loaded!")

async def cog_unload(self):
    print(f"{self.__class__.__name__} unloaded!")
