import os
import sys
import re
import pandas as pd
from pdfrw import PdfReader, PdfWriter, PdfName, PdfDict, PdfObject
from tkinter import Tk
from tkinter.filedialog import askopenfilename, asksaveasfilename


# ── Bundle path helper ────────────────────────────────────────────────────────

def resource_path(relative_path):
    """Get absolute path to resource, works for dev and PyInstaller .exe"""
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), relative_path)


# ── Helpers ───────────────────────────────────────────────────────────────────

def split_text_for_pdf(text, max_len=100):
    """Split text into up to 3 word-boundary chunks for PDF fields."""
    chunks, remaining = [], text.strip()
    for _ in range(3):
        if len(remaining) <= max_len:
            chunks.append(remaining)
            remaining = ""
        else:
            pos = remaining.rfind(" ", 0, max_len)
            pos = pos if pos != -1 else max_len
            chunks.append(remaining[:pos].rstrip())
            remaining = remaining[pos:].lstrip()
    return (chunks + ["", "", ""])[:3]


def time_to_24hr_code(time_str):
    """Convert '9-10 AM' style string to a 4-digit code like '0910'."""
    m = re.match(r"(\d+)\s*-\s*(\d+)\s*(AM|PM)", time_str.strip(), re.IGNORECASE)
    if not m:
        return None
    start, end, period = int(m[1]), int(m[2]), m[3].upper()
    if period == "AM":
        start = 0 if start == 12 else start
        end   = 0 if end   == 12 else end
    else:
        start = start if start == 12 else start + 12
        end   = end   if end   == 12 else end   + 12
    return f"{start:02d}{end:02d}"


def set_radio_group(pdf, field_name, value):
    """Set a radio button group value across all pages."""
    export = PdfName(value)
    for page in pdf.pages:
        for annot in page.Annots or []:
            if annot.Parent and annot.Parent.T and annot.Parent.T[1:-1] == field_name:
                annot.Parent.V = export
                annot.AS = export


def clean_numeric(val):
    """Return whole numbers without decimals (8.0 → '8'), pass floats through, blank otherwise."""
    try:
        f = float(val)
        return str(int(f)) if f == int(f) else str(f)
    except (ValueError, TypeError):
        return ""


# ── Load & prepare CSV ────────────────────────────────────────────────────────

Tk().withdraw()
file_path = askopenfilename(title="Select Bladder Diary CSV File", filetypes=[("CSV files", "*.csv")])
if not file_path:
    print("User canceled file selection.")
    exit()

df = pd.read_csv(file_path)
df.columns = df.columns.str.strip()
df = df.dropna(how="all")

df = df.rename(columns={
    "Record ID":                                                                    "recordID",
    "Date of Diary":                                                                "date",
    "Hour:":                                                                        "time",
    "What kind of drink? (i.e. juice, water, milk, etc.)":                         "drink",
    "How much was drank (in oz)?":                                                  "dsize",
    "How many times did you use the bathroom?":                                     "trip",
    "How much urine?":                                                              "amount",
    "Accidental Leaks How much urine?":                                             "leak",
    "Did you feel a strong urge to go?":                                            "urge",
    "What were you doing at the time?(i.e. sneezing, lifting, arriving home, sleeping, etc.)": "event",
    "How many pads were used this day?":                                            "pads",
    "How many diapers were used this day?":                                         "diapers",
    "Questions to ask my healthcare team:":                                         "questions",
})

# Build sortable datetime from date + 24-hr start hour
df["time"] = df["time"].astype(str).str.replace("'", "").str.strip() + " " + df["AM or PM"].astype(str).str.strip()
df["trip"] = pd.to_numeric(df["trip"], errors="coerce").fillna(0).astype(int)

start_hours      = df["time"].str.split("-").str[0].str.strip()
df["start_hour"] = pd.to_numeric(start_hours, errors="coerce")
df["is_pm"]      = df["AM or PM"].str.upper() == "PM"
df["start_hour_24"] = df["start_hour"].copy()
df.loc[ df["is_pm"]  & (df["start_hour"] != 12), "start_hour_24"] += 12
df.loc[~df["is_pm"]  & (df["start_hour"] == 12), "start_hour_24"]  = 0

df["Date"]     = pd.to_datetime(df["date"], errors="coerce")
df             = df.dropna(subset=["Date"])
df["DateTime"] = df["Date"] + pd.to_timedelta(df["start_hour_24"], unit="h")

