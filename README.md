# PassForge — Generate. Analyze. Protect.

A desktop password manager: create, analyze, and store your passwords behind
a single master password, with an email alert if someone tries to break in
five times in a row. Includes a browser extension that offers to save new
passwords as you create them on any site. Built with Python and
CustomTkinter — a real desktop app, not a website.

---

## What it does

- **One master password protects everything.** On first launch you create a
  PassForge account (email + master password). Every time after that, you
  need that master password to open the vault at all.
- **Unauthorized-access alerts after 5 failed attempts.** PassForge counts
  consecutive wrong master-password attempts. On the 5th in a row, it
  emails the registered owner address — not on every single miss, so a
  fumbled first attempt doesn't spam your inbox. The counter resets on a
  successful login (or after an alert fires, so the next 5 misses trigger
  another one).
- **Change your master password any time**, from inside the app (see
  "Change master password" in the vault header). Every saved entry is
  automatically re-encrypted under the new password — nothing else about
  your vault changes.
- **Edit a saved password later.** Click **Edit** on any entry to update
  its label or replace the password itself (manually or generated),
  whenever it changes on the actual site.
- **Passwords are hidden by default**, shown as `••••••••••` in the vault
  list. Click **Show** to reveal one, **Copy** to copy it to your clipboard
  (which clears itself again after 20 seconds).
- **Every password is saved with a reason** — "Personal Gmail," "Work VPN,"
  whatever you're creating it for — so you can find it again later. Search
  by reason from the toolbar.
- **Two ways to add a password:**
  - **I'll create it** — type your own, and PassForge scores its strength
    in real time (entropy-based, not a checkbox count) with concrete
    suggestions if it's weak.
  - **Generate for me** — PassForge creates a cryptographically secure
    password (or you can extend it to generate passphrases) with
    adjustable length and character rules.
- **A browser extension** (see `passforge-extension/`) that notices when
  you submit a password on any website and offers to save it straight
  into your vault, with a label you choose, without leaving the page.
- **Clean, light UI** built around the PassForge brand — no dark mode.

## Why it's actually secure (not just labeled that way)

- **The master password is never stored.** Only a salted PBKDF2 hash of it
  is kept, purely to check a login attempt. This means **losing your
  master password means losing the vault** — there's no "reset password"
  link, because a real reset would require storing something that could
  reverse it. This is disclosed to you at setup.
- **Each saved password is encrypted** (Fernet / AES) with a key derived
  from your master password. That key exists only in memory while the app
  is unlocked, and disappears when you hit **Lock**.
- **Password generation uses `secrets`**, Python's cryptographically
  secure RNG — not `random`, which is predictable and unsafe for this.

## Project structure

```
passforge/
├── main.py                       entry point
├── app.py                        window setup, session state, screen routing
├── PassForge.bat                 double-click launcher for Windows
├── PassForge.command             double-click launcher for macOS/Linux
├── core/
│   ├── crypto_utils.py           master password hashing + vault encryption
│   ├── password_tools.py         strength scoring + secure generation
│   ├── db.py                     local SQLite storage (thread-safe)
│   ├── alerts.py                 email alert after 5 failed logins
│   └── bridge_server.py          local HTTP bridge for the browser extension
├── ui/
│   ├── style.py                  colors & fonts (sampled from the logo)
│   ├── setup_frame.py            first-run account creation screen
│   ├── login_frame.py            unlock screen
│   ├── vault_frame.py            main password list
│   ├── add_entry_dialog.py       add / edit password dialog
│   └── change_master_dialog.py   change master password dialog
├── assets/
│   ├── logo.png
│   └── icon.ico
├── passforge.spec                PyInstaller build spec
├── build.sh / build.bat          one-command build scripts
├── installer.iss                 Inno Setup script → real Windows installer
├── config.example.json           email alert (SMTP) settings template
└── requirements.txt

passforge-extension/              browser extension (separate folder, see below)
```

## Running it

You need Python 3.9+ installed. Then:

```bash
pip install -r requirements.txt
python main.py
```

Or just double-click **`PassForge.bat`** (Windows) or **`PassForge.command`**
(macOS/Linux) from now on — no terminal, no VS Code. Both scripts use the
built executable automatically if you've already run `build.bat`/`build.sh`,
and fall back to running from source (installing dependencies once, if
needed) otherwise.

