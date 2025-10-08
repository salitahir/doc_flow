import argparse

import pandas as pd

from docflow.text_clean import clean_text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="input_xlsx", required=True)
    ap.add_argument("--out", dest="out_xlsx", required=True)
    args = ap.parse_args()

    df = pd.read_excel(args.input_xlsx)
    if "text" in df.columns:
        df["text"] = df["text"].astype(str).map(clean_text)
    if "current_section" in df.columns:
        df["current_section"] = df["current_section"].astype(str).map(clean_text)
    if "h1" in df.columns:
        df["h1"] = df["h1"].astype(str).map(clean_text)
    if "h2" in df.columns:
        df["h2"] = df["h2"].astype(str).map(clean_text)
    if "h3" in df.columns:
        df["h3"] = df["h3"].astype(str).map(clean_text)
    if "section_path" in df.columns:
        df["section_path"] = df["section_path"].astype(str).map(clean_text)

    df.to_excel(args.out_xlsx, index=False)
    print(f"Cleaned -> {args.out_xlsx} (rows={len(df)})")


if __name__ == "__main__":
    main()
