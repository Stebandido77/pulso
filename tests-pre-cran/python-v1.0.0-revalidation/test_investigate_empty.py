import pulso
import warnings

warnings.filterwarnings("ignore")

print("=== INVESTIGATING EMPTY DATAFRAMES ===")
# Test the 3 periods that returned (0,0)
empty_periods = [(2008, 6), (2013, 6), (2020, 6)]
for year, month in empty_periods:
    try:
        df = pulso.load(year, month, "ocupados", allow_unvalidated=True)
        ncols = len(df.columns)
        cols_preview = list(df.columns)[:5] if ncols > 0 else []
        print(f"{year}-{month:02d}: shape={df.shape}, first_cols={cols_preview}")
        if df.shape == (0, 0):
            print("  -> EMPTY DATAFRAME - possible data availability issue")
    except Exception as e:
        print(f"{year}-{month:02d}: FAIL {type(e).__name__}: {str(e)[:200]}")

print("\n=== CHECK list_available() ===")
try:
    avail = pulso.list_available()
    print(f"list_available type: {type(avail)}")
    if hasattr(avail, "shape"):
        print(f"list_available shape: {avail.shape}")
        print(avail.head(10).to_string())
except Exception as e:
    print(f"list_available FAIL: {type(e).__name__}: {e}")

print("\n=== CHECK list_available for 2008-06, 2013-06, 2020-06 ===")
try:
    avail = pulso.list_available()
    for year, month in empty_periods:
        if hasattr(avail, "iterrows"):
            match = (
                avail[(avail["year"] == year) & (avail["month"] == month)]
                if "year" in avail.columns
                else None
            )
            print(f"{year}-{month:02d}: {match}")
except Exception as e:
    print(f"Filter error: {type(e).__name__}: {e}")
