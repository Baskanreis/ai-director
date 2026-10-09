# Managed Provider Runtime

AI Director v2.34 is designed so the end user does not install Python, FFmpeg,
Whisper, llama.cpp, or model packages manually.

The Windows Setup installs the PyInstaller application into `Program Files\AI Director`
and then runs `installer\setup_ai_runtime.ps1` silently. The runtime provisioner:

1. downloads and verifies Whisper Base into `models\whisper\base.pt`;
2. downloads Qwen3 1.7B Q4_K_M into `models\llm`;
3. selects the latest official llama.cpp Windows x64 package, preferring CUDA when
   an NVIDIA GPU is detected and falling back to CPU otherwise;
4. places `llama-server.exe` and its required DLLs in `runtime\llama`;
5. writes `runtime\ai_runtime_status.json`.

The app starts llama.cpp lazily, not during application startup, to preserve the
performance-oriented startup behavior.

Cloud APIs are optional. If an API key is not configured or a provider is offline,
the agent automatically retries, switches to its configured fallback chain, and
finally uses the mature built-in agent implementation.
