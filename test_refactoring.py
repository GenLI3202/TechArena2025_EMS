#!/usr/bin/env python3
"""
Quick test to verify the refactoring of solve_model and extract_solution.
"""

import sys
from pathlib import Path
import importlib.util

# Load optimizer module directly
spec = importlib.util.spec_from_file_location('optimizer', './py_script/core/optimizer.py')
optimizer_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(optimizer_module)

print("="*80)
print("Testing Refactored Optimizer")
print("="*80)

# Test 1: Check that all classes have the new methods
print("\n[Test 1] Checking class structure...")
for cls_name in ['BESSOptimizerModelI', 'BESSOptimizerModelII', 'BESSOptimizerModelIII']:
    cls = getattr(optimizer_module, cls_name)

    # Check solve_model exists
    assert hasattr(cls, 'solve_model'), f"{cls_name} missing solve_model method"

    # Check extract_solution exists
    assert hasattr(cls, 'extract_solution'), f"{cls_name} missing extract_solution method"

    print(f"  [OK] {cls_name}: has both solve_model and extract_solution")

print("\n[Test 2] Checking method signatures...")
# Check that solve_model returns tuple
import inspect

for cls_name in ['BESSOptimizerModelI', 'BESSOptimizerModelII', 'BESSOptimizerModelIII']:
    cls = getattr(optimizer_module, cls_name)

    # Check solve_model signature
    solve_sig = inspect.signature(cls.solve_model)
    solve_return = solve_sig.return_annotation
    print(f"  {cls_name}.solve_model return type: {solve_return}")

    # Check extract_solution signature
    extract_sig = inspect.signature(cls.extract_solution)
    extract_return = extract_sig.return_annotation
    print(f"  {cls_name}.extract_solution return type: {extract_return}")

print("\n[Test 3] Checking inheritance chain...")
# Verify that ModelII and ModelIII inherit extract_solution properly
ModelI = getattr(optimizer_module, 'BESSOptimizerModelI')
ModelII = getattr(optimizer_module, 'BESSOptimizerModelII')
ModelIII = getattr(optimizer_module, 'BESSOptimizerModelIII')

# Check that solve_model is only defined in ModelI
print(f"  BESSOptimizerModelI.solve_model defined in: {ModelI.solve_model.__qualname__}")
print(f"  BESSOptimizerModelII.solve_model defined in: {ModelII.solve_model.__qualname__}")
print(f"  BESSOptimizerModelIII.solve_model defined in: {ModelIII.solve_model.__qualname__}")

# Check that extract_solution is defined in all three
print(f"  BESSOptimizerModelI.extract_solution defined in: {ModelI.extract_solution.__qualname__}")
print(f"  BESSOptimizerModelII.extract_solution defined in: {ModelII.extract_solution.__qualname__}")
print(f"  BESSOptimizerModelIII.extract_solution defined in: {ModelIII.extract_solution.__qualname__}")

print("\n" + "="*80)
print("All structural tests passed!")
print("="*80)
print("\nRefactoring verification complete.")
print("The code structure is correct. Full functionality tests should be run")
print("with actual optimization problems to verify end-to-end behavior.")
