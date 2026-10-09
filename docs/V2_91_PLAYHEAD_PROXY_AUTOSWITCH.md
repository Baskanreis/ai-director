# v2.91 — Playhead-Aware Proxy Auto-Switch

`PlayheadProxyPlanner` ranks clips near the current playhead so background proxy generation follows likely playback. `ProxyAutoSwitch` resolves playback to an available proxy without modifying timeline data.

Active clips receive priority 1000. Clips ahead are prefetched within a configurable lookahead window; recently passed clips can receive a smaller behind-playhead priority.

The proxy service completion callback can register finished proxies and refresh playback immediately.
