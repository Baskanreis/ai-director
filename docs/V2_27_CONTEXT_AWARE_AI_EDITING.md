# v2.27 Context-Aware AI Editing

AI Director artık yalnızca platforma göre değil, içeriğin **amacı ve türüne göre** edit reçetesi seçebilir.

## İçerik profilleri

Educational, Entertainment, Horror, Documentary, Cinematic, Comedy, Gaming, Vlog, Podcast, News, Tutorial, Review, Storytelling, Motivational, Music, Sports, Travel, Product, Wedding, Social, Auto ve Generic profilleri bulunur.

Her profil; pacing, cut agresifliği, transition ailesi, motion, color, caption, sound, müzik enerjisi, sessizlik davranışı, B-roll yoğunluğu, SFX yoğunluğu ve görsel yoğunluk için ayrı politika taşır.

## Karar sırası

1. İçerik metni/başlık/etiketlerden tür sinyalleri çıkarılır.
2. Tür için editoryal reçete seçilir.
3. Platform politikasıyla birlikte uygulanır.
4. Speech/meaning/continuity korumaları her zaman üst önceliktedir.
5. Son aşamada kalite kapısı; aşırı efekt, caption çakışması, ses clipping'i ve süreklilik risklerini kontrol eder.

## Öğrenme yaklaşımı

Bu katman deterministik ve açıklanabilirdir; "AI öğrensin" hedefini güvenli biçimde **edit tercihleri + geri bildirim hafızası** katmanına açacak bir sözleşme olarak tasarlar. Gelecekte model/LLM sinyalleri aynı `EditorialStylePlan` sözleşmesini doldurabilir.

Kullanıcı `requested_style` ile otomatik sınıflandırmayı override edebilir.
