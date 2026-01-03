# 📄 Erflog – LaTeX Compiler Setup

This repository uses a **LaTeX template** (`backend/core/template.tex`) to generate PDF resumes.  The only external requirement is a LaTeX compiler with a handful of packages.  Below are platform‑specific, copy‑and‑paste commands that install **just** what is needed – **no Python** or other dependencies.

---

## 📦 What the commands do

| Step | Action |
|------|--------|
| **Install a LaTeX engine** | Installs a minimal TeX distribution (BasicTeX on macOS, a minimal TeX Live on Ubuntu, MiKTeX on Windows). |
| **Add required packages** | Installs the nine LaTeX packages that `backend/core/template.tex` actually uses: `latexsym`, `fullpage`, `titlesec`, `marvosym`, `color`, `verbatim`, `enumitem`, `hyperref`, `fancyhdr`, `babel`, `tabularx`. |

---

## 🖥️ Platform‑specific installation

### macOS
```bash
# Install BasicTeX (tiny TeX Live) via Homebrew
brew install --cask basictex

# Ensure tlmgr is on the PATH (BasicTeX puts it in /usr/local/texlive/2025basic/bin/universal-darwin)
export PATH="/usr/local/texlive/2025basic/bin/universal-darwin:$PATH"

# Install ONLY the packages required by the resume template
sudo tlmgr install latexsym fullpage titlesec marvosym color verbatim enumitem hyperref fancyhdr babel tabularx
```
> **Note:** If you don’t have Homebrew, install it first with:
> ```bash
> /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
> ```

---

### Ubuntu (or any Debian‑based Linux)
```bash
# Update package index
sudo apt-get update

# Install a minimal TeX Live that provides pdflatex
sudo apt-get install -y texlive-base texlive-latex-recommended texlive-fonts-recommended

# tlmgr is included; make sure it’s on the PATH (usually /usr/bin)
export PATH="/usr/bin:$PATH"

# Install the exact LaTeX packages the template needs
sudo tlmgr install latexsym fullpage titlesec marvosym color verbatim enumitem hyperref fancyhdr babel tabularx
```
> If `tlmgr` is missing after the above, install it with:
> ```bash
> sudo apt-get install -y texlive-extra-utils
> ```

---

### Windows (PowerShell – run **as Administrator**)
#### Option A – Using **winget** (Windows 10 + 2022)
```powershell
# Install MiKTeX (basic distribution) via winget
winget install -e --id MiKTeX.MiKTeX

# Add MiKTeX to the current session PATH
$env:Path += ";$env:ProgramFiles\MiKTeX 2.9\miktex\bin\x64"

# Install the required LaTeX packages using MiKTeX's package manager (mpm)
mpm --install=latexsym,fullpage,titlesec,marvosym,color,verbatim,enumitem,hyperref,fancyhdr,babel,tabularx
```
#### Option B – Using **Chocolatey** (if you prefer Chocolatey)
```powershell
# Install Chocolatey (run only if you don’t have it)
Set-ExecutionPolicy Bypass -Scope Process -Force; 
[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.SecurityProtocolType]::Tls12; 
iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

# Install MiKTeX via Chocolatey
choco install miktex -y

# Add MiKTeX to PATH for the session
$env:Path += ";$env:ProgramFiles\MiKTeX 2.9\miktex\bin\x64"

# Install the required packages
mpm --install=latexsym,fullpage,titlesec,marvosym,color,verbatim,enumitem,hyperref,fancyhdr,babel,tabularx
```
> If you don’t have **winget** or **Chocolatey**, you can download the MiKTeX installer manually from https://miktex.org/download, run it, then execute the `mpm --install=…` line in a new PowerShell window.

---

## ✅ Verify the installation
```bash
# Check that pdflatex (or the MiKTeX equivalent) is available
pdflatex --version
```
You should see something like `pdfTeX 3.141592653-2.6-1.40.27 (TeX Live 2025)`.

Now try compiling the template:
```bash
cd backend/core
pdflatex template.tex
```
If the compilation finishes without any `File `xxx.sty' not found` errors, the required packages are correctly installed.

---

## 📚 What’s next?
* Run the FastAPI backend (if you need the full service) – see the project’s main README for Python‑related setup.
* Use the provided LaTeX template to generate PDFs for resumes, cover letters, or any other document you plug data into via `backend/agents/agent_4_operative/latex_engine.py`.

---

*Happy LaTeX‑powered resume generation!*
