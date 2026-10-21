from pathlib import Path
import pandas as pd


def _truthy(value) -> bool:
	if value is None:
		return False
	s = str(value).strip()
	if s == "":
		return False
	low = s.lower()
	if low in ("1", "true", "t", "yes", "y"):
		return True
	if low in ("0", "false", "f", "no", "n"):
		return False
	try:
		return float(s) != 0
	except Exception:
		return True


def combine_columns_by_names(df: pd.DataFrame, cols: list) -> None:
	"""Combine a list of columns in-place on `df`.

	The first name in `cols` is the target column that remains; the rest are
	OR-ed into it (truthy semantics). After combining, the other columns are
	dropped from `df`.

	Args:
		df: pandas DataFrame to modify in-place.
		cols: list of column names where cols[0] is the target column.
	"""
	if not isinstance(cols, (list, tuple)) or len(cols) < 2:
		raise ValueError("`cols` must be a list/tuple with at least two column names")

	for c in cols:
		if c not in df.columns:
			raise KeyError(f"Column not found in DataFrame: {c}")

	target = cols[0]
	others = cols[1:]

	# use Series.map via apply to avoid errors when df[cols] isn't a plain DataFrame
	truth_df = df.loc[:, cols].apply(lambda col: col.map(_truthy))
	combined = truth_df.any(axis=1).astype(int)

	df[target] = combined
	df.drop(columns=others, inplace=True)

path = Path("data.csv")


df = pd.read_csv(path)
cols_to_drop = ['ablationdata_pfa',	'applications_pfa',	'detectorsversion',	'grids_pfa', 'rawpositions_pfa',	'sites_pfa',	'visitagsessions_pfa',	'visitagsettings_pfa',	'vvversion', 'id']

df = df.drop(columns=cols_to_drop)

cols_to_combine = df.columns.tolist()
combines = []
to_combine = []
for col in cols_to_combine:
    if len(to_combine) > 0 and col[0] != 'v':
        combines.append(to_combine)
        to_combine = [col]
    else:
        to_combine.append(col)

for l in combines:
	if(len(l) > 1):
		combine_columns_by_names(df, l)

# Save outside the function as requested
df.to_csv("data_combined.csv", index=False)



