# v2.22 — Highlight Remix Director

## Amaç

Uzun bir videoda kullanıcının beğendiği bağımsız bölümleri tek bir kısa videoda
hikâye akışını koruyacak şekilde harmanlamak.

Örnek: kullanıcı 15 saniyelik bir bölümü ve videonun başka yerindeki 10 saniyelik
bölümü beğenirse motor bunları tek bir 25 saniyelik dikey kurguya dönüştürebilir.
İlk güçlü bölüm hook, ikinci bölüm payoff olarak konumlandırılabilir.

## Tasarım ilkeleri

- Kullanıcı beğenisi en güçlü sinyallerden biridir.
- Kaynak zamanları korunur; kurgu non-destructive'dır.
- Dikey/landscape teslimat platform profilinden belirlenir.
- Auto-reframe, caption, motion, SFX ve müzik ayrı katmanlar olarak eklenebilir.
- "Viral" bir garanti değil, hook/pacing/payoff/rewatch gibi ölçülebilir edit sinyallerini optimize eden bir hedef olarak ele alınır.

## API

`app.ai.viral_remix.HighlightSelection`
`app.ai.viral_remix.build_remix_plan(...)`
`app.ai.viral_remix.realize_remix(...)`

Bir sonraki katman, gerçek transcript/scene embeddings ile seçilen anların birbirine
anlamsal geçişini ölçmek ve gerektiğinde kısa bridge/B-roll üretim noktaları önermektir.