df_sorted = (
    df.sort_values("DateTime")
      .reset_index(drop=True)
      .drop(columns=["start_hour", "is_pm", "start_hour_24", "DateTime", "Date", "AM or PM"])
)


# ── Fill PDFs ─────────────────────────────────────────────────────────────────

# Use resource_path so the bundled PDF is found inside the .exe
template_pdf_path = resource_path("NIHdiary(editable).pdf")
if not os.path.exists(template_pdf_path):
    print(f"Template PDF not found: {template_pdf_path}")
    exit()

df = df_sorted.copy()
df.columns = df.columns.str.strip()
df["Date of Diary"] = pd.to_datetime(df["date"])
df["time_full"]     = df["time"]

for col in ["drink", "event", "amount", "leak", "urge", "questions"]:
    if col in df.columns:
        df[col] = df[col].fillna("").astype(str).str.strip()

for col in ["dsize", "trip", "pads", "diapers"]:
    if col in df.columns:
        df[col] = df[col].apply(clean_numeric)

save_path = None

for date, group in df.groupby("Date of Diary"):
    pdf = PdfReader(template_pdf_path)

    # Day-level values
    pads_rows     = group[group["pads"].str.strip()     != ""]
    diapers_rows  = group[group["diapers"].str.strip()  != ""]
    question_rows = group[group["questions"].str.strip() != ""]

    day_pads     = int(float(pads_rows["pads"].iloc[0]))       if not pads_rows.empty     else ""
    day_diapers  = int(float(diapers_rows["diapers"].iloc[0])) if not diapers_rows.empty  else ""
    q_chunks     = split_text_for_pdf(question_rows["questions"].iloc[0]) if not question_rows.empty else ["", "", ""]
    recordID     = f"AMPA-S{int(group['recordID'].iloc[0]):02d}"

    # Row-level fields
    for _, row in group.iterrows():
        code = time_to_24hr_code(row["time_full"])
        if not code:
            continue

        field_map = {
            f"drink{code}":    str(row.get("drink", "")),
            f"dsize{code}":    str(row.get("dsize", "")),
            f"trip{code}":     str(row.get("trip",  "")),
            f"event{code}":    str(row.get("event", "")),
        }
        urge = row.get("urge", "").strip().upper()

        for page in pdf.pages:
            for annot in page.Annots or []:
                if not annot.T:
                    continue
                key = annot.T[1:-1]

                if key in field_map:
                    annot.V, annot.AP = field_map[key], None

                elif key == f"UrgeYes{code}":
                    annot.V = annot.AS = PdfName("Yes" if urge == "YES" else "Off")
                elif key == f"UrgeNo{code}":
                    annot.V = annot.AS = PdfName("Yes" if urge == "NO"  else "Off")

        # Radio buttons
        for col, key_prefix in [("amount", f"amount{code}"), ("leak", f"leak{code}")]:
            val = str(row.get(col, "")).strip()
            if val in ("Small", "Medium", "Large"):
                set_radio_group(pdf, key_prefix, val)

    # Day-level fields
    day_fields = {
        "day_pads":      str(day_pads),
        "day_diapers":   str(day_diapers),
        "healthcare_qs1": q_chunks[0],
        "healthcare_qs2": q_chunks[1],
        "healthcare_qs3": q_chunks[2],
        "date":          row["Date of Diary"].strftime("%m/%d/%Y"),
        "recordID":      recordID,
    }
    for page in pdf.pages:
        for annot in page.Annots or []:
            if annot.T and annot.T[1:-1] in day_fields:
                annot.V, annot.AP = day_fields[annot.T[1:-1]], None

    # Save
    default_name = f"{recordID}_BladderDiary_{date.strftime('%Y%m%d')}.pdf"
    save_path = asksaveasfilename(
        title=f"Save PDF for {date.strftime('%Y-%m-%d')}",
        defaultextension=".pdf",
        initialfile=default_name,
        filetypes=[("PDF files", "*.pdf")],
    )
    if save_path:
        pdf.Root.AcroForm.update(PdfDict(NeedAppearances=PdfObject("true")))
        PdfWriter().write(save_path, pdf)
    else:
        print(f"Skipped saving PDF for {date.strftime('%Y-%m-%d')}")

if save_path:
    csv_path = os.path.join(os.path.dirname(save_path), f"{recordID}_sorted.csv")
    df_sorted.to_csv(csv_path, index=False)

print("All files saved.")
