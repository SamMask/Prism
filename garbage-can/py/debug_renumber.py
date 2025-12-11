import re

content = "**版本**: v2.0.0"
def update_version_string(match):
    full_str = match.group(0)
    major = int(match.group(1))
    rest = match.group(2)
    print(f"Matched: {full_str}, Major: {major}, Rest: {rest}")
    
    if major == 2:
        return f"v1{rest}"
    elif major == 1:
        return f"v0{rest}"
    else:
        return full_str

new_content = re.sub(r'v(\d+)(\.[0-9]+(?:\.[0-9]+)?)', update_version_string, content)
print(f"Result: {new_content}")
