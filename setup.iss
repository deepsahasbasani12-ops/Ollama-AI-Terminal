[Setup]
AppName=Ollama AI Terminal
AppVersion=1.0
DefaultDirName={pf}\OllamaTerminal
DefaultGroupName=OllamaTerminal
OutputDir=output
OutputBaseFilename=OllamaTerminalSetup
Compression=lzma
SolidCompression=yes

[Dirs]
Name: "{app}\Memory"

[Files]
Source: "dist\OllamaTerminal.exe"; DestDir: "{app}"; Flags: ignoreversion

[Run]
; Check if Ollama exists (optional warning)
Filename: "cmd.exe"; Parameters: "/c ollama --version"; Flags: runhidden

; Pull model (qwen2:0.5b)
Filename: "cmd.exe"; Parameters: "/c ollama pull qwen2:0.5b"; StatusMsg: "Downloading AI model (~500MB)..."; Flags: waituntilterminated

; Launch your app
Filename: "{app}\OllamaTerminal.exe"; Description: "Launch App"; Flags: nowait postinstall skipifsilent
