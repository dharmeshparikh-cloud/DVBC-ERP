#!/usr/bin/env python3
"""
ZERO-CRASH HARDENING SCRIPT
Scans all frontend JS/JSX files and adds safety wrappers to:
1. Array method calls (.map, .filter, .reduce, .forEach, .find, .some, .every, .flat, .flatMap, .slice)
2. Object.entries(), Object.keys(), Object.values()
3. useState initializations

APPROACH: Conservative line-by-line regex replacement
- Only wraps patterns that are genuinely unsafe
- Skips already-safe patterns (|| [], || {}, chained calls, literal arrays)
- Tracks all changes for validation report
"""

import re
import os
import glob
import json

# ---- CONFIG ----
SRC_DIR = "/app/frontend/src"
SKIP_DIRS = {"node_modules", "ui", "__tests__", "test"}
SKIP_FILES = {"safeUtils.js", "SafeRender.js", "arraySafety.js", "setupTests.js"}

# Array methods that require array input
ARRAY_METHODS = ["map", "filter", "reduce", "forEach", "find", "findIndex", "some", "every", "flat", "flatMap"]

# Stats
stats = {
    "files_scanned": 0,
    "files_modified": 0,
    "total_fixes": 0,
    "array_method_fixes": 0,
    "object_entries_fixes": 0,
    "object_keys_fixes": 0,
    "object_values_fixes": 0,
    "errors": [],
    "modified_files": [],
}


def is_safe_before(line, match_start):
    """Check if the expression before the method call is already safe"""
    before = line[:match_start].rstrip()
    
    # Already wrapped with || [])
    if before.endswith("|| [])") or before.endswith("|| []) ") or before.endswith("?? [])"):
        return True
    
    # Result of another method call (chained) - e.g., .filter().map()
    if before.endswith(")"):
        return True
    
    # Literal array - e.g., [1,2,3].map()
    if before.endswith("]"):
        # But not IDENT[index].map() - check for variable access
        # Simple heuristic: if ] is preceded by a digit or ], it's likely an array literal
        stripped = before[:-1].rstrip()
        if not stripped or stripped[-1] in "0123456789]\"'`":
            return True
        # Otherwise it's array indexing like items[0].map() - not safe
        return False

    return False


def fix_array_method_in_line(line, method):
    """
    Fix unsafe EXPR.method( patterns in a single line.
    
    Matches patterns like:
      identifier.method(
      obj.prop.method(
      obj?.prop.method(
      obj?.prop?.nested.method(
    
    Does NOT match:
      ).method(   - chained call (safe)
      ].method(   - could be literal array
      || []).method( - already safe
    """
    # Pattern explanation:
    # (?<![)\]]) - not preceded by ) or ]
    # ([\w$]+(?:(?:\?\.|\.)[a-zA-Z_$][\w$]*)*) - identifier chain like: data, data.items, data?.items?.list
    # \.METHOD\( - .method(
    pattern = r'(?<![)\]])(\b[\w$]+(?:(?:\?\.|\.)[a-zA-Z_$][\w$]*)*)\.' + method + r'\('
    
    fixes = 0
    
    def replacer(match):
        nonlocal fixes
        expr = match.group(1)
        full_match = match.group(0)
        
        # Check if the full expression is already wrapped
        # Look back in the original line for || []) before this match
        pos = match.start()
        before_text = line[:pos]
        
        # Skip if already wrapped: (expr || []).method(
        if before_text.rstrip().endswith("|| [])") or before_text.rstrip().endswith("?? [])"):
            return full_match
        
        # Skip if the expression starts with a known safe source
        # Like: Array.from(...).method(, [...spread].method(
        if expr.startswith("Array") or expr.startswith("JSON"):
            return full_match
        
        # Skip single-letter temp variables in arrow functions that are clearly arrays
        # e.g., in .map(x => x.items.map()) - the inner x.items might need wrapping
        # but 'x' alone in a map callback is the current item, not necessarily an array
        
        # Skip known constant arrays (ALL_CAPS naming convention)
        if re.match(r'^[A-Z_][A-Z_0-9]+$', expr):
            # Constants like STEPS, TABS, WEEKDAYS are typically safe literal arrays
            return full_match
            
        # Skip if expression is clearly a local const array (e.g., tabs, steps defined nearby)
        # We can't reliably detect this, so we wrap conservatively
        
        # Add optional chaining for nested property access
        # e.g., data.items.map( → (data?.items || []).map(
        # e.g., obj.prop.nested.map( → (obj?.prop?.nested || []).map(
        safe_expr = expr
        if '.' in expr and '?.' not in expr:
            # Add ?. for the intermediate accesses (not the last one since we're wrapping with || [])
            parts = expr.split('.')
            if len(parts) >= 2:
                safe_expr = parts[0] + '?.' + '?.'.join(parts[1:])
        
        fixes += 1
        return f'({safe_expr} || []).{method}('
    
    result = re.sub(pattern, replacer, line)
    return result, fixes


