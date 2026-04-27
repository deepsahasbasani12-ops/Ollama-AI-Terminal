[Setup]
AppName=Ollama Terminal
AppVersion=1.0
DefaultDirName={pf}\OllamaTerminal
DefaultGroupName=OllamaTerminal
OutputDir=output
OutputBaseFilename=OllamaTerminalSetup
Compression=lzma
SolidCompression=yes

[Files]
Source: "dist\OllamaTerminal.exe"; DestDir: "{app}"; Flags: ignoreversion

[Run]
; Check if Ollama exists
Filename: "cmd.exe"; Parameters: "/c ollama --version"; Flags: runhidden

; Pull model (only model download happens here)
Filename: "cmd.exe"; Parameters: "/c ollama pull qwen2:0.5b"; StatusMsg: "Downloading model qwen2:0.5b..."; Flags: waituntilterminated

; Launch your app
Filename: "{app}\OllamaTerminal.exe"; Flags: nowait postinstall skipifsilent
