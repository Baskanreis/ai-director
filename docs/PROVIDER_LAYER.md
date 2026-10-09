# AI Director Provider Layer

v2.33 introduces an independent model/provider layer for Multi-Agent Director.

## Independent selection

Every specialist can use a different provider:

- `vision` → local GPU vision model
- `speech` → local Whisper
- `copy` / `creative` → strong LLM
- remaining agents → local LLM or built-in fallback

Create `~/.ai_director/providers.json` or pass a provider configuration directly to
`MultiAgentOrchestrator`.

Example:

```json
{
  "providers": {
    "local_vision": {
      "kind": "openai_compatible",
      "endpoint": "http://127.0.0.1:11434/v1",
      "model": "llava"
    },
    "whisper_local": {
      "kind": "whisper",
      "model": "small"
    },
    "strong_llm": {
      "kind": "openai_compatible",
      "endpoint": "https://api.openai.com/v1",
      "model": "gpt-5.6",
      "api_key_env": "OPENAI_API_KEY"
    }
  },
  "agents": {
    "vision": {"provider": "local_vision", "fallback": ["builtin"], "retries": 2},
    "speech": {"provider": "whisper_local", "fallback": ["builtin"], "retries": 1},
    "copy": {"provider": "strong_llm", "fallback": ["local_llm", "builtin"], "retries": 2}
  }
}
```

Real providers are opt-in through `AI_DIRECTOR_ENABLE_PROVIDERS=1` so an existing
installation never unexpectedly starts network inference. Per-run overrides can be
supplied in `context["agent_providers"]`.

Failure path:

`cache hit → provider → retry → fallback provider → built-in agent → Final Compiler`

The compiler always receives the complete `AgentResult` map and produces exactly one
`CompiledEditPlan`; a single provider outage cannot terminate the whole director.
