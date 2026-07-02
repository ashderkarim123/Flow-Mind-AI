import re

original_key_from_transcript = """-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQDJhy9rIi7xPCob
+kahMJAJqkbCWMQYXQe6XfoD+EgUUw+gSvzpa/OWcF7Dbn5CwEEpkVjl9YQk8g5e
Hs0lWSf4zs3u8cuPVWs4mCgIS4LZoYN4fNTGot2Wf4nTyLrYFouWaoM5XWczkCTb
b+H0KTRSwzSk8bxK3EsvAhaOztX0041ZOffjyaU+4yo4BdhOdU25zRHvDx7rJcLn
jvkXh006gzxQVXk8Nr6jd3zArcLPm/tgZdikeyumuKNO+oVXQLw56zLhGIDDppyV
2fePHGmp7BToZISkjqMf3WX5zuhj6d0H2+C+kKdI43KecrawesGtWHNeVy+7JjnR
ErE/A1SDAgMBAAECggEAU2MV+ljvHo9cBy6Ueg77kpw74h/TqBcaYwGOuYTK4moK
DbPpmXY7GPUPKQN3yAwACoCjTae80YK88jIBhaIx+XAs4uF27qyUDJtc+S2xi3aa
zUitzDFIygSk1ZZ5xX7yrD8PZDWjRcEvlwLg9mP0TAiMqHGEDV/A1kchaV7pRf9k
TW6u3BnSZ/29d0CxZDSoAz3BS2CCHzLiXM2lZzW4CrzhWxsUQ8z+KCku+nmWGEOM
741FlpMB8aUG61Vc5kTeUa4SmSvqUjK3fsrEuo6+ww2e8Vk5wj18W2vZSuwq5VOk
rjiZfR6QT/sNQg2MfTbpouB/ZHt6eZXO3VkkfJzN4QKBgQD7aHjY2+KeNdNafwW4
KGCE2n1AiDHnAtWJCld8RUSQ+4YbO1dRvmP7fLrivXAq2yELfP+1cc4MuRY4QM2w
LAld1Pswxmq+v93Yy3qURSWRYElVZbPlmKRHqO3CMzyX8qHunZmKgwL/moIW4MCe
b41JRt/n5WD4kRhv5YvSbGAHowKBgQDNNXw+++NIx7RabjUajmgVrPavpXvxzRZT
1m3UTCPJjrMT7oFBGYasUEQ8N1Fk5xoQAh220tnACC0ojJCzUatR0IMLZV78vNp7
jDvBPwJHZfesh+d22YLH8fFKMD42IKBm5Qw49epuYKY7tqVBYgk4xiN7+e2jqE6c
nHMGeYvNoQKBgGmoi3lgWApzxqK21ZmC5qWPCarQUmCrEUEp5oCkv99Kxh61vsnt
ASoVTpmyUezA8U9ZtkH0VUuFkfAMVCWhLEKSGwtxqDUIf9z4D0k3EkXZuJg6SPPK
ReiT93Bxhhq57xJQi9Hpo532uouQ44LykOdl8P4NqcZtfF6ykyPZRjaPAoGAMH7z
Xe8pR4nqlXR2GFCPSJAXvGrfX8WYATgrvIBB9OBEcfFrmnbt3MsbVR+9nJsBDcdy
PkKWM0u7YFnX2Ij0c+FTFt5eFFyNRaVeeczqPPVcEuoLSYsd3SLQYzgDe8c6IRcA
THXRcURmBLalV05T35bzy9jE0Gh2K4zNojoXUAECgYEAgj1NWbt0wXU9zyoOXd2l
XzZ5K6lfTgUS29xJg+ywHKsfBg7r5c7Xv/ROggCf7sZ9foyiDTIi3Kxtb3Efjdyc
jrxIy0J4dEImTOnhNAXh5dYFJTz3JMGng/yJG07m3SqvZIUE3aP9dMyS6Qa4I9dz
q9+OfbKWFgoR6rlV8HuFjmM=
-----END PRIVATE KEY-----"""

env_path = r"D:\FYP I Flowmind AI\Flowmind AI\Flowmind AI Final\backend\.env"

with open(env_path, "r", encoding="utf-8") as f:
    text = f.read()

text = re.sub(r'FIREBASE_PRIVATE_KEY=".*?"', 'FIREBASE_PRIVATE_KEY="{}"'.format(original_key_from_transcript.replace('\n', '\\n')), text, flags=re.DOTALL)

with open(env_path, "w", encoding="utf-8") as f:
    f.write(text)
print("replaced!")
