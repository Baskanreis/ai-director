from __future__ import annotations
import json
from PySide6.QtCore import Qt, QSettings, QSize, QTimer, QMimeData
from PySide6.QtGui import QDrag, QPixmap
from PySide6.QtWidgets import (QComboBox, QDialog, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QMessageBox, QPushButton, QSplitter, QTextEdit, QVBoxLayout, QCheckBox, QWidget,
    QFileDialog, QSlider)
from app.effects.pro_asset_library import catalog, search, CreativeAsset
from app.effects.asset_discovery import DiscoveryFilters, category_meta, visual_query, similar_assets, visual_similar_assets, category_counts
from app.effects.asset_timeline_bridge import AssetTimelineBridge, AssetAction
from app.effects.marketplace import builtin_packs, get_pack, export_pack
from app.ai.effects_director import CreativeDecision
from app.ai.creative_apply import apply_creative_pass, apply_creative_stack
from app.ai.creative_library_studio import preview_spec, recommend
from app.ai.creative_studio_ai import ClipContext, rank_for_clip, generate_variations
from app.ai.scene_creative_director import build_scene_creative_plan, flatten_plan
from app.ui.creative_preview import cached_asset_preview, render_asset_preview
from app.ui.live_creative_preview import LiveCreativePreview


class CreativeAssetList(QListWidget):
    def __init__(self, owner, parent=None):
        super().__init__(parent); self.owner = owner
        self.setMouseTracking(True); self.setDragEnabled(True); self._press_pos = None

    def mousePressEvent(self, event):
        self._press_pos = event.position().toPoint()
        super().mousePressEvent(event)

    def startDrag(self, supportedActions):  # noqa: N802
        item = self.currentItem()
        if not item: return
        aid = item.data(Qt.UserRole)
        mime = QMimeData(); mime.setData("application/x-ai-director-creative", str(aid).encode("utf-8"))
        drag = QDrag(self); drag.setMimeData(mime)
        icon = item.icon(); pix = icon.pixmap(QSize(264,148))
        if not pix.isNull(): drag.setPixmap(pix)
        drag.exec(Qt.CopyAction)


