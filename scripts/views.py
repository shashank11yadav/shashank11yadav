"""Read a komarev.com counter badge (SVG) on stdin and print the view count."""
import re
import sys

numbers = re.findall(r">\s*([\d,]+)\s*<", sys.stdin.read())
if not numbers:
    sys.exit("no view count found in the counter badge")
print(numbers[-1].replace(",", ""))
