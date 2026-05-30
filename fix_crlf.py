import glob
import os

files = glob.glob("*.sh") + glob.glob("docker/*.sh")
for f in files:
    with open(f, "rb") as file:
        content = file.read()
    content = content.replace(b"\r\n", b"\n")
    with open(f, "wb") as file:
        file.write(content)
print("Fixed CRLF line endings for all shell scripts.")