class CreativeLibraryDialog(QDialog):
    """50,000-item Creative Library + built-in Asset Marketplace/Pack Engine."""
    def __init__(self, timeline, selected_clip_id=None, parent=None):
        super().__init__(parent); self.timeline=timeline; self.selected_clip_id=selected_clip_id
        self.settings=QSettings("AI Director","AI Director")
        self.setWindowTitle("Creative Library Studio • 50K Asset Marketplace")
        self.resize(1180,760)
        root=QVBoxLayout(self)
        top=QHBoxLayout(); self.search_box=QLineEdit(); self.search_box.setPlaceholderText("Ara veya bir öğe seç: neon gaming transition, cinematic…")
        self.kind=QComboBox(); self.kind.addItem("Tür: Tümü", "")
        counts=category_counts()
        icon_map={"spark":"✨","transition":"↔️","motion":"🎞️","sticker":"🏷️","sound":"🔊","audio":"🎚️","subtitle":"CC","text":"T","color":"🎨","overlay":"◈","broll":"🎬","template":"▦","music":"🎵"}
        for k in sorted(counts):
            code, label, icon = category_meta(k); self.kind.addItem(f"{icon_map.get(icon, '•')} {code}  {label} ({counts[k]:,})",k)
        self.pack=QComboBox(); self.pack.addItem("Pack: Tümü", "")
        for p in builtin_packs(): self.pack.addItem(p.name, p.id)
        self.fav=QCheckBox("★ Favoriler")
        self.safe=QCheckBox("✓ Güvenli")
        top.addWidget(self.search_box,1); top.addWidget(self.kind); top.addWidget(self.pack); top.addWidget(self.fav); top.addWidget(self.safe); root.addLayout(top)
        filter_row=QHBoxLayout()
        self.intent=QComboBox(); self.intent.addItem("Intent: Tümü", "")
        self.intent.addItems(["hook","impact","cinematic","education","travel","gaming","social","podcast","creator"])
        self.mood=QComboBox(); self.mood.addItem("Mood: Tümü", ""); self.mood.addItems(["energetic","calm","dramatic","playful","clean","premium","neutral"])
        self.style=QComboBox(); self.style.addItem("Style: Tümü", ""); self.style.addItems(["neon","glitch","cinematic","minimal","bold","soft","retro","clean"])
        self.similar_btn=QPushButton("✨ Şuna Benzer (Görsel + AI)")
        self.clear_filters=QPushButton("Filtreleri Temizle")
        for w in (self.intent,self.mood,self.style,self.similar_btn,self.clear_filters): filter_row.addWidget(w)
        root.addLayout(filter_row)
        self.category_hint=QLabel("50K katalog • tüm 50.000 öğe erişilebilir • sayfa başına 300 • hover ile mikro-animasyon")
        self.category_hint.setStyleSheet("font-weight:700;padding:6px 2px")
        root.addWidget(self.category_hint)
        pager=QHBoxLayout()
        self.page_prev=QPushButton("‹ Önceki 300")
        self.page_next=QPushButton("Sonraki 300 ›")
        self.page_label=QLabel("Sayfa 1 / 1")
        self.page_label.setAlignment(Qt.AlignCenter)
        pager.addWidget(self.page_prev); pager.addWidget(self.page_label,1); pager.addWidget(self.page_next)
        root.addLayout(pager)
        split=QSplitter(Qt.Horizontal); root.addWidget(split,1)
        self.list=CreativeAssetList(self); self.list.setUniformItemSizes(True)
        self.list.setSelectionMode(QListWidget.ExtendedSelection); self.list.setViewMode(QListWidget.IconMode)
        self.list.setIconSize(QSize(132,74)); self.list.setGridSize(QSize(156,112)); self.list.setResizeMode(QListWidget.Adjust); self.list.setSpacing(6)
        split.addWidget(self.list)
        right=QVBoxLayout(); panel=QWidget(); panel.setLayout(right); split.addWidget(panel)
        self.title=QLabel("Öğe seç"); self.title.setStyleSheet("font-size:20px;font-weight:700")
        self.live_preview=LiveCreativePreview(); self.preview=self.live_preview.image
        self.meta=QLabel(); self.meta.setWordWrap(True); self.details=QTextEdit(); self.details.setReadOnly(True)
        right.addWidget(self.title); right.addWidget(self.live_preview); right.addWidget(self.meta); right.addWidget(self.details,1)
        self.favorite_btn=QPushButton("☆ Favoriye ekle"); self.apply_btn=QPushButton("Klibe Uygula"); self.insert_btn=QPushButton("Timeline'a Ekle"); self.variant_btn=QPushButton("Varyasyon Oluştur"); self.stack_btn=QPushButton("Seçilenleri Stack Uygula")
        self.ai_btn=QPushButton("AI Top-3 Öner"); self.auto_btn=QPushButton("AI Klip İçin Seç"); self.scenes_btn=QPushButton("AI Tüm Sahneleri Yönet")
        self.export_pack_btn=QPushButton("Seçili Pack'i Dışa Aktar"); self.close_btn=QPushButton("Kapat")
        for b in (self.favorite_btn,self.apply_btn,self.insert_btn,self.variant_btn,self.stack_btn,self.ai_btn,self.auto_btn,self.scenes_btn,self.export_pack_btn,self.close_btn): right.addWidget(b)
        self.hover_timer=QTimer(self); self.hover_timer.setSingleShot(True); self.hover_timer.setInterval(350); self.hover_timer.timeout.connect(self._hover_preview)
        self._hover_item=None
        self._page=0
        self._page_size=300
        self._result_assets=[]
        self.search_box.textChanged.connect(self._reset_page_and_refresh); self.kind.currentIndexChanged.connect(self._reset_page_and_refresh); self.pack.currentIndexChanged.connect(self._reset_page_and_refresh); self.fav.stateChanged.connect(self._reset_page_and_refresh); self.safe.stateChanged.connect(self._reset_page_and_refresh); self.intent.currentIndexChanged.connect(self._reset_page_and_refresh); self.mood.currentIndexChanged.connect(self._reset_page_and_refresh); self.style.currentIndexChanged.connect(self._reset_page_and_refresh); self.similar_btn.clicked.connect(self.find_similar); self.clear_filters.clicked.connect(self.reset_filters)
        self.page_prev.clicked.connect(self._previous_page)
        self.page_next.clicked.connect(self._next_page)
        self.list.currentItemChanged.connect(self.select); self.list.itemEntered.connect(self._hovered)
        self.auto_btn.clicked.connect(self.ai_for_clip); self.favorite_btn.clicked.connect(self.toggle_favorite); self.apply_btn.clicked.connect(self.apply); self.stack_btn.clicked.connect(self.apply_stack); self.ai_btn.clicked.connect(self.ai_recommend)
        self.close_btn.clicked.connect(self.close); self.scenes_btn.clicked.connect(self.ai_all_scenes); self.export_pack_btn.clicked.connect(self.export_selected_pack); self.refresh()

    def _favorites(self): return set(self.settings.value("creative/favorites", [], type=list))
    def _set_favorites(self, ids): self.settings.setValue("creative/favorites", sorted(ids))
    def _asset_by_id(self, aid): return next((a for a in catalog() if a.id==aid), None)

    def _reset_page_and_refresh(self, *args):
        self._page=0
        self.refresh()

    def _previous_page(self):
        if self._page > 0:
            self._page -= 1
            self.refresh()

    def _next_page(self):
        pages=max(1, (len(self._result_assets)+self._page_size-1)//self._page_size)
        if self._page + 1 < pages:
            self._page += 1
            self.refresh()

    def refresh(self):
        q=self.search_box.text().strip(); kind=self.kind.currentData() or None; favs=self._favorites()
        pack_id=self.pack.currentData() or None
        selected_pack=get_pack(pack_id) if pack_id else None
        filters=DiscoveryFilters(kind=kind, intent=self.intent.currentData() or None, mood=self.mood.currentData() or None, style=self.style.currentData() or None, safe_only=self.safe.isChecked(), favorites_only=self.fav.isChecked())
        if selected_pack:
            pack_ids={a.id for a in selected_pack.assets(limit=10000)}
            assets=visual_query(q,filters,50000) if q else [a for a in catalog(kind) if a.id in pack_ids]
            assets=[a for a in assets if a.id in pack_ids]
        else:
            assets=visual_query(q,filters,50000) if q else list(catalog(kind))
        self._result_assets=assets
        pages=max(1, (len(assets)+self._page_size-1)//self._page_size)
        self._page=min(self._page,pages-1)
        start=self._page*self._page_size
        shown=assets[start:start+self._page_size]
        self.list.clear()
        for a in shown:
            key=json.dumps(a.params,sort_keys=True,ensure_ascii=False)
            pm=cached_asset_preview(a.id,a.kind,a.name,key,132,74)
            item=QListWidgetItem(("★ " if a.id in favs else "")+a.name); item.setData(Qt.UserRole,a.id); item.setToolTip(" • ".join(a.tags)); item.setIcon(pm); item.setTextAlignment(Qt.AlignHCenter); self.list.addItem(item)
        pack_note=f" • Pack: {selected_pack.name} ({selected_pack.count():,})" if selected_pack else ""
        self.meta.setText(f"Toplam {len(assets):,} sonuç • Gösterilen {start+1 if assets else 0}–{min(start+len(shown),len(assets))} • Katalog: {len(catalog()):,} öğe{pack_note} • Sürükle-bırak aktif")
        self.page_label.setText(f"Sayfa {self._page+1:,} / {pages:,} • 300'lü sayfalar")
        self.page_prev.setEnabled(self._page > 0)
        self.page_next.setEnabled(self._page + 1 < pages)

    def find_similar(self):
        a=self._asset()
        if not a:
            QMessageBox.information(self,"Öğe seçilmedi","Önce bir preview seçin; ardından Şuna Benzer'e basın.")
            return
        rows=visual_similar_assets(a,30); ids={x.id for x,_ in rows}
        self.search_box.blockSignals(True); self.search_box.setText(a.name); self.search_box.blockSignals(False)
        self.list.clear()
        for x,score in rows:
            key=json.dumps(x.params,sort_keys=True,ensure_ascii=False); pm=cached_asset_preview(x.id,x.kind,x.name,key,132,74)
            item=QListWidgetItem(x.name); item.setData(Qt.UserRole,x.id); item.setToolTip(f"Benzerlik {score:.0%} • {' • '.join(x.tags)}"); item.setIcon(pm); item.setTextAlignment(Qt.AlignHCenter); self.list.addItem(item)
        self.meta.setText(f"'{a.name}' için en benzer {len(rows)} öğe • görsel karakter + metadata • hareket, yoğunluk, glow, kontrast, ritim ve stil")

    def reset_filters(self):
        for combo in (self.kind,self.pack,self.intent,self.mood,self.style): combo.setCurrentIndex(0)
        self.search_box.clear(); self.fav.setChecked(False); self.safe.setChecked(False); self.refresh()

    def export_selected_pack(self):
        pack_id=self.pack.currentData() or None
        if not pack_id:
            QMessageBox.information(self, "Pack seçilmedi", "Önce Pack listesinden bir paket seçin.")
            return
        pack=get_pack(pack_id)
        if not pack: return
        path,_=QFileDialog.getSaveFileName(self,"Creative Pack kaydet",f"{pack.id}.json","AI Director Pack (*.json)")
        if not path:return
        try:
            export_pack(path,pack.id)
            QMessageBox.information(self,"Pack hazır",f"{pack.name} paketi dışa aktarıldı.\n{pack.count():,} reçete.")
        except Exception as exc:
            QMessageBox.warning(self,"Pack dışa aktarılamadı",str(exc))

    def _asset(self):
        item=self.list.currentItem(); return self._asset_by_id(item.data(Qt.UserRole)) if item else None

    def select(self, current, previous=None):
        a=self._asset()
        if not a:return
        self._hover_item=current; self.title.setText(a.name); self.live_preview.set_asset(a)
        self.meta.setText(f"{a.kind.upper()} • {', '.join(a.tags)}\nLisans: {a.license}")
        spec=preview_spec(a); self.details.setPlainText(json.dumps({"preview":spec.__dict__,"params":a.params,"drag_drop":"timeline üzerine bırak"},ensure_ascii=False,indent=2))
        self.favorite_btn.setText("★ Favoriden çıkar" if a.id in self._favorites() else "☆ Favoriye ekle")

    def _hovered(self, item):
        self._hover_item=item; self.hover_timer.start()

    def _hover_preview(self):
        if self._hover_item is None:return
        self.list.setCurrentItem(self._hover_item)
        self.select(self._hover_item, None)
        if not self.live_preview.playing:self.live_preview.toggle()

    def toggle_favorite(self):
        a=self._asset()
        if not a:return
        favs=self._favorites(); favs.remove(a.id) if a.id in favs else favs.add(a.id); self._set_favorites(favs); self.refresh()

    def _apply_asset_at(self, asset_id: str, clip_id: str | None, start: float | None = None) -> bool:
        a=self._asset_by_id(asset_id)
        clip=self.timeline.find(clip_id) if clip_id else None
        if not a or not clip:return False
        start = clip.start if start is None else max(clip.start, min(float(start), clip.end))
        duration=min(max(.05,float(a.params.get("duration",.8))), max(.05, clip.end-start))
        decision=CreativeDecision(a.kind,a.id,start,min(clip.end,start+duration),1.0,"Creative Library drag/drop",1.0,dict(a.params))
        report=apply_creative_pass(self.timeline,type("Plan",(),{"decisions":[decision]})())
        if report.applied:
            self.settings.setValue("creative/last_used",a.id); return True
        return False

    def apply(self):
        a=self._asset()
        if not a or not self.selected_clip_id:
            QMessageBox.information(self,"Klip seçilmedi","Timeline'dan önce bir klip seçin."); return
        result=AssetTimelineBridge(self.timeline).apply(AssetAction("apply",a.id,self.selected_clip_id))
        if result.changed:
            self.settings.setValue("creative/last_used",a.id); self.accept()
        elif self._apply_asset_at(a.id,self.selected_clip_id):
            self.settings.setValue("creative/last_used",a.id); self.accept()
        else: QMessageBox.warning(self,"Uygulanamadı","Bu öğe mevcut timeline motorunda uygulanamadı.")

    def insert(self):
        a=self._asset()
        if not a:
            QMessageBox.information(self,"Öğe seçilmedi","Önce bir Asset seçin."); return
        at=0.0
        if self.selected_clip_id:
            found=self.timeline.find(self.selected_clip_id)
            if found: at=found[1].start
        track_id="A1" if a.kind in {"audio_fx","sfx","music"} else "V1"
        result=AssetTimelineBridge(self.timeline).apply(AssetAction("insert",a.id,target_track_id=track_id,at=at))
        if result.changed:
            self.settings.setValue("creative/last_used",a.id)
            self.meta.setText(f"Timeline'a eklendi • {a.name} • {track_id} • {at:.2f}s")
        else:
            QMessageBox.warning(self,"Eklenemedi","Asset bu konuma eklenemedi; çakışan bir klip olabilir.")

    def variant(self):
        a=self._asset()
        if not a or not self.selected_clip_id:
            QMessageBox.information(self,"Klip/öğe seçilmedi","Önce bir Asset ve timeline klibi seçin."); return
        result=AssetTimelineBridge(self.timeline).apply(AssetAction("variation",a.id,self.selected_clip_id,variant=1))
        if result.changed:
            self.settings.setValue("creative/last_used",a.id)
            self.meta.setText(f"Varyasyon #1 oluşturuldu • {a.name} • timeline'da non-destructive")
        else:
            QMessageBox.warning(self,"Varyasyon oluşturulamadı","Bu öğe için varyasyon uygulanamadı.")

    def _selected_assets(self):
        ids={i.data(Qt.UserRole) for i in self.list.selectedItems()}; all_assets={a.id:a for a in catalog()}; return [all_assets[i] for i in ids if i in all_assets]

    def ai_for_clip(self):
        if not self.selected_clip_id: QMessageBox.information(self,"Klip seçilmedi","Önce timeline'dan bir klip seçin."); return
        clip=self.timeline.find(self.selected_clip_id)
        if clip is None:return
        meta=getattr(clip,"metadata",{}) or {}; tags=tuple(meta.get("tags",()) or ())
        ctx=ClipContext(str(clip.id),float(clip.duration),str(meta.get("scene_type","general")),float(meta.get("energy",.55)),bool(meta.get("speech",False)),bool(meta.get("music",False)),bool(meta.get("faces",False)),tags,str(meta.get("platform","shorts")),str(meta.get("style","viral_fast")))
        ranked=rank_for_clip(ctx,limit=12); plans=generate_variations(ctx,ranked,3); ids={c.asset_id for c in plans[0].cues}
        self.list.clearSelection()
        for row in range(self.list.count()):
            if self.list.item(row).data(Qt.UserRole) in ids:self.list.item(row).setSelected(True)
        self.title.setText("AI Klip Reçetesi"); self.meta.setText(f"{len(ids)} öğe • {len(plans)} varyasyon • {ctx.style} • enerji {ctx.energy:.2f}")
        self.details.setPlainText(json.dumps({"primary":plans[0].to_dict(),"alternatives":[p.to_dict() for p in plans[1:]]},ensure_ascii=False,indent=2))

    def ai_all_scenes(self):
        video_track=self.timeline.first_track("video")
        if not video_track: QMessageBox.information(self,"Video yok","Timeline'da video klibi bulunamadı."); return
        contexts=[]
        for clip in video_track.sorted_clips():
            meta=getattr(clip,"metadata",{}) or {}
            contexts.append(ClipContext(str(clip.id),float(clip.duration),str(meta.get("scene_type","general")),float(meta.get("energy",.55)),bool(meta.get("speech",False)),bool(meta.get("music",False)),bool(meta.get("faces",False)),tuple(meta.get("tags",()) or ()),str(meta.get("platform","shorts")),str(meta.get("style","viral_fast"))))
        if not contexts:return
        plan=build_scene_creative_plan(contexts,items_per_scene=4,variant=0); rows=flatten_plan(plan); report=apply_creative_stack(self.timeline, rows)
        self.details.setPlainText(json.dumps(plan.to_dict(),ensure_ascii=False,indent=2)); self.title.setText("AI Scene Director"); self.meta.setText(f"{len(plan.stacks)} sahne • {plan.item_count} yaratıcı karar • {report.applied} uygulandı")
        if report.applied:self.settings.setValue("creative/last_scene_run",len(plan.stacks))

    def ai_recommend(self):
        q=self.search_box.text().strip() or self.kind.currentText(); recs=recommend(q,kind=self.kind.currentData() or None,limit=3); self.list.clearSelection(); ids={a.id for a in recs}
        for row in range(self.list.count()):
            if self.list.item(row).data(Qt.UserRole) in ids:self.list.item(row).setSelected(True)
        if recs:self.title.setText("AI Top-3: "+" • ".join(a.name for a in recs)); self.meta.setText("AI önerisi • 3 farklı yaratıcı seçenek")

    def apply_stack(self):
        assets=self._selected_assets()
        if not assets or not self.selected_clip_id: QMessageBox.information(self,"Öğe/Klip seçilmedi","Bir klip ve en az bir Creative Library öğesi seçin."); return
        clip=self.timeline.find(self.selected_clip_id)
        if clip is None:return
        step=max(.05,min(.8,clip.duration/max(1,len(assets)))); items=[]
        for idx,a in enumerate(assets): items.append({"asset_id":a.id,"clip_id":clip.id,"start":clip.start+idx*step,"duration":min(step,clip.end-(clip.start+idx*step)),"intensity":1.0})
        report=apply_creative_stack(self.timeline,items)
        if report.applied:self.settings.setValue("creative/last_used",assets[-1].id); self.accept()
        else: QMessageBox.warning(self,"Uygulanamadı","Seçilen öğeler mevcut timeline motorunda uygulanamadı.")
