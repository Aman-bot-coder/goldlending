; Inno Setup Script for Gold & Silver Loan Management System
; Build with Inno Setup 6.x: https://jrsoftware.org/isinfo.php

[Setup]
AppName=Gold & Silver Loan Management System
AppVersion=1.0.0
AppPublisher=Gold Silver Loan Services
AppPublisherURL=
DefaultDirName={autopf}\GoldSilverLoan
DefaultGroupName=Gold Silver Loan
OutputDir=..\dist\installer
OutputBaseFilename=GoldSilverLoan_Setup_v1.0.0
SetupIconFile=..\assets\icons\app.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern
MinVersion=10.0
PrivilegesRequired=admin

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\dist\GoldSilverLoan\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Gold Silver Loan Manager"; Filename: "{app}\GoldSilverLoan.exe"
Name: "{group}\{cm:UninstallProgram,Gold Silver Loan Manager}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Gold Silver Loan Manager"; Filename: "{app}\GoldSilverLoan.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\GoldSilverLoan.exe"; Description: "{cm:LaunchProgram,Gold Silver Loan Manager}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "{app}\GoldSilverLoan.exe"; Parameters: "--uninstall"; Flags: skipifdoesntexist

[Messages]
WelcomeLabel2=This will install [name/ver] on your computer.%n%nNOTE: Database credentials and API keys are never bundled inside the installer. You will configure the database connection on first launch.
