import pandas as pd
import re
from pdfrw import PdfReader, PdfWriter, PdfName, PdfDict, PdfObject
from tkinter import Tk
from tkinter.filedialog import askopenfilename, asksaveasfilename
import os

################### THIS SECTION OF THE CODE CONVERTS THE CSV FILE DOWNLOADED FROM REDCAP TO ONE THAT CAN BE READ INTO THE PDF #############
# --- Select RAW CSV File ---
Tk().withdraw()  # Hide the root window
file_path = askopenfilename(title="Select Bladder Diary CSV File", filetypes=[("CSV files", "*.csv")])
if not file_path:
    print("User canceled file selection.")
    exit()

# --- Read CSV ---
df = pd.read_csv(file_path)
df.columns = df.columns.str.strip()  # remove leading/trailing spaces
# --- Drop completely empty rows ---
df = df.dropna(how='all')

# --- Rename columns ---
df = df.rename(columns={
    'Record ID': 'recordID',
    'Date of Diary': 'date',
    'Hour:': 'time',
    'What kind of drink? (i.e. juice, water, milk, etc.)': 'drink',
    'How much was drank (in oz)? ': 'dsize',
    'How many times did you use the bathroom?': 'trip',
    'How much urine?': 'amount',
    'Accidental Leaks How much urine?': 'leak',
    'Did you feel a strong urge to go?':'urge',
    'What were you doing at the time?(i.e. sneezing, lifting, arriving home, sleeping, etc.)':'event'
})
# Convert 'trip' column to integers
df['trip'] = pd.to_numeric(df['trip'], errors='coerce').fillna(0).astype(int)

# --- Clean Hour column (remove leading apostrophe) ---
df['time'] = df['time'].astype(str).str.replace("'", "")

# --- Consolidate Hour: and AM or PM into single column ---
df['time'] = df['time'].astype(str).str.strip() + ' ' + df['AM or PM'].astype(str).str.strip()

# --- Extract start hour safely ---
start_hours = df['time'].str.split('-').str[0].str.strip()
df['start_hour'] = pd.to_numeric(start_hours, errors='coerce')

# --- Convert 12-hour clock to 24-hour time ---
df['is_pm'] = df['AM or PM'].str.upper() == 'PM'
df['start_hour_24'] = df['start_hour']
# PM (except 12 PM)
df.loc[df['is_pm'] & (df['start_hour'] != 12), 'start_hour_24'] += 12
# 12 AM -> 0
df.loc[~df['is_pm'] & (df['start_hour'] == 12), 'start_hour_24'] = 0

# --- Convert Date column ---
df['Date'] = pd.to_datetime(df['date'], errors='coerce')
df = df.dropna(subset=['Date'])

# --- Combine Date + Hour to datetime ---
df['DateTime'] = df['Date'] + pd.to_timedelta(df['start_hour_24'], unit='h')

# --- Sort chronologically ---
df_sorted = df.sort_values('DateTime').reset_index(drop=True)

# --- Drop helper columns ---
df_sorted = df_sorted.drop(columns=['start_hour', 'is_pm', 'start_hour_24', 'DateTime', 'Date', 'AM or PM'])

# --- Display sorted table ---
#print(df_sorted)

##########################################################################################################
######## THIS PART OF THE CODE ADDS THE CSV TO THE PDF ###################################################
# Get the folder where the current script is located
script_folder = os.path.dirname(os.path.abspath(__file__))

# Build the PDF template path relative to the script folder
template_pdf_path = os.path.join(script_folder, "NIHdiary(editable).pdf")

# Check if the template exists
if not os.path.exists(template_pdf_path):
    print(f"Template PDF not found in script folder: {template_pdf_path}")
    exit()

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
def set_radio_group(pdf, field_name, value):
    for page in pdf.pages:
        for annot in page.Annots or []:
            if annot.Parent and annot.Parent.T:
                name = annot.Parent.T[1:-1]

                if name == field_name:
                    export = PdfName(value)

                    annot.Parent.V = export
                    annot.AS = export

# --- Use the sorted dataframe for the PDF step ---
df = df_sorted.copy()

df.columns = df.columns.str.strip()

# Rename date column to match later code
df["Date of Diary"] = pd.to_datetime(df["date"])

# time column already exists, so just rename for the PDF logic
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
         # --- Radio buttons ---
        amount_value = row.get("amount")
        leak_value = row.get("leak")

        amount_value = "" if pd.isna(amount_value) else str(amount_value).strip()
        leak_value = "" if pd.isna(leak_value) else str(leak_value).strip()

        if amount_value in ["Small", "Medium", "Large"]:
            set_radio_group(pdf, amount_key, amount_value)

        if leak_value in ["Small", "Medium", "Large"]:
            set_radio_group(pdf, leak_key, leak_value)

    # --- Ask user where to save PDF ---
    recordID = group["recordID"].iloc[0]
    default_name = f"{recordID}_BladderDiary_{date.strftime('%Y%m%d')}.pdf"
    save_path = asksaveasfilename(
        title=f"Save PDF for {date.strftime('%Y-%m-%d')}",
        defaultextension=".pdf",
        initialfile=default_name,
        filetypes=[("PDF files", "*.pdf")]
    )

    if save_path:
        pdf.Root.AcroForm.update(PdfDict(NeedAppearances=PdfObject("true")))
        PdfWriter().write(save_path, pdf)
        print("Saved")
    else:
        print(f"Skipped saving PDF for {date.strftime('%Y-%m-%d')}")

csv_path = os.path.join(os.path.dirname(save_path), f"{recordID}_sorted.csv")
df_sorted.to_csv(csv_path, index=False)
