import json
import sys

json_str = """
[
  {
    "domain": ".youtube.com",
    "expirationDate": 1795798431.851903,
    "hostOnly": false,
    "httpOnly": true,
    "name": "VISITOR_PRIVACY_METADATA",
    "path": "/",
    "sameSite": "no_restriction",
    "secure": true,
    "session": false,
    "storeId": "0",
    "value": "CgJFRxIEGgAgGw%3D%3D"
  },
  {
    "domain": ".youtube.com",
    "expirationDate": 1795798431.851796,
    "hostOnly": false,
    "httpOnly": true,
    "name": "VISITOR_INFO1_LIVE",
    "path": "/",
    "sameSite": "no_restriction",
    "secure": true,
    "session": false,
    "storeId": "0",
    "value": "ponOldQCOoE"
  },
  {
    "domain": ".youtube.com",
    "expirationDate": 1796412547.233186,
    "hostOnly": false,
    "httpOnly": true,
    "name": "LOGIN_INFO",
    "path": "/",
    "sameSite": "no_restriction",
    "secure": true,
    "session": false,
    "storeId": "0",
    "value": "AFmmF2swRQIhANVN1SVVFrPP60amkbWLL8mHPDdgbwHlMM5AKwe15qFBAiB5O1Ho3k6pp2Z95gi926ujgG1HNnT_j6JWlKC7n6O92w:QUQ3MjNmeGVuZDBBTi01SzRVcDZtcXR1dkNQRmVHTHV5aWUzc0NDWkNFQlI1S2NZT2J1YThhUGw3WGtPVVFpSDY2eDhIeDUtV2syX3R0TUhUcDBFUUN6a1RaQktTaVBxR3IxZm5qbFBNUW1pMzhXM1BzLUo0LXl3VXpSTl93ZzR6SmxBbk5CMzBsSDN6VVgxZzB4NzZDNHZoNmQ1SHB2cjNn"
  },
  {
    "domain": ".youtube.com",
    "expirationDate": 1791476844.130088,
    "hostOnly": false,
    "httpOnly": true,
    "name": "__Secure-BUCKET",
    "path": "/",
    "sameSite": "lax",
    "secure": true,
    "session": false,
    "storeId": "0",
    "value": "CLED"
  },
  {
    "domain": ".youtube.com",
    "expirationDate": 1787071029,
    "hostOnly": false,
    "httpOnly": false,
    "name": "_gcl_au",
    "path": "/",
    "sameSite": "unspecified",
    "secure": false,
    "session": false,
    "storeId": "0",
    "value": "1.1.1915891484.1779295029"
  },
  {
    "domain": ".youtube.com",
    "expirationDate": 1814796378.796421,
    "hostOnly": false,
    "httpOnly": false,
    "name": "SID",
    "path": "/",
    "sameSite": "unspecified",
    "secure": false,
    "session": false,
    "storeId": "0",
    "value": "g.a000-ghH4nYSVsWyY1wHb6gXq3F1BoRAG2KT7H24jezzFtSlTl-No1Fj7IWjh3kSbF8XqPhKHAACgYKAQUSARESFQHGX2Mi7Nq5SVvinlYfT96sH_oJKBoVAUF8yKqgrRJGXqE8UdecnQlte-880076"
  },
  {
    "domain": ".youtube.com",
    "expirationDate": 1814796378.796657,
    "hostOnly": false,
    "httpOnly": true,
    "name": "__Secure-1PSID",
    "path": "/",
    "sameSite": "unspecified",
    "secure": true,
    "session": false,
    "storeId": "0",
    "value": "g.a000-ghH4nYSVsWyY1wHb6gXq3F1BoRAG2KT7H24jezzFtSlTl-N2NWbkUhr6Lz-I3uB9gKepAACgYKAakSARESFQHGX2MirRIPg0x9CSFFX7pOFzk37hoVAUF8yKrLPywxoDzV45H5xlK1kdwf0076"
  },
  {
    "domain": ".youtube.com",
    "expirationDate": 1814796378.796707,
    "hostOnly": false,
    "httpOnly": true,
    "name": "__Secure-3PSID",
    "path": "/",
    "sameSite": "no_restriction",
    "secure": true,
    "session": false,
    "storeId": "0",
    "value": "g.a000-ghH4nYSVsWyY1wHb6gXq3F1BoRAG2KT7H24jezzFtSlTl-NKNMkoQXCRNnUvzlqnoiA6AACgYKAagSARESFQHGX2MiZwtoIEtlAiTrJHLXH6xWohoVAUF8yKr0Nob93udE3cNXQ2NrMHok0076"
  },
  {
    "domain": ".youtube.com",
    "expirationDate": 1814796378.796756,
    "hostOnly": false,
    "httpOnly": true,
    "name": "HSID",
    "path": "/",
    "sameSite": "unspecified",
    "secure": false,
    "session": false,
    "storeId": "0",
    "value": "A8xu33Sdno9k3oH0D"
  },
  {
    "domain": ".youtube.com",
    "expirationDate": 1814796378.796804,
    "hostOnly": false,
    "httpOnly": true,
    "name": "SSID",
    "path": "/",
    "sameSite": "unspecified",
    "secure": true,
    "session": false,
    "storeId": "0",
    "value": "AwusqDUTxs39Q6evP"
  },
  {
    "domain": ".youtube.com",
    "expirationDate": 1814796378.796852,
    "hostOnly": false,
    "httpOnly": false,
    "name": "APISID",
    "path": "/",
    "sameSite": "unspecified",
    "secure": false,
    "session": false,
    "storeId": "0",
    "value": "zKMXVfn-hl1dCRpv/AQ7F4uPfLxedd0TNT"
  },
  {
    "domain": ".youtube.com",
    "expirationDate": 1814796378.796906,
    "hostOnly": false,
    "httpOnly": false,
    "name": "SAPISID",
    "path": "/",
    "sameSite": "unspecified",
    "secure": true,
    "session": false,
    "storeId": "0",
    "value": "GV-IOqmCrkN04GJU/Au61zRvqJEjZ0UPDh"
  },
  {
    "domain": ".youtube.com",
    "expirationDate": 1814796378.796957,
    "hostOnly": false,
    "httpOnly": false,
    "name": "__Secure-1PAPISID",
    "path": "/",
    "sameSite": "unspecified",
    "secure": true,
    "session": false,
    "storeId": "0",
    "value": "GV-IOqmCrkN04GJU/Au61zRvqJEjZ0UPDh"
  },
  {
    "domain": ".youtube.com",
    "expirationDate": 1814796378.79701,
    "hostOnly": false,
    "httpOnly": false,
    "name": "__Secure-3PAPISID",
    "path": "/",
    "sameSite": "no_restriction",
    "secure": true,
    "session": false,
    "storeId": "0",
    "value": "GV-IOqmCrkN04GJU/Au61zRvqJEjZ0UPDh"
  },
  {
    "domain": ".youtube.com",
    "expirationDate": 1814804645.522944,
    "hostOnly": false,
    "httpOnly": false,
    "name": "PREF",
    "path": "/",
    "sameSite": "unspecified",
    "secure": true,
    "session": false,
    "storeId": "0",
    "value": "f7=44100&tz=Africa.Cairo&repeat=NONE&guide_collapsed=false&autoplay=true&volume=100"
  },
  {
    "domain": ".youtube.com",
    "expirationDate": 1811782267.441136,
    "hostOnly": false,
    "httpOnly": true,
    "name": "__Secure-1PSIDTS",
    "path": "/",
    "sameSite": "unspecified",
    "secure": true,
    "session": false,
    "storeId": "0",
    "value": "sidts-CjQBhkeRdxjlsyDHhGda2qjewbBCYyQaD7xoWb7HIJ9Zw1-dNbm3I_b-lEdPambeno1rQ_U0EAA"
  },
  {
    "domain": ".youtube.com",
    "expirationDate": 1811782267.441298,
    "hostOnly": false,
    "httpOnly": true,
    "name": "__Secure-3PSIDTS",
    "path": "/",
    "sameSite": "no_restriction",
    "secure": true,
    "session": false,
    "storeId": "0",
    "value": "sidts-CjQBhkeRdxjlsyDHhGda2qjewbBCYyQaD7xoWb7HIJ9Zw1-dNbm3I_b-lEdPambeno1rQ_U0EAA"
  },
  {
    "domain": ".youtube.com",
    "expirationDate": 1795798428.889738,
    "hostOnly": false,
    "httpOnly": true,
    "name": "__Secure-YNID",
    "path": "/",
    "sameSite": "no_restriction",
    "secure": true,
    "session": false,
    "storeId": "0",
    "value": "18.YT=C2psyKbS1H3CJtuUaxsBvsbp5i3KX718nTSzqYMp8sCuz9-g0W-wfE1DWWXulp5MqifTyd1M4qIBI1nPNe_pdU4xovQS200bwlTcjY8Pcc9wGzIUUeQZVUn0s9RxCW3DdViB1lWhuMHxvHZvyiY6xh7m6WMGYpo_azPcd6Kmo9NOeturxD4LnBSRtU-hYpeWgKoCcgKxbm9dKJN2dk4L-Wdl-f80bCxCxJQOL9YMkCoy9DgP6G6tGXcT81InnwK5rdX_11cyFWn3phdBDpyEQ51hOvSu4kpKzI6nV1ewnGbacQxjnf9s3RDxVtXe_tmo2eEVGdE32pW4VQ224WsNjw"
  },
  {
    "domain": ".youtube.com",
    "hostOnly": false,
    "httpOnly": true,
    "name": "YSC",
    "path": "/",
    "sameSite": "no_restriction",
    "secure": true,
    "session": true,
    "storeId": "0",
    "value": "rBpVXzQULuI"
  },
  {
    "domain": ".youtube.com",
    "expirationDate": 1811782729.536215,
    "hostOnly": false,
    "httpOnly": false,
    "name": "SIDCC",
    "path": "/",
    "sameSite": "unspecified",
    "secure": false,
    "session": false,
    "storeId": "0",
    "value": "AKEyXzWib0hCxCu2gVQDj2xYSPE1iH87b2so8i-Knp2uYDasrwXYA-ByK-Ae4X2l47LfpRBIrJUm"
  },
  {
    "domain": ".youtube.com",
    "expirationDate": 1811782729.536329,
    "hostOnly": false,
    "httpOnly": true,
    "name": "__Secure-1PSIDCC",
    "path": "/",
    "sameSite": "unspecified",
    "secure": true,
    "session": false,
    "storeId": "0",
    "value": "AKEyXzXy2hzCOOhOC6vTfgteM4mJzoNeg15eDA83XxvBG-ToqzgffJH7sIQ75n3DCqlH65seW5gp"
  },
  {
    "domain": ".youtube.com",
    "expirationDate": 1811782729.536401,
    "hostOnly": false,
    "httpOnly": true,
    "name": "__Secure-3PSIDCC",
    "path": "/",
    "sameSite": "no_restriction",
    "secure": true,
    "session": false,
    "storeId": "0",
    "value": "AKEyXzUC4bmZuIxvU74U8rrQX_E4STkXogl87RETl14RAAc0bhnBwMlnkhmuhgf9ZEW5l60nXhA"
  }
]
"""

cookies = json.loads(json_str)
with open('cookies.txt', 'w') as f:
    f.write('# Netscape HTTP Cookie File\n')
    f.write('# http://curl.haxx.se/rfc/cookie_spec.html\n')
    f.write('# This is a generated file!  Do not edit.\n\n')
    
    for cookie in cookies:
        domain = cookie.get('domain', '')
        include_subdomains = 'TRUE' if domain.startswith('.') else 'FALSE'
        path = cookie.get('path', '/')
        secure = 'TRUE' if cookie.get('secure', False) else 'FALSE'
        
        # Expiry
        if 'expirationDate' in cookie:
            expiry = str(int(cookie['expirationDate']))
        else:
            expiry = '0'
            
        name = cookie.get('name', '')
        value = cookie.get('value', '')
        
        f.write(f"{domain}\t{include_subdomains}\t{path}\t{secure}\t{expiry}\t{name}\t{value}\n")
        
print("Converted successfully to cookies.txt!")
