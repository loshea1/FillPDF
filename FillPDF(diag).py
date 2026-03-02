import pandas as pd
import re
from pdfrw import PdfReader, PdfWriter, PdfName
from tkinter import Tk
from tkinter.filedialog import askopenfilename, asksaveasfilename

# --- PDF Template ---
template_pdf_path = r"\\fs2.smpp.local\smulab2\STU00224908 - Ampakine Protocol\Bladder Diary\NIHdiary(editable).pdf"

# --- Diagnostic: print all field names ---
pdf = PdfReader(template_pdf_path)
print("=== PDF Field Names Diagnostic ===")
for page_num, page in enumerate(pdf.pages, start=1):
    if hasattr(page, "Annots"):
        for ann in page.Annots or []:
            if ann.T:
                field_name = ann.T[1:-1]
                print(f"Page {page_num}: {field_name}")
print("=== End of PDF Field Names ===\n")

# --- Select CSV File ---
Tk().withdraw()
csv_path = askopenfilename(title="Select Bladder Diary CSV File", filetypes=[("CSV files", "*.csv")])
if not csv_path:
    print("User canceled file selection.")
    exit()

df = pd.read_csv(csv_path)
df.columns = df.columns.str.strip()

# Ensure date is datetime
df["Date of Diary"] = pd.to_datetime(df["Date of Diary"])

# Combine hour and AM/PM into single string if needed
# Adjust these column names to match your CSV
if "Hour" in df.columns and "AM/PM" in df.columns:
    df["time_full"] = df["Hour"].astype(str) + " " + df["AM/PM"]
else:
    df["time_full"] = df["time"]

# --- Convert time to 24-hour code for PDF field naming ---
def time_to_24hr_code(time_str):
    m = re.match(r"(\d+)\s*-\s*(\d+)\s*(AM|PM)", time_str.strip(), re.IGNORECASE)
    if not m:
        return None
    start, end, period = m.groups()
    start, end = int(start), int(end)
    period = period.upper()
    if period == "AM":
        start = 0 if start == 12 else start
        end = 0 if end == 12 else end
    else:
        start = start if start == 12 else start + 12
        end = end if end == 12 else end + 12
    return f"{start:02d}{end:02d}"

# --- Fill PDFs per date ---
for date, group in df.groupby("Date of Diary"):
    pdf = PdfReader(template_pdf_path)  # fresh copy per date

    for _, row in group.iterrows():
        code = time_to_24hr_code(row["time_full"])
        if not code:
            continue

        # PDF field keys
        drink_key = f"drink{code}"
        dsize_key = f"dsize{code}"
        trip_key = f"trip{code}"
        event_key = f"event{code}"
        amount_key = f"amount{code}"
        urge_yes_key = f"UrgeYes{code}"
        urge_no_key = f"UrgeNo{code}"

        for page in pdf.pages:
            for annot in page.Annots or []:
                if not annot.T:
                    continue
                key = annot.T[1:-1]

                # TEXT FIELDS
                if key == drink_key:
                    annot.V = str(row.get("drink", ""))
                    annot.AP = None
                elif key == dsize_key:
                    annot.V = str(row.get("dsize", ""))
                    annot.AP = None
                elif key == trip_key:
                    annot.V = str(row.get("trip", ""))
                    annot.AP = None
                elif key == event_key:
                    annot.V = str(row.get("event", ""))
                    annot.AP = None

                # RADIO BUTTON (Amount)
                elif key == amount_key:
                    value = row.get("amount", "")
                    if value in ["Small", "Medium", "Large"]:
                        annot.V = PdfName(value)
                        annot.AP = None

                # CHECKBOX (Urge Yes/No)
                elif key == urge_yes_key:
                    if row.get("urge", "").strip().upper() == "YES":
                        annot.V = PdfName("Yes")
                        annot.AS = PdfName("Yes")
                    else:
                        annot.V = PdfName("Off")
                        annot.AS = PdfName("Off")
                elif key == urge_no_key:
                    if row.get("urge", "").strip().upper() == "NO":
                        annot.V = PdfName("Yes")
                        annot.AS = PdfName("Yes")
                    else:
                        annot.V = PdfName("Off")
                        annot.AS = PdfName("Off")

    # --- Ask user where to save the PDF ---
    default_name = f"BladderDiary_{date.strftime('%Y%m%d')}.pdf"
    save_path = asksaveasfilename(title=f"Save PDF for {date.strftime('%Y-%m-%d')}",
                                  defaultextension=".pdf",
                                  initialfile=default_name,
                                  filetypes=[("PDF files", "*.pdf")])
    if save_path:
        PdfWriter().write(save_path, pdf)
        print("Saved:", save_path)
    else:
        print(f"Skipped saving PDF for {date.strftime('%Y-%m-%d')}")