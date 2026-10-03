from app.timeline.model import Timeline, Clip
from app.pro import MarkerStore, ProfessionalEditEngine, RenderQueue, RenderJob

def make_timeline():
    t=Timeline(30)
    v=t.first_track("video")
    v.add(Clip("m","A",0,5,0))
    v.add(Clip("m","B",5,10,5))
    return t

def test_markers_roundtrip():
    s=MarkerStore(); m=s.add(2.5,"Hook",duration=1,note="open")
    s2=MarkerStore.from_dict(s.to_dict())
    assert s2.markers[0].time==2.5 and s2.markers[0].name=="Hook"

def test_roll_edit_changes_boundary_only():
    t=make_timeline(); e=ProfessionalEditEngine(t)
    r=e.roll("missing","missing",.1); assert not r.changed
    a,b=t.first_track("video").sorted_clips()
    r=e.roll(a.id,b.id,.5); assert r.changed
    assert abs(a.end-b.start)<1e-6

def test_nudge_uses_frames():
    t=make_timeline(); e=ProfessionalEditEngine(t)
    a=t.first_track("video").sorted_clips()[0]
    assert e.nudge(a.id,3).changed
    assert abs(a.start-.1)<1e-6

def test_snap():
    t=make_timeline(); e=ProfessionalEditEngine(t)
    assert e.snap(5.05,.1)==5

def test_render_queue_roundtrip():
    q=RenderQueue(); q.add(RenderJob("x.mp4"))
    q2=RenderQueue.from_dict(q.to_dict())
    assert q2.jobs[0].output_path=="x.mp4"

def test_project_editor_data_persists(tmp_path):
    from app.project.project import Project
    p=Project("Pro"); p.editor_data["markers"]=[{"time":3.0,"name":"Hook"}]
    path=tmp_path/"x.aidproj"; p.save(path)
    q=Project.load(path)
    assert q.editor_data["markers"][0]["name"]=="Hook"


def test_workspace_roundtrip_and_modes():
    from app.pro import EditingWorkspace
    w=EditingWorkspace(); w.select(["a","b"]); w.set_range(5,2); w.set_mode("ripple"); w.playhead=4.5
    r=EditingWorkspace.from_dict(w.to_dict())
    assert r.selected_clip_ids==["a","b"] and r.range_start==2 and r.range_end==5 and r.edit_mode=="ripple"


def test_match_frame_and_batch_edit():
    t=make_timeline(); e=ProfessionalEditEngine(t); c=t.tracks[0].clips[0]
    hit=e.match_frame(c.start+0.5, "V1")
    assert hit and hit["clip_id"]==c.id
    r=e.set_selected([c.id], gain_db=-3, speed=2)
    assert r.changed and c.gain_db==-3 and c.speed==2
