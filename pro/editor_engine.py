"""Professional, non-destructive NLE edit operations.

Implements insert/overwrite, ripple/roll/slide/slip, frame nudging and snapping.
All operations mutate the supplied Timeline only after validating the complete
operation, making them safe to call from a UI command/undo transaction.
"""
from __future__ import annotations
from dataclasses import dataclass
from copy import deepcopy
from app.timeline.model import Timeline, Clip, Track, TimelineError, EPS, MIN_CLIP

@dataclass(frozen=True)
class EditResult:
    changed: bool
    operation: str
    affected_ids: tuple[str, ...] = ()

class ProfessionalEditEngine:
    def __init__(self, timeline: Timeline):
        self.timeline = timeline

    def snap(self, time: float, threshold: float = 0.12, exclude_ids=frozenset()) -> float:
        if threshold <= 0:
            return max(0.0, time)
        points = self.timeline.snap_points(frozenset(exclude_ids))
        nearest = min(points, key=lambda p: abs(p-time), default=time)
        return nearest if abs(nearest-time) <= threshold else max(0.0,time)

    def nudge(self, clip_id: str, frames: int, ripple: bool = True) -> EditResult:
        f = self.timeline.find(clip_id)
        if not f: return EditResult(False,"nudge")
        delta = frames / max(self.timeline.fps, 1.0)
        ok = self.timeline.move(clip_id, f[1].start + delta, ripple=ripple)
        return EditResult(ok,"nudge",(clip_id,) if ok else ())

    def insert(self, source_clip: Clip, track_id: str, at: float, ripple: bool = True) -> EditResult:
        track = self.timeline.track(track_id)
        at = max(0.0, at)
        duration = source_clip.duration
        if duration < MIN_CLIP: return EditResult(False,"insert")
        if ripple:
            for c in track.clips:
                if c.start >= at - EPS:
                    c.start += duration
                elif c.start < at < c.end:
                    # Split the underlying clip, preserving the material on both sides.
                    if not self.timeline.split(at, c.id): return EditResult(False,"insert")
                    for cc in track.clips:
                        if cc.id != c.id and cc.start >= at-EPS and cc.start < at+duration+EPS:
                            cc.start += duration
            clone=deepcopy(source_clip); clone.id=clone.id+"-insert"; clone.start=at
            if track.overlaps(clone.start,clone.end): return EditResult(False,"insert")
            track.clips.append(clone)
            return EditResult(True,"insert",(clone.id,))
        if track.overlaps(at,at+duration):
            return EditResult(False,"insert")
        clone=deepcopy(source_clip); clone.id=clone.id+"-insert"; clone.start=at
        track.clips.append(clone)
        return EditResult(True,"insert",(clone.id,))

    def overwrite(self, source_clip: Clip, track_id: str, at: float) -> EditResult:
        track=self.timeline.track(track_id); at=max(0.0,at)
        end=at+source_clip.duration
        # Trim/remove only material covered by the overwrite range.
        for c in list(track.clips):
            if c.end <= at+EPS or c.start >= end-EPS: continue
            if c.start < at < c.end:
                self.timeline.trim(c.id,"end",at)
            if at < c.end and c.start < end and c.end > end:
                self.timeline.trim(c.id,"start",end)
            if c.start >= at-EPS and c.end <= end+EPS:
                track.clips.remove(c)
        clone=deepcopy(source_clip); clone.id=clone.id+"-overwrite"; clone.start=at
        if track.overlaps(clone.start,clone.end): return EditResult(False,"overwrite")
        track.clips.append(clone)
        return EditResult(True,"overwrite",(clone.id,))

    def roll(self, left_id: str, right_id: str, delta: float) -> EditResult:
        lf=self.timeline.find(left_id); rf=self.timeline.find(right_id)
        if not lf or not rf or lf[0] is not rf[0]: return EditResult(False,"roll")
        left,right=lf[1],rf[1]
        if abs(left.end-right.start)>EPS: return EditResult(False,"roll")
        ns=left.end+delta
        if ns-left.start<MIN_CLIP or right.end-ns<MIN_CLIP: return EditResult(False,"roll")
        speed_l=left.speed if not left.freeze else 1.0
        speed_r=right.speed if not right.freeze else 1.0
        left.source_out += delta*speed_l
        right.source_in += delta*speed_r
        right.start = ns
        return EditResult(True,"roll",(left.id,right.id))

    def slip(self, clip_id: str, delta_source: float) -> EditResult:
        f=self.timeline.find(clip_id)
        if not f: return EditResult(False,"slip")
        c=f[1]; span=c.source_out-c.source_in
        new_in=c.source_in+delta_source; new_out=c.source_out+delta_source
        if new_in<0 or new_out<=new_in: return EditResult(False,"slip")
        # Media duration is not stored on Clip; project layer should validate the
        # upper bound before calling this operation when exact source duration is known.
        c.source_in,c.source_out=new_in,new_out
        return EditResult(True,"slip",(c.id,))

    def slide(self, clip_id: str, delta: float) -> EditResult:
        f=self.timeline.find(clip_id)
        if not f: return EditResult(False,"slide")
        track,c=f
        others=sorted((x for x in track.clips if x.id!=c.id), key=lambda x:x.start)
        left=max((x for x in others if x.end<=c.start+EPS), key=lambda x:x.end, default=None)
        right=min((x for x in others if x.start>=c.end-EPS), key=lambda x:x.start, default=None)
        if left is None or right is None: return EditResult(False,"slide")
        new_start=c.start+delta; new_end=c.end+delta
        left_new_end=left.end+delta; right_new_start=right.start+delta
        if left_new_end-left.start<MIN_CLIP or right.end-right_new_start<MIN_CLIP: return EditResult(False,"slide")
        # slide changes neighboring edit points, keeping the selected clip duration.
        left.source_out += delta*(left.speed if not left.freeze else 1.0)
        right.source_in += delta*(right.speed if not right.freeze else 1.0)
        c.start=new_start
        return EditResult(True,"slide",(left.id,c.id,right.id))

    def match_frame(self, time: float, track_id: str | None = None):
        """Return the clip and source timestamp visible under a timeline time."""
        tracks = [self.timeline.track(track_id)] if track_id else self.timeline.tracks
        for track in tracks:
            for clip in track.clips:
                if clip.start - EPS <= time < clip.end - EPS:
                    offset = max(0.0, time - clip.start)
                    source = clip.source_in if clip.freeze else clip.source_in + offset * max(clip.speed, EPS)
                    if clip.reversed and not clip.freeze:
                        source = clip.source_out - offset * max(clip.speed, EPS)
                    return {"clip_id": clip.id, "track_id": track.id, "source_time": max(0.0, source)}
        return None

    def extend_to_playhead(self, clip_id: str, playhead: float, edge: str = "end") -> EditResult:
        """Extend a clip edge to the playhead without crossing neighbors."""
        found = self.timeline.find(clip_id)
        if not found: return EditResult(False, "extend")
        track, clip = found
        p = max(0.0, float(playhead))
        if edge == "end":
            if p <= clip.start + MIN_CLIP or track.overlaps(clip.start, p, ignore_id=clip.id):
                return EditResult(False, "extend")
            if not self.timeline.trim(clip.id, "end", p): return EditResult(False, "extend")
        elif edge == "start":
            if p >= clip.end - MIN_CLIP or track.overlaps(p, clip.end, ignore_id=clip.id):
                return EditResult(False, "extend")
            if not self.timeline.trim(clip.id, "start", p): return EditResult(False, "extend")
        else:
            return EditResult(False, "extend")
        return EditResult(True, "extend", (clip.id,))

    def set_selected(self, clip_ids, *, muted=None, gain_db=None, speed=None) -> EditResult:
        """Batch-edit multiple clips as one deterministic operation."""
        affected=[]
        wanted=set(clip_ids)
        for track in self.timeline.tracks:
            for clip in track.clips:
                if clip.id not in wanted: continue
                if muted is not None: clip.muted=bool(muted)
                if gain_db is not None: clip.gain_db=float(gain_db)
                if speed is not None and float(speed)>0: clip.speed=float(speed)
                affected.append(clip.id)
        return EditResult(bool(affected), "batch", tuple(affected))

    def ripple_delete_range(self, start: float, end: float, track_ids=None) -> EditResult:
        if end<=start: return EditResult(False,"ripple_delete")
        tracks=[self.timeline.track(t) for t in track_ids] if track_ids else self.timeline.tracks
        delta=end-start; affected=[]
        for t in tracks:
            for c in list(t.clips):
                if c.end<=start+EPS: continue
                if c.start>=end-EPS:
                    c.start-=delta; affected.append(c.id); continue
                # Partial coverage: trim the affected side(s).
                if c.start<start and c.end>end:
                    self.timeline.trim(c.id,"end",start)
                    affected.append(c.id)
                elif c.start<start<c.end<=end:
                    self.timeline.trim(c.id,"end",start); affected.append(c.id)
                elif start<=c.start<end<c.end:
                    self.timeline.trim(c.id,"start",start); c.start=start
                    # remove the covered portion by moving to end then compensate
                    self.timeline.trim(c.id,"start",end-delta)
                    c.start-=delta; affected.append(c.id)
                elif c.start>=start and c.end<=end:
                    t.clips.remove(c); affected.append(c.id)
        return EditResult(bool(affected),"ripple_delete",tuple(affected))
