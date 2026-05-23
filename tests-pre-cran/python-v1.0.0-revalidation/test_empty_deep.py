import pulso
import warnings
import traceback

# Don't filter warnings so we see everything
print("=== DEEP INVESTIGATION: Empty DataFrames ===")

# Test one with verbose output
for year, month in [(2008, 6), (2013, 6), (2020, 6)]:
    print(f"\n--- {year}-{month:02d} ---")
    try:
        # Try load without allow_unvalidated first
        try:
            df = pulso.load(year, month, "ocupados")
            print(f"  strict load: shape={df.shape}")
        except Exception as e1:
            print(f"  strict load FAIL: {type(e1).__name__}: {e1}")

        # Now with allow_unvalidated=True
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            df = pulso.load(year, month, "ocupados", allow_unvalidated=True)
            print(f"  unvalidated load: shape={df.shape}")
            for warning in w:
                print(f"  WARNING: {warning.message}")
    except Exception as e:
        print(f"  EXCEPTION: {type(e).__name__}: {e}")
        traceback.print_exc()

# Also check different modules for these periods
print("\n=== Testing different modules for 2008-06 ===")
modules = [
    "ocupados",
    "desocupados",
    "caracteristicas_generales",
    "vivienda_hogares",
    "inactivos",
    "otros_ingresos",
]
for mod in modules:
    try:
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            df = pulso.load(2008, 6, mod, allow_unvalidated=True)
            print(f"  2008-06 {mod}: shape={df.shape}")
    except Exception as e:
        print(f"  2008-06 {mod}: FAIL {type(e).__name__}: {e}")

# Check the cache to see what's being downloaded
print("\n=== Cache info ===")
try:
    ci = pulso.cache_info()
    print(f"cache_info: {ci}")
except Exception as e:
    print(f"cache_info FAIL: {type(e).__name__}: {e}")

try:
    cp = pulso.cache_path()
    print(f"cache_path: {cp}")
    import os

    # List files in cache path related to 2008-06
    for root, dirs, files in os.walk(cp):
        for f in files:
            if "2008" in f or "2013" in f or "2020" in f:
                full = os.path.join(root, f)
                size = os.path.getsize(full)
                print(f"  cached: {full} ({size} bytes)")
except Exception as e:
    print(f"cache inspection FAIL: {type(e).__name__}: {e}")