The first time you run it, you'll be asked to create your PassForge
account. Every time after that, you'll see the unlock screen.

Your vault is stored locally at `~/.passforge/vault.db` (on Windows:
`C:\Users\<you>\.passforge\vault.db`).

## Setting up email alerts (optional but recommended)

Without this step, PassForge still works completely normally — failed
logins are just logged locally instead of emailed.

1. Copy `config.example.json` to `config.json`.
2. Fill in an SMTP account PassForge can send *from*. For Gmail:
   - `host`: `smtp.gmail.com`, `port`: `587`
   - `username`: your Gmail address
   - `app_password`: a 16-character [Google App Password](https://myaccount.google.com/apppasswords)
     — **not** your normal Gmail password (Google blocks normal-password
     SMTP login for security reasons)
3. Save, and restart PassForge. Alerts will go to whatever email address
   you registered as the owner at setup — it doesn't have to match the
   SMTP sender address.

`config.json` is already in `.gitignore` — never commit real credentials.

## Building a standalone executable

You don't need Python installed to *run* the built app — only to build it.
Build on the OS you want the executable for (PyInstaller doesn't
cross-compile):

**macOS / Linux:**
```bash
./build.sh
```

**Windows:**
```bat
build.bat
```

Either produces a single executable in `dist/` — `PassForge` (macOS/Linux)
or `PassForge.exe` (Windows) — that runs standalone, no Python required,
with the PassForge icon and no console window.

## Making it installable for other people (Windows)

A raw `.exe` works, but a real installer is what makes a tool feel finished
— Start Menu entry, optional desktop icon, proper uninstall. PassForge
includes an [Inno Setup](https://jrsoftware.org/isinfo.php) script for
exactly that, free and widely used for indie Windows software:

1. Run `build.bat` first (see above) — you need `dist\PassForge.exe` to exist.
2. Install Inno Setup (free) if you don't have it.
3. Open `installer.iss` in Inno Setup and click **Compile** — or from the
   command line: `ISCC.exe installer.iss`.
4. You'll get `Output\PassForgeSetup.exe`. That single file is what you
   share — anyone can double-click it, click Next a few times, and get
   PassForge installed with shortcuts and an uninstaller, no Python needed.

## Browser extension (save passwords as you create them)

`passforge-extension/` is a companion Chrome/Edge extension: it notices
when you submit a password on any website and offers to save it into your
PassForge vault, right from the page, with a label you choose.

It talks to the desktop app over a small localhost-only bridge server
(`core/bridge_server.py`) that only accepts connections while the vault is
unlocked. See `passforge-extension/README.md` for install steps (it's a
"Load unpacked" extension — a couple of clicks in `chrome://extensions`)
and a one-time pairing step using a token PassForge generates for you.

## Limitations & honest caveats

- **This is a single-user, single-vault design.** It's built for one
  person protecting their own passwords, not a shared team vault.
- **No master password recovery**, by design (see above). Write it down
  somewhere safe outside the app.
- **Email alerts depend on your own SMTP credentials.** PassForge doesn't
  run its own mail server or come with one built in.
- **The wordlist for passphrase generation** (in `core/password_tools.py`)
  is a small placeholder set; swap in the [EFF long wordlist](https://www.eff.org/dice)
  for real Diceware-strength passphrases if you build that feature out
  further.
- The local database file itself isn't additionally encrypted at the
  filesystem level — the individual password *values* inside it are, but
  reasons/labels and metadata are stored in plain SQLite. Full-disk or
  file-level encryption (which most modern OSes offer) covers this in
  practice.
- **The browser extension's trust model is intentionally lightweight** —
  a paired token over localhost, not browsers' native-messaging API. Fine
  for a personal tool on your own machine; see
  `passforge-extension/README.md` for the full explanation.
- **The extension doesn't autofill or deduplicate** — it prompts to save
  on every password form submission, and you decide each time.
- Changing the master password re-encrypts every entry in one pass. On a
  vault with a very large number of entries this could take a moment;
  for typical personal use (tens to low hundreds of entries) it's instant.

## License

MIT — see `LICENSE`.
