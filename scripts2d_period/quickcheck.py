#!/usr/bin/env python3
import pandas as pd
df = pd.read_csv(r"C:\Users\timot\Downloads\Science\src\Unification\vol14\S-Series\S3_GalacticNASA\lake\s3_gaia_luminosity_source.csv", nrows=5)
print(df.columns.tolist())