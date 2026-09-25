; PassForge installer script for Inno Setup (https://jrsoftware.org/isinfo.php — free).
;
; How to use:
;   1. Run build.bat first. This produces dist\PassForge.exe.
;   2. Install Inno Setup (free) from the link above.
;   3. Open this file (installer.iss) in Inno Setup and click Compile —
;      or from the command line: "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss
;   4. You'll get Output\PassForgeSetup.exe — a normal Windows installer
;      that anyone can double-click: it installs PassForge, adds Start
;      Menu and (optionally) Desktop shortcuts, and registers an
;      uninstaller in "Add or Remove Programs". No Python required.

#define MyAppName "PassForge"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "PassForge"
#define MyAppExeName "PassForge.exe"

[Setup]
AppId={{B6C1B9B9-6B7A-4B7E-9C4B-9F1D9E7A6B7C}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
UninstallDisplayIcon={app}\{#MyAppExeName}
OutputDir=Output
OutputBaseFilename=PassForgeSetup
Compression=lzma
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64compatible
DisableProgramGroupPage=yes
SetupIconFile=assets\icon.ico

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"

[Files]
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName} now"; Flags: nowait postinstall skipifsilent
