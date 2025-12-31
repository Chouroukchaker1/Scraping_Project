#!/usr/bin/env python3
"""Fix excessive indentation in pnud.py"""

import re

def fix_indentation(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    fixed_lines = []
    for i, line in enumerate(lines, 1):
        # Skip empty lines
        if not line.strip():
            fixed_lines.append(line)
            continue

        # Count leading spaces
        leading_spaces = len(line) - len(line.lstrip())

        # If more than 12 spaces (3 levels of indentation), reduce to appropriate level
        if leading_spaces >= 16:
            # Likely should be 8 spaces (2 levels)
            new_line = '        ' + line.lstrip()
            print(f"Line {i}: {leading_spaces} spaces -> 8 spaces")
            fixed_lines.append(new_line)
        else:
            fixed_lines.append(line)

    # Write fixed content
    with open(filename, 'w', encoding='utf-8') as f:
        f.writelines(fixed_lines)

    print(f"\n✅ Fixed {filename}")

if __name__ == '__main__':
    fix_indentation('pnud.py')
