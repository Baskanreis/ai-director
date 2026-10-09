# v2.56 Regional Hotspot Revision

Retention hotspot'ları artık tüm projeyi yeniden kurmadan küçük alternatif editler üretebilir.

## Akış
1. Hotspot seçilir.
2. `targeted_revision_request` ile neden/aksiyon çıkarılır.
3. En fazla üç düşük-maliyetli aday hazırlanır.
4. Her aday mevcut preview/QC evaluator'a verilebilir.
5. Skoru mevcut sürümden anlamlı derecede yüksek olmayan aday reddedilir.
6. Kazanan yalnızca `regional_revision` metadata'sı ve hedefli cue değişiklikleriyle döner.

## Aksiyonlar
- B-roll adayı
- Reframe / hafif punch-in
- Pattern break
- Pacing hint

## CPU politikası
Yeni model yüklenmez. Gerçek render için mevcut preview renderer callback'i kullanılır. Varsayılan aday sayısı 3'tür.
