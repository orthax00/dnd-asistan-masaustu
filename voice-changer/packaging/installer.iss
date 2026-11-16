; Inno Setup betiği: iscc packaging\installer.iss
; Önce PyInstaller çıktısı (dist\DnDVoiceChanger) ve build\vbcable klasörü hazır olmalı.

#define AppName "DnD Voice Changer"
#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif

[Setup]
AppId={{6C0E7B9A-4F1D-4C55-9E3B-DD20C0A1B7F2}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=DnD Voice Changer
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
OutputDir=..\dist
OutputBaseFilename=DnDVoiceChanger_Setup_{#AppVersion}
SetupIconFile=..\icon.ico
UninstallDisplayIcon={app}\DnDVoiceChanger.exe
Compression=lzma2
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin
WizardStyle=modern
InfoBeforeFile=vbcable_notice.txt

[Languages]
Name: "turkish"; MessagesFile: "compiler:Languages\Turkish.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Masaüstü kısayolu oluştur"; GroupDescription: "Kısayollar:"
Name: "vbcable"; Description: "Sanal mikrofonu (VB-CABLE, VB-Audio donationware) kur - Discord için gerekli"; GroupDescription: "Sürücü:"; Check: not CableInstalled

[Files]
Source: "..\dist\DnDVoiceChanger\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion
Source: "..\build\vbcable\*"; DestDir: "{tmp}\vbcable"; Flags: recursesubdirs deleteafterinstall; Tasks: vbcable

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\DnDVoiceChanger.exe"
Name: "{group}\{#AppName} kaldır"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\DnDVoiceChanger.exe"; Tasks: desktopicon

[Run]
; VB-CABLE resmi kurulumu (sessiz kurulum bayrakları: -i -h)
Filename: "{tmp}\vbcable\VBCABLE_Setup_x64.exe"; Parameters: "-i -h"; StatusMsg: "Sanal mikrofon (VB-CABLE) kuruluyor..."; Flags: waituntilterminated; Tasks: vbcable
Filename: "{app}\DnDVoiceChanger.exe"; Description: "Uygulamayı başlat"; Flags: nowait postinstall skipifsilent; Tasks: not vbcable

[Code]
function CableInstalled: Boolean;
begin
  { VB-CABLE sürücüsü kuruluysa bu dosya bulunur }
  Result := FileExists(ExpandConstant('{sys}\drivers\vbaudio_cable64_win10.sys'))
         or FileExists(ExpandConstant('{sys}\drivers\vbaudio_cable64_win7.sys'));
end;

function NeedRestart(): Boolean;
begin
  Result := WizardIsTaskSelected('vbcable');
end;
