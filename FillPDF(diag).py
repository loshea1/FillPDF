import pandas as pd
import re
from pdfrw import PdfReader, PdfWriter, PdfName, PdfDict, PdfObject
from tkinter import Tk
from tkinter.filedialog import askopenfilename, asksaveasfilename

# --- PDF Template ---
template_pdf_path = r"\\fs2.smpp.local\smulab2\STU00224908 - Ampakine Protocol\Bladder Diary\NIHdiary(editable).pdf"

# --- Helper: Convert time to 24-hour code ---
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

# --- Helper: Set radio button appearance (recursive) ---
def set_radio_button(field, value):
    field.V = PdfName(value)

    def update_kids(kids):
        for kid in kids:
            if kid.AP and kid.AP.N:
                if PdfName(value) in kid.AP.N:
                    kid.AS = PdfName(value)
                else:
                    kid.AS = PdfName('Off')
            if getattr(kid, "Kids", None):
                update_kids(kid.Kids)

    if getattr(field, "Kids", None):
        update_kids(field.Kids)

# --- Select CSV ---
Tk().withdraw()
csv_path = askopenfilename(title="Select Bladder Diary CSV File", filetypes=[("CSV files", "*.csv")])
if not csv_path:
    print("User canceled file selection.")
    exit()

df = pd.read_csv(csv_path)
df.columns = df.columns.str.strip()
df["Date of Diary"] = pd.to_datetime(df["Date of Diary"])

# Combine hour + AM/PM if present
if "Hour" in df.columns and "AM/PM" in df.columns:
    df["time_full"] = df["Hour"].astype(str) + " " + df["AM/PM"]
else:
    df["time_full"] = df["time"]

# --- Fill PDFs per date ---
for date, group in df.groupby("Date of Diary"):
    pdf = PdfReader(template_pdf_path)  # fresh copy per date

    for _, row in group.iterrows():
        code = time_to_24hr_code(row["time_full"])
        if not code:
            continue

        # --- PDF field keys ---
        drink_key = f"drink{code}"
        dsize_key = f"dsize{code}"
        trip_key = f"trip{code}"
        event_key = f"event{code}"
        amount_key = f"amount{code}"
        leak_key = f"leak{code}"
        urge_yes_key = f"UrgeYes{code}"
        urge_no_key = f"UrgeNo{code}"

        date_key = "date"
        recordID_key = "recordID"
        day_pads_key = "day_pads"
        day_diapers_key = "day_diapers"
        healthcare_qs1_key = "healthcare_qs1"
        healthcare_qs2_key = "healthcare_qs2"
        healthcare_qs3_key = "healthcare_qs3"

        for page in pdf.pages:
            for annot in page.Annots or []:
                if not annot.T:
                    continue
                key = annot.T[1:-1]

                # --- Text fields ---
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
                elif key == date_key:
                    annot.V = row["Date of Diary"].strftime("%m/%d/%Y")
                    annot.AP = None
                elif key == recordID_key:
                    annot.V = str(row.get("recordID", ""))
                    annot.AP = None
                elif key == day_pads_key:
                    annot.V = str(row.get("day_pads", ""))
                    annot.AP = None
                elif key == day_diapers_key:
                    annot.V = str(row.get("day_diapers", ""))
                    annot.AP = None
                elif key == healthcare_qs1_key:
                    annot.V = str(row.get("healthcare_qs1", ""))
                    annot.AP = None
                elif key == healthcare_qs2_key:
                    annot.V = str(row.get("healthcare_qs2", ""))
                    annot.AP = None
                elif key == healthcare_qs3_key:
                    annot.V = str(row.get("healthcare_qs3", ""))
                    annot.AP = None

                # --- Radio buttons ---
                elif key == amount_key:
                    value = row.get("amount", "")
                    if value in ["Small", "Medium", "Large"]:
                        set_radio_button(annot, value)
                elif key == leak_key:
                    value = row.get("leak", "")
                    if value in ["Small", "Medium", "Large"]:
                        set_radio_button(annot, value)

                # --- Checkboxes ---
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

    # --- Ask user where to save PDF ---
    default_name = f"BladderDiary_{date.strftime('%Y%m%d')}.pdf"
    save_path = asksaveasfilename(
        title=f"Save PDF for {date.strftime('%Y-%m-%d')}",
        defaultextension=".pdf",
        initialfile=default_name,
        filetypes=[("PDF files", "*.pdf")]
    )

    if save_path:
        pdf.Root.AcroForm.update(PdfDict(NeedAppearances=PdfObject("true")))
        PdfWriter().write(save_path, pdf)
        print("Saved:", save_path)
    else:
        print(f"Skipped saving PDF for {date.strftime('%Y-%m-%d')}")