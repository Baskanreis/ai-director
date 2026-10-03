# v2.27 Content-Aware AI Editing

AI Director artık platformdan bağımsız bir **creative direction** katmanına sahiptir.
İçeriğin eğitsel, eğlence, korku, belgesel, oyun, vlog, podcast, tutorial, review,
teknoloji, spor, seyahat, komedi, sinematik, haber, hikâye, müzik veya röportaj
karakterine göre kurgu politikasını değiştirir.

## İlke

`QVideoFrame -> GPU/RHI -> compositor` hattı performans katmanıdır; creative
intelligence ise **ne yapılacağına** karar veren metadata katmanıdır. Böylece efekt
kararları render backend'ine bağımlı değildir.

## Stil sözleşmesi

Her genre şu boyutları kontrol eder:

- pacing / cut aggression
- transition density
- motion density
- captions
- color mood
- sound design
- B-roll density
- silence policy
- hook language
- camera language
- effect budget
- avoid list

## Öğrenme / kalibrasyon

Sistem deterministik başlangıç politikası kullanır. Daha sonra kullanıcı kabul/ret
kararları, reference video profilleri ve kanal performans kayıtları bu ağırlıkları
kalibre edebilir. Bu, "kusursuz" sonucu garanti etmek yerine hataların ölçülmesini,
geribildirimle stilin kişiselleştirilmesini ve geri alınabilir/non-destructive
edit kararlarını sağlar.
