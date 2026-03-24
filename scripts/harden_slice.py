#!/usr/bin/env python3
"""
Second pass: Fix .slice().arrayMethod() chains where .slice() source could be undefined
Only wraps .slice() when followed by an array method to avoid breaking string.slice()
"""
import re
import os
import glob
import json

SRC_DIR = "/app/frontend/src"
SKIP_DIRS = {"node_modules", "ui", "__tests__", "test"}
SKIP_FILES = {"safeUtils.js", "SafeRender.js", "arraySafety.js", "setupTests.js"}

ARRAY_METHODS_AFTER_SLICE = ["map", "filter", "reduce", "forEach", "find", "findIndex", "some", "every", "reverse", "sort", "join", "flat", "flatMap"]

stats = {"files_modified": 0, "fixes": 0, "details": []}


def fix_slice_chains(filepath):
    """Fix EXPR.slice(...).arrayMethod(...) patterns"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except:
        return False
    
    original = content
    fixes = 0
    
    # Pattern: IDENTIFIER.slice(ARGS).ARRAY_METHOD(
    # But NOT: (EXPR || []).slice(  -- already safe
    # Not: ).slice( -- chained
    for method in ARRAY_METHODS_AFTER_SLICE:
        # Match: identifier_chain.slice(anything).method(
        pattern = r'(?<![)\]|])([\w$]+(?:(?:\?\.|\.)[a-zA-Z_$][\w$]*)*)\.slice\(([^)]*)\)\.' + method + r'\('
        
        def replacer(match):
            nonlocal fixes
            expr = match.group(1)
            slice_args = match.group(2)
            
            # Skip constants (ALL_CAPS)
            if re.match(r'^[A-Z_][A-Z_0-9]+$', expr):
                return match.group(0)
            
            # Check if already wrapped
            # We need to look at the context before the match
            # Simple check: if the expression is already in parentheses with || []
            
            # Add optional chaining for nested properties
            safe_expr = expr
            if '.' in expr and '?.' not in expr:
                parts = expr.split('.')
                if len(parts) >= 2:
                    safe_expr = parts[0] + '?.' + '?.'.join(parts[1:])
            
            fixes += 1
            return f'({safe_expr} || []).slice({slice_args}).{method}('
        
        content = re.sub(pattern, replacer, content)
    
    # Also fix standalone .slice() that feeds into .map/.filter via chaining with .reverse()
    # e.g., expr.slice().reverse().map(
    # Pattern: EXPR.slice(ARGS).reverse().map(
    for method in ["map", "filter", "forEach", "find", "some", "every"]:
        pattern = r'(?<![)\]|])([\w$]+(?:(?:\?\.|\.)[a-zA-Z_$][\w$]*)*)\.slice\(([^)]*)\)\.reverse\(\)\.' + method + r'\('
        
        def replacer2(match):
            nonlocal fixes
            expr = match.group(1)
            slice_args = match.group(2)
            
            safe_expr = expr
            if '.' in expr and '?.' not in expr:
                parts = expr.split('.')
                if len(parts) >= 2:
                    safe_expr = parts[0] + '?.' + '?.'.join(parts[1:])
            
            fixes += 1
            return f'({safe_expr} || []).slice({slice_args}).reverse().{method}('
        
        content = re.sub(pattern, replacer2, content)
    
    # Also fix standalone .slice().forEach() patterns (no chained method after)
    # And standalone .slice(0, N) that are used in iteration contexts
    
    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        stats["files_modified"] += 1
        stats["fixes"] += fixes
        stats["details"].append({
            "file": filepath.replace(SRC_DIR + "/", ""),
            "fixes": fixes
        })
        return True
    return False


def get_all_files():
    files = []
    for ext in ['*.js', '*.jsx']:
        for filepath in glob.glob(os.path.join(SRC_DIR, '**', ext), recursive=True):
            rel_path = os.path.relpath(filepath, SRC_DIR)
            parts = rel_path.split(os.sep)
            if any(skip_dir in parts for skip_dir in SKIP_DIRS):
                continue
            filename = os.path.basename(filepath)
            if filename in SKIP_FILES:
                continue
            files.append(filepath)
    return sorted(files)


def main():
    print("SLICE CHAIN HARDENING - Pass 2")
    print("=" * 40)
    
    files = get_all_files()
    for f in files:
        fix_slice_chains(f)
    
    print(f"Files modified: {stats['files_modified']}")
    print(f"Total fixes: {stats['fixes']}")
    for d in stats['details']:
        print(f"  {d['fixes']} fixes - {d['file']}")


if __name__ == "__main__":
    main()
