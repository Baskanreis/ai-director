from app.ai.creative_studio_ai import ClipContext, rank_for_clip, build_preview_plan, generate_variations

def test_context_ranking_and_preview_plan():
    c=ClipContext('clip-1',8.0,scene_type='gaming',energy=.9,speech=True,music=True,faces=True,style='gaming',tags=('glitch','impact'))
    ranked=rank_for_clip(c,limit=12)
    assert len(ranked)==12
    plan=build_preview_plan(c,[a for a,_ in ranked[:5]])
    assert plan.clip_id=='clip-1' and 1 <= len(plan.cues) <= 5

def test_context_variations_are_deterministic_and_distinct():
    c=ClipContext('clip-2',6.0,style='cinematic',energy=.3)
    ranked=rank_for_clip(c,limit=15)
    plans=generate_variations(c,ranked,3)
    assert len(plans)==3
    assert len({tuple(x.asset_id for x in p.cues) for p in plans})>=2
