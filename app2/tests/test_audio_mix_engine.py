from app.audio.mix_engine import AudioMixEngine

def test_mix_plan():
    r=AudioMixEngine().mix_plan({'cues':[{'kind':'music','asset_id':'m','start':0,'end':20,'gain_db':-14},{'kind':'sfx','asset_id':'s','start':3,'end':3.5,'gain_db':-6}]},[{'start':2,'end':5},{'start':8,'end':10}],20)
    assert len(r['cues'])==2 and len(r['voice_ducking'])==2 and r['qa']['status']=='pass'

def test_merge():
    r=AudioMixEngine().voice_ducking([{'start':0,'end':2},{'start':1.5,'end':4}],10)
    assert len(r)==1 and r[0].end==4

def test_qa():
    r=AudioMixEngine().mix_plan({'cues':[{'kind':'sfx','asset_id':'x','start':0,'end':15,'gain_db':5}]},[],20)
    assert r['qa']['status']=='warning'
