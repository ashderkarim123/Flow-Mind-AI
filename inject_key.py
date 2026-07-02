import re

first_key = """-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQDJhy9rIi7xPCob
+kahMJAJqkbCWMQYXQe6XfoD+EgUUw+gSvzpa/OWcF7Dbn5CwEEpkVjl9YQk8g5e
BRHItMms061ig/RDHPRfk6mwmByNeF/IDgA/p7/a1WxTqcfUURJb3j6Z3u7eyzuz
h0o9xo4/6C9EiCEXzyChGzic4LRUxxoODXZIbOJHsmxzQIMFFtLc/vrSRLu/3FyE
2z+OVUmfrsW5s1aGhmirVi+Hwx/JbMxUVPI1gutujIJSdwVLxbf418oWz/+4GnOA
ZBrxfKo85dIHudwLohDTkZ36AVKIggEV64hFljMhzh5z4r3Wwv85QtzAFuqdtCxb
2yCZfK1rAgMBAAECggEAStXK9ySPj3Oktj/sB+wK0yoUTTauv+Mys3grcMvo2TGz
cJEwCJrtO8L4NEtNscrqgyq9oRUdY8oZG1kpQbSebZMjcgfoLWmZnxmm4etb6taL
osF7Zdn91K0GMnsx+N8e6gBspMxcOs2s3kWG41OOGC7tNsDlCaFzozJxM0MQnGEu
IXNM7Sos7LWh/QbrTDg3w40JX2zIegRADlgAV1IVxsnMRHAc3mh0blvfMMSwuazP
MxglXA+hDzkjGBg6lZoXmxXdUL8OWdtfd+uCXFQLCm71QVBrfPK8ntM0cGSIEfES
VAzZCgT6lPzRkgGC9WWUdZ7VPShUEUZ/sVjq7iDvhQKBgQD1Bc2XBurCnKF3Ry/x
CrLyisWIF2dhJAPqaaJFlOdocW5j7/VifftjwBYHhKaP6qZhNRc+PcQggAQhVdfZ
0SgOfbvcRLK3s/mFa6dIOBxpOlOJ50JEB+L2KxHXImzq6LG1iRgD2xK4xiCBUtPp
Y1IeF4gRYjTbJuhr9F/0EKipdwKBgQDMic+jVGGCpB32wR5Q4nKsQUYdZTIomzw0
GBr2dLOLJFAt5Vk/E//07HlHBiSAejQuo7SfKnHXOzXtZG25wOHBmuTohCXyFY3X
S7f7VuFlr0PH7rTI0dooMndvifxKvekx58o2XPQR5kC5c5zY9+3VTT9YfCEWCJP6
psddnRkYrQKBgHLXZnX8Avp2KWPblMfYaOkvS8gumAC6va8YFbuhQBj+2Wuz44Jn
Y/Vr6adacCsSIyt6k8tTbeKBve3V61anJqwsGGn0NQPPMgtr2rsJuZ9EfDUtlCyI
ucMBitoXw48Sw4A/ombkPlEmY8PZi4NfTvTVuKvVKMry4IsAvhyJ1lOfAoGAKs9p
Y0ElC6f4EY6IHtvWrpEW8M4eentLVYf6FL2GWsgl9AU98cLo3sWj+KajezSYuW5Q
PsQugaMF/YL4qFljpxcZdEU8f/fc8UQK5RNhJ9xQLoea1TF/HMy7TOAvqyEmruhZ
3ZkFCL4NrAMzwAHciLmbWZTZg/gVqO/BaKmZ+B0CgYBWDC91nygsq5NQcBhDil1g
8QrZjzvEIhzxRJpmBzN58knujmERdae3+oQzxjmtndIudng5eGeJkW/jNp0C1L6s
KJ6/FjfDIGvtsqrsqhdqLI20/W8vczKhou74pipxwgxpZrnKxFgJyiJOSyvwKcls
e7FtPKIRezy+WG1o3WmDxQ==
-----END PRIVATE KEY-----"""

env_path = r"backend\.env"

with open(env_path, "r", encoding="utf-8") as f:
    text = f.read()

# Insert after FIREBASE_PRIVATE_KEY_ID
new_key_line = 'FIREBASE_PRIVATE_KEY="' + first_key.replace('\n', '\\n') + '"\n'

text = re.sub(r'FIREBASE_PRIVATE_KEY_ID=(.*)', r'FIREBASE_PRIVATE_KEY_ID=\1\n' + new_key_line, text)

with open(env_path, "w", encoding="utf-8") as f:
    f.write(text)
print("Injected key!")