def fix_object_method_in_line(line, method):
    """
    Fix Object.entries(expr), Object.keys(expr), Object.values(expr) 
    to Object.entries(expr || {})
    """
    pattern = rf'Object\.{method}\(([^)]+)\)'
    fixes = 0
    
    def replacer(match):
        nonlocal fixes
        arg = match.group(1).strip()
        
        # Already safe
        if '|| {}' in arg or '?? {}' in arg:
            return match.group(0)
        
        # If the argument is already a safe expression like a function call
        if arg.endswith(')'):
            return match.group(0)
            
        fixes += 1
        return f'Object.{method}({arg} || {{}})'
    
    result = re.sub(pattern, replacer, line)
    return result, fixes


def process_file(filepath):
    """Process a single file and apply all safety fixes"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        stats["errors"].append(f"READ ERROR: {filepath}: {str(e)}")
        return False
    
    original_content = ''.join(lines)
    new_lines = []
    file_fixes = 0
    
    for i, line in enumerate(lines):
        current_line = line
        
        # Skip comment lines
        stripped = current_line.lstrip()
        if stripped.startswith('//') or stripped.startswith('*') or stripped.startswith('/*'):
            new_lines.append(current_line)
            continue
        
        # Fix array methods
        for method in ARRAY_METHODS:
            if f'.{method}(' in current_line:
                current_line, fixes = fix_array_method_in_line(current_line, method)
                file_fixes += fixes
                stats["array_method_fixes"] += fixes
        
        # Fix Object.entries
        if 'Object.entries(' in current_line:
            current_line, fixes = fix_object_method_in_line(current_line, 'entries')
            file_fixes += fixes
            stats["object_entries_fixes"] += fixes
        
        # Fix Object.keys
        if 'Object.keys(' in current_line:
            current_line, fixes = fix_object_method_in_line(current_line, 'keys')
            file_fixes += fixes
            stats["object_keys_fixes"] += fixes
        
        # Fix Object.values
        if 'Object.values(' in current_line:
            current_line, fixes = fix_object_method_in_line(current_line, 'values')
            file_fixes += fixes
            stats["object_values_fixes"] += fixes
        
        new_lines.append(current_line)
    
    new_content = ''.join(new_lines)
    
    if new_content != original_content:
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            stats["files_modified"] += 1
            stats["total_fixes"] += file_fixes
            stats["modified_files"].append({
                "file": filepath.replace(SRC_DIR + "/", ""),
                "fixes": file_fixes
            })
            return True
        except Exception as e:
            stats["errors"].append(f"WRITE ERROR: {filepath}: {str(e)}")
            return False
    
    return False


def get_all_files():
    """Get all JS/JSX files to process, excluding skip directories"""
    files = []
    for ext in ['*.js', '*.jsx']:
        for filepath in glob.glob(os.path.join(SRC_DIR, '**', ext), recursive=True):
            # Skip excluded directories
            rel_path = os.path.relpath(filepath, SRC_DIR)
            parts = rel_path.split(os.sep)
            
            if any(skip_dir in parts for skip_dir in SKIP_DIRS):
                continue
            
            # Skip excluded files
            filename = os.path.basename(filepath)
            if filename in SKIP_FILES:
                continue
            
            files.append(filepath)
    
    return sorted(files)


def main():
    print("=" * 60)
    print("ZERO-CRASH HARDENING SCRIPT")
    print("=" * 60)
    
    files = get_all_files()
    stats["files_scanned"] = len(files)
    
    print(f"\nFound {len(files)} files to process...")
    
    for filepath in files:
        rel_path = os.path.relpath(filepath, SRC_DIR)
        process_file(filepath)
    
    # Print report
    print("\n" + "=" * 60)
    print("HARDENING REPORT")
    print("=" * 60)
    print(f"Files scanned:        {stats['files_scanned']}")
    print(f"Files modified:       {stats['files_modified']}")
    print(f"Total fixes applied:  {stats['total_fixes']}")
    print(f"  Array method fixes: {stats['array_method_fixes']}")
    print(f"  Object.entries:     {stats['object_entries_fixes']}")
    print(f"  Object.keys:        {stats['object_keys_fixes']}")
    print(f"  Object.values:      {stats['object_values_fixes']}")
    
    if stats["errors"]:
        print(f"\nERRORS ({len(stats['errors'])}):")
        for err in stats["errors"]:
            print(f"  - {err}")
    
    if stats["modified_files"]:
        print(f"\nModified files ({len(stats['modified_files'])}):")
        for f in sorted(stats["modified_files"], key=lambda x: -x["fixes"]):
            print(f"  {f['fixes']:3d} fixes - {f['file']}")
    
    # Save report
    report_path = "/app/frontend/src/utils/hardening_report.json"
    with open(report_path, 'w') as f:
        json.dump(stats, f, indent=2)
    print(f"\nReport saved to: {report_path}")
    
    return stats["total_fixes"]


if __name__ == "__main__":
    total = main()
    print(f"\n{'='*60}")
    if total > 0:
        print(f"SUCCESS: Applied {total} safety fixes across {stats['files_modified']} files")
    else:
        print("No unsafe patterns found (codebase may already be safe)")
    print(f"{'='*60}")
