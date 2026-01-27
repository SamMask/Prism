import glob
import os

files = ['000.txt'] + glob.glob('garbage-can/007*.md') + glob.glob('garbage-can/006*.md')
outfile = 'temp_content_dump.txt'

with open(outfile, 'w', encoding='utf-8') as out:
    for f in files:
        if os.path.exists(f):
            out.write(f"\n\n========== START FILE: {f} ==========\n\n")
            try:
                with open(f, 'r', encoding='utf-8', errors='replace') as infile:
                    out.write(infile.read())
            except Exception as e:
                out.write(f"Error reading {f}: {e}")
            out.write(f"\n\n========== END FILE: {f} ==========\n\n")
        else:
            out.write(f"\nFile not found: {f}\n")

print("Done writing to", outfile)
