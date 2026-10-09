"""Timeline Undo/Redo gecmisi.

Basit ve saglam bir yaklasim: her duzenleme oncesi timeline'in tam bir
anlik goruntusu (snapshot, `Timeline.to_dict()`) yiginin (stack) tepesine
itilir. Geri al (undo) bir onceki anlik goruntuyu geri yukler; ileri al
(redo) ayri bir yigindan geri alinan durumu tekrar uygular.

Bu yaklasim, timeline modelindeki her islemin (split/remove/move/trim/
add_media/ses ayarlari/altyazi/sahne bolme vb.) tek bir ortak mekanizma
ile geri alinabilmesini saglar; her islem icin ayri "command" sinifi
yazmaya gerek kalmaz ve bu yuzden hata olasiligi dusuktur.

Kullanim:
    history = TimelineHistory(timeline)
    history.push()          # degisiklikten ONCE cagrilir
    timeline.split(...)     # degisikligi yap
    ...
    history.undo()          # bir onceki duruma doner, guncel Timeline'i dondurur
    history.redo()          # geri alinani tekrar uygular
"""
from __future__ import annotations

from app.timeline.model import Timeline

MAX_HISTORY = 100


class TimelineHistory:
    def __init__(self, timeline: Timeline) -> None:
        self._timeline = timeline
        self._undo_stack: list[dict] = []
        self._redo_stack: list[dict] = []

    def set_timeline(self, timeline: Timeline) -> None:
        """Proje degistiginde (yeni/ac) gecmisi sifirlar ve yeni timeline'i baglar."""
        self._timeline = timeline
        self.clear()

    def clear(self) -> None:
        self._undo_stack.clear()
        self._redo_stack.clear()

    def push(self) -> None:
        """Bir duzenleme yapmadan HEMEN ONCE cagrilmalidir.

        Mevcut durumu undo yiginina kaydeder ve redo yiginini temizler
        (yeni bir dal basladigi icin eski "ileri al" gecmisi gecersizdir).
        """
        self._undo_stack.append(self._timeline.to_dict())
        if len(self._undo_stack) > MAX_HISTORY:
            self._undo_stack.pop(0)
        self._redo_stack.clear()

    def can_undo(self) -> bool:
        return bool(self._undo_stack)

    def can_redo(self) -> bool:
        return bool(self._redo_stack)

    def undo(self) -> Timeline | None:
        """Bir onceki duruma doner. Yeni Timeline nesnesini dondurur, yoksa None."""
        if not self._undo_stack:
            return None
        self._redo_stack.append(self._timeline.to_dict())
        snapshot = self._undo_stack.pop()
        self._timeline = Timeline.from_dict(snapshot)
        return self._timeline

    def redo(self) -> Timeline | None:
        """Geri alinan degisikligi tekrar uygular. Yeni Timeline nesnesini dondurur, yoksa None."""
        if not self._redo_stack:
            return None
        self._undo_stack.append(self._timeline.to_dict())
        snapshot = self._redo_stack.pop()
        self._timeline = Timeline.from_dict(snapshot)
        return self._timeline
