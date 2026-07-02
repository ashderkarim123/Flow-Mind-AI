import re

env_path = r"backend\.env"

with open(env_path, "r", encoding="utf-8") as f:
    text = f.read()

# Fix literal newlines in the key
import ast
lines = text.split("\n")
new_lines = []
in_key = False
key_parts = []
for line in lines:
    if line.startswith('FIREBASE_PRIVATE_KEY="-----BEGIN'):
        in_key = True
        key_parts.append(line.replace('FIREBASE_PRIVATE_KEY="', ''))
    elif in_key:
        if line.endswith('"'):
            key_parts.append(line[:-1])
            in_key = False
            new_lines.append('FIREBASE_PRIVATE_KEY="' + '\\n'.join(key_parts) + '"')
        else:
            key_parts.append(line)
    else:
        new_lines.append(line)

with open(env_path, "w", encoding="utf-8") as f:
    f.write("\n".join(new_lines))
print("Fixed newlines!")
