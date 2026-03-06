# Build Instructions — BladderDiaryFiller.exe

## What you need on your Windows machine

- Python 3.9+ installed (https://www.python.org/downloads/)
- The two output files from this package:
  - `bladder_diary.py`
  - `bladder_diary.spec`
- Your PDF template: `NIHdiary(editable).pdf`

---

## Step 1 — Put all three files in the same folder

```
C:\BladderDiaryBuild\
    bladder_diary.py
    bladder_diary.spec
    NIHdiary(editable).pdf      ← your actual template PDF
```

---

## Step 2 — Install dependencies

Open a Command Prompt in that folder and run:

```
pip install pyinstaller pandas pdfrw
```

---

## Step 3 — Build the .exe

Still in the same folder, run:

```
pyinstaller bladder_diary.spec
```

PyInstaller will create a `dist\` folder. Your finished executable will be at:

```
dist\BladderDiaryFiller.exe
```

That single `.exe` file contains everything — including the bundled PDF template.
You can copy it to any Windows computer and run it without Python installed.

---

## Notes

- **Console window**: The exe currently shows a console window so you can see progress/errors.
  To hide it, open `bladder_diary.spec` and change `console=True` → `console=False`, then rebuild.

- **Antivirus false positives**: Some antivirus programs flag PyInstaller exes.
  This is a known issue with PyInstaller; the exe is safe. You may need to add an exception.

- **64-bit only**: The exe will match the Python architecture you build with (64-bit recommended).
