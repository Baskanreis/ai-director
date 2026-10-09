from app.ai.creative_studio_ai import ClipContext
from app.ai.scene_creative_director import build_scene_creative_plan, flatten_plan


def test_scene_plan_builds_independent_stack_per_scene():
    contexts=[
        ClipContext('c1',4.0,scene_type='hook',energy=.9,speech=True,style='viral_fast',tags=('impact',)),
        ClipContext('c2',7.0,scene_type='broll',energy=.25,music=True,style='cinematic',tags=('cinematic',)),
    ]
    plan=build_scene_creative_plan(contexts,items_per_scene=4)
    assert len(plan.stacks)==2
    assert all(stack.items for stack in plan.stacks)
    assert plan.stacks[0].clip_id != plan.stacks[1].clip_id
    assert plan.item_count <= 8


def test_scene_plan_flattens_to_existing_apply_contract():
    c=ClipContext('c1',5.0,scene_type='gaming',energy=.8,style='gaming')
    plan=build_scene_creative_plan([c],items_per_scene=3)
    rows=flatten_plan(plan)
    assert len(rows)==plan.item_count
    assert all({'asset_id','clip_id','start','duration','intensity'} <= set(r) for r in rows)


def test_scene_variants_are_deterministic_but_can_differ():
    c=ClipContext('c1',5.0,scene_type='gaming',energy=.8,style='gaming',tags=('glitch',))
    a=build_scene_creative_plan([c],items_per_scene=4,variant=0)
    b=build_scene_creative_plan([c],items_per_scene=4,variant=1)
    assert a.to_dict()==build_scene_creative_plan([c],items_per_scene=4,variant=0).to_dict()
    assert tuple(x.asset_id for x in a.stacks[0].items) != tuple(x.asset_id for x in b.stacks[0].items)
