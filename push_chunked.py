
import os
import subprocess

def run(cmd):
    print("Running:", cmd)
    subprocess.run(cmd, shell=True, check=True)

# Prepare branch
run("git checkout -f master")
subprocess.run("git branch -D temp_submit", shell=True)
run("git checkout --orphan temp_submit")
run("git rm -rf . --cached")

# Get files
files = []
for root, dirs, filenames in os.walk("."):
    if ".git" in root or "build" in root or "install" in root or "log" in root:
        continue
    for f in filenames:
        files.append(os.path.join(root, f))

size = 0
count = 0
for f in files:
    if f.endswith(".ps1") or f.endswith(".py") or f.endswith(".sh"):
        continue
    run(f"git add \"{f}\"")
    size += os.path.getsize(f)
    
    if size > 30000000:
        count += 1
        run(f"git commit -m \"chore: upload chunk {count}\"")
        run(f"git push -f -u origin temp_submit:refs/heads/master")
        size = 0

if size > 0:
    count += 1
    run(f"git commit -m \"chore: upload final chunk {count}\"")
    run(f"git push -f -u origin temp_submit:refs/heads/master")

run("git checkout -f master")

