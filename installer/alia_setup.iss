; Inno Setup script for Alia AI — Windows installer
; Compiled by the GitHub Actions windows-build workflow.

[Setup]
AppName=Alia AI
AppVersion=1.0.0
AppPublisher=Subhajit Mandal
AppPublisherURL=https://github.com/Subhajit907/Sam-Ai
AppSupportURL=https://github.com/Subhajit907/Sam-Ai/issues
DefaultDirName={autopf}\Alia AI
DefaultGroupName=Alia AI
AllowNoIcons=yes
OutputDir=..\installer_output
OutputBaseFilename=Alia-AI-Installer-Windows
SetupIconFile=..\modules\assets\alia_icon.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequiredOverridesAllowed=dialog
MinVersion=10.0

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"; Flags: unchecked

[Files]
; The entire PyInstaller output folder
Source: "..\dist\Alia AI\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Alia AI";              Filename: "{app}\Alia AI.exe"
Name: "{group}\Uninstall Alia AI";    Filename: "{uninstallexe}"
Name: "{userdesktop}\Alia AI";        Filename: "{app}\Alia AI.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\Alia AI.exe"; Description: "&Launch Alia AI now"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Remove user data directory on uninstall (optional — comment out to keep chat history)
; Type: filesandordirs; Name: "{userappdata}\Alia AI"
