#!/usr/bin/env python3
import numpy as np
import sys

# load saved raw depth if available, otherwise exit:
arr = np.load("depth_raw.npy")    # path from previous diagnostic
h, w = arr.shape
mask_invalid = np.isneginf(arr) | np.isposinf(arr) | np.isnan(arr)

# percent invalid per row and per column
row_pct = 100.0 * mask_invalid.sum(axis=1) / w
col_pct = 100.0 * mask_invalid.sum(axis=0) / h

# print summary
print("Image shape:", arr.shape)
print("Overall invalid:", mask_invalid.sum(), "/", arr.size)
# rows with >1% invalid
print("\nRows with >1% invalid (row_idx -> percent):")
for r,p in enumerate(row_pct):
    if p > 1.0:
        print(f"{r:03d} -> {p:.1f}%")

# first and last row with notable invalids
rows_nonzero = np.where(row_pct > 0.1)[0]
if rows_nonzero.size:
    print(f"\nInvalid rows range: {rows_nonzero[0]} .. {rows_nonzero[-1]}")
else:
    print("No rows with >0.1% invalid")

# optional: save row_pct for plotting
np.savetxt("depth_invalid_row_pct.csv", row_pct, delimiter=",")
np.savetxt("depth_invalid_col_pct.csv", col_pct, delimiter=",")
print("Saved depth_invalid_row_pct.csv and depth_invalid_col_pct.csv")

