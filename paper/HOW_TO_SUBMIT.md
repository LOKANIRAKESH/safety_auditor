# IEEE Submission Checklist

Follow these steps in order after your paper draft is complete and results are filled in.

---

## Step 1 — Choose your submission system

| Conference | System | URL |
|---|---|---|
| IEEE ETFA 2027 | Papercept | https://papercept.net |
| IEEE CASE 2027 | Papercept | https://papercept.net |
| FMICS 2027 | EasyChair | https://easychair.org |
| SafeComp 2027 | EasyChair | https://easychair.org |

Search for the 2027 call for papers in Jan–Feb 2027.

---

## Step 2 — Create author account

1. Go to the submission system for your target conference
2. Create an account with your **institutional email** (`@students.amrita.edu`)
3. Add co-author Dr. Raviteja with their institutional email

---

## Step 3 — Compile the paper and check it

```bash
# Install MiKTeX (Windows): https://miktex.org/download
# Then compile:
cd paper
pdflatex main.tex
bibtex main
pdflatex main.tex
pdflatex main.tex
```

Check:
- [ ] No LaTeX compilation errors
- [ ] No `\RESULT{}` placeholders remaining in the PDF (search for "FILL:" in the PDF)
- [ ] All references in `references.bib` appear in the paper
- [ ] No `[TODO]` strings remain in `references.bib`
- [ ] Total page count is within conference limit (8 pages for IEEE ETFA/CASE, 15 for FMICS)
- [ ] Figures are readable at 100% zoom
- [ ] Tables fit within column width

---

## Step 4 — IEEE PDF compliance check (mandatory for IEEE)

1. Download IEEE PDF eXpress: https://www.pdf-express.org
2. Create an account using your conference's PDF eXpress conference ID (found in the CFP)
3. Upload your PDF — it will check margins, fonts, and Xplore compatibility
4. Fix any reported issues and re-upload until you get a "Compliant" stamp

**Common issues:**
- Fonts not embedded — add `\usepackage{ae}` or compile with `pdflatex`
- Margins wrong — do not change `\documentclass[conference]{IEEEtran}` margins
- File too large — compress images with `\includegraphics[width=\columnwidth]{...}`

---

## Step 5 — Author information (fill in before submitting)

In `paper/main.tex`, fill in:
- [ ] Your email address: `\texttt{[YOUR EMAIL]@students.amrita.edu}`
- [ ] Dr. Raviteja's surname: `\IEEEauthorblockN{Dr. Raviteja [SURNAME]}`
- [ ] Dr. Raviteja's email: `\texttt{[GUIDE EMAIL]@amrita.edu}`

---

## Step 6 — Submit

1. Log into the submission system
2. Click "Submit New Paper"
3. Enter:
   - **Title**: `Pre-Synthesis Safety Auditing of Industrial Control Specifications Using a Neuro-Symbolic Framework`
   - **Abstract**: copy from `main.tex` (the text between `\begin{abstract}` and `\end{abstract}`)
   - **Keywords**: `Industrial Control Systems, Safety Auditing, Neuro-Symbolic AI, PLC, Z3 SMT Solver, IEC 61511, Formal Verification, Large Language Models`
   - **Topic area**: Industrial Automation / Safety-Critical Systems / AI for Industrial Systems
4. Upload the IEEE PDF eXpress-compliant PDF
5. Add all authors (you + Dr. Raviteja)
6. **Get Dr. Raviteja's approval before clicking Submit**

---

## Step 7 — After submission

- Save the submission confirmation email and paper ID
- The conference will email you reviewer feedback (typically 2–3 reviewers)
- If accepted: you will need to sign the IEEE copyright transfer form (automatic in the system)
- If major revision: address each reviewer comment point-by-point in a response letter

---

## Important: Things that will cause immediate rejection

| Issue | How to avoid |
|---|---|
| Results are placeholders / obviously incomplete | Run the evaluation, fill in all `\RESULT{}` |
| Related work doesn't cover HAZOP / IEC 61511 tools | Complete CITATION_TODO.md items |
| Paper not proofread | Have Dr. Raviteja read the full draft |
| Over page limit | Trim Section VI (Discussion) first |
| No real data | Run on Schneider Electric document, add to Section V-D |
| Guide not informed | Never submit without guide approval |
