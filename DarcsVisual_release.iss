; Darc's Visual Pickit Inno Setup installer
; Version and product defines are generated from release_metadata.py
; SOURCE TREE NOTE:
;   app_main.py is now split across multiple local .py modules.
;   build_release.bat refreshes .version_auto.issinc from release_metadata.py
;   and produces a one-folder PyInstaller build at:
;   dist\DarcsVisualPickit\
; THIS .iss FILE LIVES IN THE SAME FOLDER AS:
;   build_release.bat
;   darc.ico
;   dist\DarcsVisualPickit\DarcsVisualPickit.exe

#include ".version_auto.issinc"

[Setup]
AppId={{2F27508A-8149-4F14-A53A-4C7A09A6F6B7}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}

DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes

OutputDir=.\output
OutputBaseFilename=DarcsVisualPickit-Setup-v{#MyAppVersion}

Compression=lzma
SolidCompression=yes
WizardStyle=modern
WizardSizePercent=110

PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog
UsedUserAreasWarning=no

ArchitecturesInstallIn64BitMode=x64compatible

SetupIconFile=darc.ico
UninstallDisplayIcon={app}\{#MyAppExeName}

CloseApplications=yes
CloseApplicationsFilter={#MyAppExeName}

UsePreviousAppDir=yes
DisableDirPage=no
DisableReadyMemo=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
Source: "dist\DarcsVisualPickit\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[UninstallDelete]
Type: filesandordirs; Name: "{localappdata}\KolbotForever\DarcsVisualPickit\temp"
