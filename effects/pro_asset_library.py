"""Professional, parameterized creative toolkit.

This is an original, FFmpeg-friendly toolkit inspired by common NLE workflows.
It deliberately does not bundle proprietary CapCut/Premiere assets, presets or
fonts. Users can add licensed packs through the same schema.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Literal

Kind = Literal["effect", "transition", "motion", "text", "sfx", "music", "audio_fx", "overlay", "filter", "sticker", "template"]

@dataclass(frozen=True)
class CreativeAsset:
    id: str
    name: str
    kind: Kind
    tags: tuple[str, ...]
    params: dict
    license: str = "AI Director Original / user-importable"

ASSETS = [
    CreativeAsset("effect.cinematic", "Cinematic Grade", "effect", ("cinematic","film","story"), {"preset":"cinematic"}),
    CreativeAsset("effect.vivid", "Vivid Social", "effect", ("social","bright","vivid"), {"preset":"social_vivid"}),
    CreativeAsset("effect.noir", "Noir", "effect", ("dark","dramatic","noir"), {"preset":"noir"}),
    CreativeAsset("effect.skin_soft", "Skin Soft", "effect", ("portrait","skin","talking_head"), {"preset":"skin_soft"}),
    CreativeAsset("effect.shorts_energy", "Shorts Energy", "effect", ("shorts","viral","energy"), {"preset":"shorts_energy"}),
    CreativeAsset("transition.crossfade", "Cross Dissolve", "transition", ("clean","cinematic","soft"), {"kind":"crossfade","duration":0.35}),
    CreativeAsset("transition.fade_black", "Fade Through Black", "transition", ("cinematic","dramatic"), {"kind":"fade_black","duration":0.25}),
    CreativeAsset("transition.flash", "Flash Cut", "transition", ("energy","beat","shorts"), {"kind":"flash","duration":0.10}),
    CreativeAsset("transition.zoom", "Zoom Cut", "transition", ("social","energy","punch"), {"kind":"zoom","duration":0.18}),
    CreativeAsset("motion.punch_in", "Punch In", "motion", ("emphasis","speaker","hook"), {"scale_from":1.0,"scale_to":1.055,"duration":0.45}),
    CreativeAsset("motion.punch_out", "Punch Out", "motion", ("reveal","emphasis"), {"scale_from":1.055,"scale_to":1.0,"duration":0.45}),
    CreativeAsset("motion.ken_burns", "Ken Burns", "motion", ("photo","story","cinematic"), {"scale_from":1.0,"scale_to":1.035,"duration":3.0}),
    CreativeAsset("motion.shake_light", "Micro Shake", "motion", ("impact","music","shorts"), {"amplitude":2.0,"duration":0.16}),
    CreativeAsset("text.clean_caption", "Clean Captions", "text", ("caption","subtitle","clean"), {"font_family":"system","weight":700,"size":46,"animation":"word_pop"}),
    CreativeAsset("text.bold_hook", "Bold Hook", "text", ("hook","shorts","social"), {"font_family":"system","weight":900,"size":58,"animation":"word_pop"}),
    CreativeAsset("text.kinetic", "Kinetic Type", "text", ("music","lyrics","energetic"), {"font_family":"system","weight":800,"size":52,"animation":"kinetic"}),
    CreativeAsset("text.minimal_title", "Minimal Title", "text", ("title","cinematic","documentary"), {"font_family":"system","weight":600,"size":54,"animation":"fade_up"}),
    CreativeAsset("audio_fx.voice_clean", "Voice Clean", "audio_fx", ("voice","podcast","dialogue"), {"denoise":10,"compressor":True,"limiter":True,"voice_enhance":True}),
    CreativeAsset("audio_fx.duck_music", "Auto Duck Music", "audio_fx", ("dialogue","music","mix"), {"duck_db":-10,"attack":0.08,"release":0.35}),
    CreativeAsset("audio_fx.punch_sfx", "Impact Accent", "sfx", ("impact","hit","shorts"), {"generator":"impact"}),
    CreativeAsset("audio_fx.whoosh", "Whoosh Accent", "sfx", ("transition","motion","swipe"), {"generator":"whoosh"}),
    CreativeAsset("audio_fx.rise", "Riser Accent", "sfx", ("build","hook","transition"), {"generator":"riser"}),
]


# Expanded original catalog: effects, transitions, motion, typography and audio FX.
ASSETS.extend([
    CreativeAsset("effect.viral_pop", "Viral Pop", "effect", ("viral","shorts","creator"), {"preset":"viral_pop"}),
    CreativeAsset("effect.cyberpunk", "Cyberpunk", "effect", ("gaming","neon","tech"), {"preset":"cyberpunk"}),
    CreativeAsset("effect.golden_hour", "Golden Hour", "effect", ("travel","warm","sunset"), {"preset":"golden_hour"}),
    CreativeAsset("effect.beauty_soft", "Beauty Soft", "effect", ("portrait","beauty","skin"), {"preset":"beauty_soft"}),
    CreativeAsset("effect.food_pop", "Food Pop", "effect", ("food","crisp","social"), {"preset":"food_pop"}),
    CreativeAsset("effect.gaming_neon", "Gaming Neon", "effect", ("gaming","rgb","energy"), {"preset":"gaming_neon"}),
    CreativeAsset("effect.podcast_clean", "Podcast Clean", "effect", ("podcast","talking_head","clean"), {"preset":"podcast_clean"}),
    CreativeAsset("effect.teal_cinema", "Teal Cinema", "effect", ("cinematic","film","teal"), {"preset":"teal_cinema"}),
    CreativeAsset("effect.gold_cinema", "Gold Cinema", "effect", ("cinematic","film","gold"), {"preset":"gold_cinema"}),
    CreativeAsset("effect.low_light_recover", "Low Light Recover", "effect", ("night","recovery","portrait"), {"preset":"low_light_recover"}),
    CreativeAsset("transition.whip_left", "Whip Left", "transition", ("energy","motion","shorts"), {"animation":"motion.whip_left"}),
    CreativeAsset("transition.whip_right", "Whip Right", "transition", ("energy","motion","shorts"), {"animation":"motion.whip_right"}),
    CreativeAsset("transition.blur_push", "Blur Push", "transition", ("cinematic","motion"), {"animation":"transition.blur_push"}),
    CreativeAsset("transition.spin", "Spin Cut", "transition", ("gaming","energy"), {"animation":"transition.spin"}),
    CreativeAsset("transition.flash_white", "White Flash", "transition", ("impact","beat"), {"animation":"transition.flash_white"}),
    CreativeAsset("motion.punch_fast", "Fast Punch In", "motion", ("hook","impact","shorts"), {"animation":"motion.punch_fast"}),
    CreativeAsset("motion.parallax", "Parallax Drift", "motion", ("broll","photo","cinematic"), {"animation":"motion.parallax"}),
    CreativeAsset("motion.float", "Float", "motion", ("aesthetic","product"), {"animation":"motion.float"}),
    CreativeAsset("motion.shake_medium", "Impact Shake", "motion", ("impact","beat","gaming"), {"animation":"motion.shake_medium"}),
    CreativeAsset("text.typewriter", "Typewriter", "text", ("title","story","minimal"), {"animation":"text.typewriter","size":52}),
    CreativeAsset("text.glitch", "Glitch Caption", "text", ("gaming","tech","impact"), {"animation":"text.glitch","size":54}),
    CreativeAsset("text.neon", "Neon Pulse", "text", ("music","gaming","night"), {"animation":"text.neon","size":56}),
    CreativeAsset("text.highlight_sweep", "Highlight Sweep", "text", ("education","caption","explain"), {"animation":"text.highlight_sweep","size":48}),
    CreativeAsset("text.bounce_word", "Bounce Word", "text", ("fun","caption","viral"), {"animation":"text.bounce_word","size":52}),
    CreativeAsset("overlay.film_grain", "Film Grain", "motion", ("film","texture","cinematic"), {"animation":"overlay.film_grain"}),
    CreativeAsset("overlay.light_leak", "Light Leak", "motion", ("dream","travel","aesthetic"), {"animation":"overlay.light_leak"}),
    CreativeAsset("audio_fx.voice_broadcast", "Voice Broadcast", "audio_fx", ("voice","radio","podcast"), {"eq":"broadcast","compressor":True,"limiter":True}),
    CreativeAsset("audio_fx.voice_warm", "Voice Warm", "audio_fx", ("voice","podcast","story"), {"eq":"warm","compressor":True,"limiter":True}),
    CreativeAsset("audio_fx.music_sidechain", "Music Sidechain", "audio_fx", ("music","ducking","beat"), {"duck_db":-7,"attack":0.04,"release":0.22}),
    CreativeAsset("audio_fx_music_riser", "Generated Riser", "sfx", ("riser","build","tension"), {"file":"sfx_digital_up.wav"}),
    CreativeAsset("audio_fx_sub_drop", "Sub Drop", "sfx", ("impact","drop","shorts"), {"file":"sfx_sub_drop.wav"}),
    CreativeAsset("audio_fx_laser", "Laser Blip", "sfx", ("gaming","tech","transition"), {"file":"sfx_laser.wav"}),
    CreativeAsset("audio_fx_camera", "Camera Snap", "sfx", ("camera","photo","transition"), {"file":"sfx_camera.wav"}),
    CreativeAsset("audio_fx_coin", "Coin Spark", "sfx", ("reward","gaming","success"), {"file":"sfx_coin.wav"}),
])


def catalog(kind: str | None = None) -> list[CreativeAsset]:
    return [a for a in ASSETS if kind is None or a.kind == kind]


def search(query: str, kind: str | None = None, limit: int = 20) -> list[CreativeAsset]:
    tokens = {x.strip().lower() for x in query.replace(",", " ").split() if x.strip()}
    scored = []
    for asset in catalog(kind):
        hay = {asset.id.lower(), asset.name.lower(), *asset.tags}
        score = sum(2 if t in asset.name.lower() else 1 for t in tokens if any(t in h for h in hay))
        if score:
            scored.append((score, asset))
    return [a for _, a in sorted(scored, key=lambda x: (-x[0], x[1].name))[:limit]]


def manifest() -> list[dict]:
    return [asdict(a) for a in ASSETS]

# v2.28 Mega Creative Library -------------------------------------------------
# Metadata-first, original presets. No proprietary CapCut/Premiere assets.
_MEGA = []
def _add(kind, prefix, rows):
    for slug, name, tags, params in rows:
        _MEGA.append(CreativeAsset(f"{prefix}.{slug}", name, kind, tuple(tags), params))

_add("effect", "effect", [
 ("warm_skin","Warm Skin",["portrait","beauty","skin"],{"preset":"warm_skin"}),
 ("cool_clean","Cool Clean",["clean","modern","social"],{"preset":"cool_clean"}),
 ("matte_film","Matte Film",["film","cinematic","matte"],{"preset":"matte_film"}),
 ("bleach_bypass","Bleach Bypass",["cinema","dramatic","film"],{"preset":"bleach_bypass"}),
 ("vintage_90s","90s Vintage",["retro","vintage","nostalgia"],{"preset":"vintage_90s"}),
 ("vhs","VHS",["retro","vhs","glitch"],{"preset":"vhs"}),
 ("dreamy","Dreamy Glow",["dream","soft","aesthetic"],{"preset":"dreamy"}),
 ("moody_blue","Moody Blue",["moody","night","cinema"],{"preset":"moody_blue"}),
 ("orange_teal","Orange Teal",["cinema","travel","commercial"],{"preset":"orange_teal"}),
 ("high_contrast","High Contrast",["impact","shorts","bold"],{"preset":"high_contrast"}),
 ("pastel","Pastel",["soft","lifestyle","beauty"],{"preset":"pastel"}),
 ("mono","Monochrome",["blackwhite","cinema","dramatic"],{"preset":"mono"}),
 ("infrared","Infrared",["experimental","music","art"],{"preset":"infrared"}),
 ("duotone","Duotone",["graphic","music","poster"],{"preset":"duotone"}),
 ("chromatic","Chromatic Aberration",["glitch","music","impact"],{"preset":"chromatic"}),
 ("film_bloom","Film Bloom",["film","glow","cinema"],{"preset":"film_bloom"}),
 ("hdr_pop","HDR Pop",["food","product","social"],{"preset":"hdr_pop"}),
 ("night_vision","Night Vision",["gaming","night","tech"],{"preset":"night_vision"}),
])

_add("transition", "transition", [
 ("slide_up","Slide Up",["clean","social","motion"],{"kind":"slide_up","duration":.22}),
 ("slide_down","Slide Down",["clean","social","motion"],{"kind":"slide_down","duration":.22}),
 ("slide_left","Slide Left",["social","motion"],{"kind":"slide_left","duration":.22}),
 ("slide_right","Slide Right",["social","motion"],{"kind":"slide_right","duration":.22}),
 ("push_left","Push Left",["fast","shorts","motion"],{"kind":"push_left","duration":.18}),
 ("push_right","Push Right",["fast","shorts","motion"],{"kind":"push_right","duration":.18}),
 ("push_up","Push Up",["fast","shorts"],{"kind":"push_up","duration":.18}),
 ("doorway","Doorway",["cinematic","reveal"],{"kind":"doorway","duration":.4}),
 ("circle_open","Circle Open",["fun","reveal"],{"kind":"circle_open","duration":.35}),
 ("circle_close","Circle Close",["fun","reveal"],{"kind":"circle_close","duration":.35}),
 ("pixelize","Pixelize",["gaming","tech","glitch"],{"kind":"pixelize","duration":.25}),
 ("morph","Morph",["modern","smooth","ai"],{"kind":"morph","duration":.45}),
 ("rgb_split","RGB Split",["glitch","gaming","music"],{"kind":"rgb_split","duration":.12}),
 ("strobe","Strobe Cut",["beat","impact","music"],{"kind":"strobe","duration":.08}),
 ("light_leak","Light Leak",["dream","travel","aesthetic"],{"kind":"light_leak","duration":.35}),
 ("lens_flash","Lens Flash",["camera","cinema","impact"],{"kind":"lens_flash","duration":.18}),
 ("digital_wipe","Digital Wipe",["tech","gaming","creator"],{"kind":"digital_wipe","duration":.2}),
])

_add("motion", "motion", [
 ("zoom_in_soft","Soft Zoom In",["cinema","emphasis"],{"scale_from":1,"scale_to":1.03,"duration":1.2}),
 ("zoom_in_fast","Fast Zoom In",["hook","impact"],{"scale_from":1,"scale_to":1.09,"duration":.28}),
 ("zoom_out_reveal","Zoom Out Reveal",["reveal","cinema"],{"scale_from":1.08,"scale_to":1,"duration":.55}),
 ("drift_left","Drift Left",["broll","aesthetic"],{"x_from":.52,"x_to":.47,"duration":3}),
 ("drift_right","Drift Right",["broll","aesthetic"],{"x_from":.48,"x_to":.53,"duration":3}),
 ("tilt_up","Tilt Up",["cinematic","reveal"],{"y_from":.55,"y_to":.45,"duration":1.5}),
 ("tilt_down","Tilt Down",["cinematic","reveal"],{"y_from":.45,"y_to":.55,"duration":1.5}),
 ("handheld","Handheld",["documentary","energy"],{"amplitude":1.5,"frequency":7}),
 ("impact_zoom","Impact Zoom",["impact","beat","shorts"],{"scale_from":1,"scale_to":1.12,"duration":.14}),
 ("rubber_band","Rubber Band",["fun","meme","viral"],{"animation":"rubber_band"}),
 ("bounce","Bounce",["fun","caption","social"],{"animation":"bounce"}),
 ("elastic","Elastic",["fun","social"],{"animation":"elastic"}),
 ("swing","Swing",["title","fashion","social"],{"animation":"swing"}),
 ("float_up","Float Up",["aesthetic","beauty"],{"animation":"float_up"}),
 ("jitter","Jitter",["glitch","gaming","music"],{"animation":"jitter"}),
])

_add("text", "text", [
 ("word_pop_pro","Word Pop Pro",["caption","viral","kinetic"],{"animation":"word_pop","weight":900,"size":54}),
 ("karaoke","Karaoke Highlight",["lyrics","music","caption"],{"animation":"karaoke","weight":800,"size":50}),
 ("karaoke_box","Karaoke Box",["lyrics","caption","shorts"],{"animation":"karaoke_box","weight":800,"size":48}),
 ("minimal_lower","Minimal Lower Third",["lowerthird","corporate","clean"],{"animation":"fade_up","weight":600,"size":38}),
 ("creator_tag","Creator Tag",["social","branding","creator"],{"animation":"slide_up","weight":800,"size":40}),
 ("number_counter","Number Counter",["stats","finance","education"],{"animation":"counter","weight":800,"size":58}),
 ("quote","Quote Card",["quote","story","cinema"],{"animation":"fade_up","weight":700,"size":52}),
 ("comic","Comic Impact",["meme","fun","impact"],{"animation":"pop","weight":900,"size":60}),
 ("retro","Retro Title",["retro","vhs","nostalgia"],{"animation":"typewriter","weight":800,"size":56}),
 ("gradient","Gradient Caption",["beauty","music","social"],{"animation":"word_pop","weight":800,"size":52}),
 ("outline","Outline Caption",["gaming","impact","caption"],{"animation":"bounce","weight":900,"size":54}),
 ("shadow","Heavy Shadow",["shorts","outdoor","social"],{"animation":"word_pop","weight":900,"size":56}),
])

_add("overlay", "overlay", [
 ("dust","Dust Particles",["film","cinema","texture"],{"blend":"screen","opacity":.2}),
 ("bokeh","Bokeh",["beauty","dream","cinema"],{"blend":"screen","opacity":.22}),
 ("rain","Rain",["moody","night","story"],{"blend":"screen","opacity":.18}),
 ("snow","Snow",["winter","travel","cinema"],{"blend":"screen","opacity":.22}),
 ("confetti","Confetti",["celebration","fun","social"],{"blend":"screen","opacity":.35}),
 ("hearts","Hearts",["love","beauty","social"],{"blend":"screen","opacity":.3}),
 ("sparkles","Sparkles",["beauty","fashion","music"],{"blend":"screen","opacity":.3}),
 ("scanlines","Scanlines",["vhs","tech","gaming"],{"blend":"screen","opacity":.2}),
 ("vignette_soft","Soft Vignette",["cinema","portrait"],{"blend":"multiply","amount":.22}),
 ("vignette_heavy","Heavy Vignette",["dramatic","cinema"],{"blend":"multiply","amount":.4}),
 ("paper","Paper Texture",["documentary","craft","story"],{"blend":"multiply","opacity":.15}),
 ("halftone","Halftone",["comic","graphic","retro"],{"blend":"multiply","opacity":.2}),
])

_add("audio_fx", "audio_fx", [
 ("voice_podcast","Podcast Voice",["voice","podcast","speech"],{"eq":"podcast","compressor":True,"deesser":True,"limiter":True}),
 ("voice_clarity","Clarity Voice",["voice","dialogue","creator"],{"eq":"clarity","compressor":True,"limiter":True}),
 ("voice_deesser","De-Esser",["voice","speech"],{"deesser":True}),
 ("music_duck_aggressive","Aggressive Duck",["music","voice","shorts"],{"duck_db":-13,"attack":.04,"release":.28}),
 ("music_duck_soft","Soft Duck",["music","voice","cinema"],{"duck_db":-5,"attack":.12,"release":.5}),
 ("beat_pump","Beat Pump",["music","beat","energy"],{"amount":.12,"release":.18}),
 ("bass_boost","Bass Boost",["music","gaming","impact"],{"low_shelf_db":4}),
 ("radio","Radio",["voice","retro","effect"],{"preset":"radio"}),
 ("telephone","Telephone",["voice","retro","effect"],{"preset":"telephone"}),
 ("megaphone","Megaphone",["voice","meme","impact"],{"preset":"megaphone"}),
])

_add("filter", "filter", [
 ("sharpen","Smart Sharpen",["detail","social","food"],{"amount":.25}),
 ("denoise","Video Denoise",["lowlight","clean","recovery"],{"amount":.2}),
 ("deband","Deband",["gradient","sky","cinema"],{"amount":.25}),
 ("glow","Soft Glow",["beauty","dream","music"],{"amount":.18}),
 ("motion_blur","Motion Blur",["transition","sports","energy"],{"amount":.35}),
 ("chromatic","Chromatic Fringe",["glitch","music","gaming"],{"amount":.18}),
])


_add("sticker", "sticker", [
 ("arrow","Arrow",["pointer","tutorial","education"],{"shape":"arrow"}),
 ("circle","Circle Marker",["highlight","tutorial"],{"shape":"circle"}),
 ("star","Star",["fun","celebration"],{"shape":"star"}),
 ("spark","Spark",["impact","beauty"],{"shape":"spark"}),
 ("check","Check Mark",["education","success"],{"shape":"check"}),
 ("x","X Mark",["meme","reaction"],{"shape":"x"}),
 ("question","Question",["reaction","education"],{"shape":"question"}),
 ("fire","Fire",["viral","hype"],{"shape":"fire"}),
 ("heart","Heart",["love","beauty"],{"shape":"heart"}),
 ("wow","WOW",["reaction","shorts"],{"shape":"wow"}),
])
_add("template", "template", [
 ("podcast","Podcast Viral",["podcast","talking_head","shorts"],{"layout":"speaker_caption_broll"}),
 ("gaming","Gaming Highlight",["gaming","clip","shorts"],{"layout":"facecam_gameplay"}),
 ("vlog","Vlog Story",["vlog","travel","lifestyle"],{"layout":"hook_broll_payoff"}),
 ("product","Product Ad",["product","commercial","social"],{"layout":"problem_demo_cta"}),
 ("fashion","Fashion Reel",["fashion","beauty","reel"],{"layout":"beat_cuts"}),
 ("travel","Travel Reel",["travel","cinematic","broll"],{"layout":"montage"}),
 ("education","Explainer",["education","tutorial","caption"],{"layout":"hook_steps_summary"}),
 ("story","Storytime",["story","talking_head","retention"],{"layout":"hook_context_payoff"}),
 ("meme","Meme Short",["meme","comedy","viral"],{"layout":"setup_reaction_punchline"}),
 ("motivation","Motivation",["motivation","quote","cinematic"],{"layout":"quote_broll_riser"}),
 ("news","News Short",["news","headline","caption"],{"layout":"headline_facts_cta"}),
 ("review","Review",["review","product","creator"],{"layout":"hook_pros_cons_verdict"}),
])
ASSETS.extend(_MEGA)

# v2.28 Pro-grade original metadata expansion. These are parameter definitions,
# not proprietary media files; users can attach licensed media through packs.
_PRO28 = []
def _pro28(kind, prefix, rows):
    for slug,name,tags,params in rows:
        _PRO28.append(CreativeAsset(f"{prefix}.{slug}",name,kind,tuple(tags),params))

_pro28("effect","effect",[
("cinema_warm","Cinema Warm",["cinematic","film","warm"],{"preset":"cinema_warm"}),
("cinema_cool","Cinema Cool",["cinematic","film","cool"],{"preset":"cinema_cool"}),
("skin_pro","Skin Pro",["portrait","beauty","skin"],{"preset":"skin_pro"}),
("clarity","Clarity Boost",["clean","sharp","creator"],{"preset":"clarity"}),
("soft_bloom","Soft Bloom",["beauty","dream","bloom"],{"preset":"soft_bloom"}),
("film_fade","Film Fade",["film","vintage","matte"],{"preset":"film_fade"}),
("bleach","Bleach",["dramatic","editorial","film"],{"preset":"bleach"}),
("mono_high","Mono High Contrast",["blackwhite","dramatic","portrait"],{"preset":"mono_high"}),
("pastel_social","Pastel Social",["pastel","social","beauty"],{"preset":"pastel_social"}),
("night_lift","Night Lift",["night","lowlight","clean"],{"preset":"night_lift"}),
])
_pro28("transition","transition",[
("luma","Luma Wipe",["clean","cinematic","wipe"],{"animation":"luma_wipe","duration":.35}),
("radial","Radial Wipe",["social","energy","wipe"],{"animation":"radial_wipe","duration":.3}),
("zoom_blur","Zoom Blur",["zoom","energy","shorts"],{"animation":"zoom_blur","duration":.25}),
("rgb","RGB Split",["glitch","gaming","tech"],{"animation":"rgb_split","duration":.2}),
("strobe","Strobe Cut",["beat","impact","shorts"],{"animation":"strobe","duration":.12}),
("film_burn","Film Burn",["film","cinematic","light"],{"animation":"film_burn","duration":.4}),
("pixel","Pixel Wipe",["gaming","tech","retro"],{"animation":"pixel_wipe","duration":.3}),
("circle","Circle Reveal",["social","creator","fun"],{"animation":"circle_reveal","duration":.3}),
])
_pro28("motion","motion",[
("micro_push","Micro Push",["subtle","speaker","dialogue"],{"animation":"micro_push","scale_to":1.025}),
("impact_push","Impact Push",["impact","beat","shorts"],{"animation":"impact_push","scale_to":1.08}),
("tilt_left","Tilt Left",["motion","dynamic","creator"],{"animation":"tilt_left","degrees":3}),
("tilt_right","Tilt Right",["motion","dynamic","creator"],{"animation":"tilt_right","degrees":-3}),
("swing","Swing",["fun","social","motion"],{"animation":"swing"}),
("rubber","Rubber Band",["fun","bounce","viral"],{"animation":"rubber_band"}),
("camera_handheld","Camera Handheld",["vlog","documentary","organic"],{"animation":"handheld"}),
("dolly","Dolly In",["cinematic","portrait","story"],{"animation":"dolly_in","scale_to":1.045}),
])
_pro28("text","text",[
("karaoke","Karaoke Highlight",["caption","karaoke","word"],{"animation":"karaoke","size":50}),
("box_karaoke","Karaoke Box",["caption","karaoke","box"],{"animation":"karaoke_box","size":48}),
("comic","Comic Impact",["meme","fun","impact"],{"animation":"comic_impact","size":60}),
("editorial","Editorial Title",["fashion","luxury","title"],{"animation":"editorial","size":58}),
("lower_third","Creator Lower Third",["creator","podcast","lowerthird"],{"animation":"slide_up","size":42}),
("quote","Quote Card",["quote","story","motivation"],{"animation":"fade_up","size":54}),
("counter","Number Counter",["number","stats","education"],{"animation":"counter","size":58}),
("cta","CTA Button",["cta","social","conversion"],{"animation":"pop","size":48}),
])
_pro28("audio_fx","audio_fx",[
("voice_studio","Voice Studio",["voice","dialogue","podcast"],{"denoise":18,"compressor":True,"limiter":True,"voice_enhance":True}),
("voice_bright","Voice Bright",["voice","clarity","dialogue"],{"eq":"presence","compressor":True}),
("music_duck_12","Music Duck -12",["music","ducking","dialogue"],{"duck_db":-12,"attack":.06,"release":.32}),
("music_duck_6","Music Duck -6",["music","ducking","light"],{"duck_db":-6,"attack":.08,"release":.28}),
])
ASSETS.extend(_PRO28)

# v2.38 Creative Library Expansion: original metadata presets covering the
# major NLE categories. These are parameter recipes only; no proprietary media
# from CapCut/Premiere is bundled.
_PRO38_ROWS = {
"effect":[
("dream_glow","Dream Glow",["aesthetic","beauty","dream"],{"preset":"dream_glow"}),
("vhs_retro","VHS Retro",["retro","vhs","nostalgia"],{"preset":"vhs_retro"}),
("chromatic","Chromatic",["rgb","glitch","music"],{"preset":"chromatic"}),
("matte_film","Matte Film",["film","cinema","matte"],{"preset":"matte_film"}),
("moody_blue","Moody Blue",["moody","night","cinematic"],{"preset":"moody_blue"}),
("summer_pop","Summer Pop",["summer","travel","bright"],{"preset":"summer_pop"}),
("wedding_soft","Wedding Soft",["wedding","romantic","soft"],{"preset":"wedding_soft"}),
("street_grit","Street Grit",["street","urban","gritty"],{"preset":"street_grit"}),
("horror_dark","Horror Dark",["horror","dark","dramatic"],{"preset":"horror_dark"}),
("anime_pop","Anime Pop",["anime","cartoon","pop"],{"preset":"anime_pop"}),
("luxury_gold","Luxury Gold",["luxury","fashion","gold"],{"preset":"luxury_gold"}),
("clean_white","Clean White",["product","clean","commercial"],{"preset":"clean_white"}),
],
"transition":[
("slide_left","Slide Left",["slide","social","clean"],{"animation":"slide_left","duration":.28}),
("slide_right","Slide Right",["slide","social","clean"],{"animation":"slide_right","duration":.28}),
("slide_up","Slide Up",["slide","modern","title"],{"animation":"slide_up","duration":.30}),
("slide_down","Slide Down",["slide","modern"],{"animation":"slide_down","duration":.30}),
("cube","Cube Flip",["3d","gaming","fun"],{"animation":"cube","duration":.42}),
("door","Door Reveal",["3d","cinematic","reveal"],{"animation":"door","duration":.42}),
("glitch","Glitch",["glitch","gaming","tech"],{"animation":"glitch","duration":.18}),
("digital","Digital Wipe",["digital","tech","gaming"],{"animation":"digital_wipe","duration":.24}),
("liquid","Liquid Reveal",["liquid","beauty","aesthetic"],{"animation":"liquid","duration":.48}),
("light_leak","Light Leak",["film","dream","travel"],{"animation":"light_leak","duration":.38}),
("prism","Prism",["music","aesthetic","energy"],{"animation":"prism","duration":.25}),
("paper","Paper Swipe",["paper","education","story"],{"animation":"paper_swipe","duration":.34}),
("clock","Clock Wipe",["retro","creative","fun"],{"animation":"clock","duration":.35}),
("heart","Heart Reveal",["romantic","wedding","fun"],{"animation":"heart","duration":.36}),
],
"motion":[
("zoom_snap","Zoom Snap",["zoom","hook","viral"],{"animation":"zoom_snap","scale_to":1.08,"duration":.16}),
("zoom_out","Zoom Out",["reveal","cinematic"],{"animation":"zoom_out","scale_from":1.06,"duration":.35}),
("camera_push","Camera Push",["cinematic","story"],{"animation":"camera_push","scale_to":1.035,"duration":.65}),
("camera_pull","Camera Pull",["cinematic","reveal"],{"animation":"camera_pull","scale_from":1.045,"duration":.65}),
("orbit","Orbit",["dynamic","product","music"],{"animation":"orbit","degrees":4}),
("drift_left","Drift Left",["aesthetic","broll"],{"animation":"drift_left","distance":.025}),
("drift_right","Drift Right",["aesthetic","broll"],{"animation":"drift_right","distance":.025}),
("bounce","Bounce",["meme","fun","viral"],{"animation":"bounce","amplitude":.06}),
("rubber","Rubber",["meme","fun","social"],{"animation":"rubber","amplitude":.08}),
("handheld_light","Handheld Light",["vlog","documentary","organic"],{"animation":"handheld","amplitude":1.5}),
("spin_in","Spin In",["gaming","music","energy"],{"animation":"spin_in","degrees":5}),
("spin_out","Spin Out",["gaming","music","energy"],{"animation":"spin_out","degrees":-5}),
],
"text":[
("pop","Pop In",["caption","viral","social"],{"animation":"pop","size":52}),
("bounce","Bounce Text",["meme","fun","caption"],{"animation":"bounce","size":54}),
("word_by_word","Word By Word",["caption","education","podcast"],{"animation":"word_by_word","size":48}),
("sentence_reveal","Sentence Reveal",["caption","story"],{"animation":"sentence_reveal","size":48}),
("gradient","Gradient Title",["title","modern","social"],{"animation":"gradient","size":58}),
("outline","Outline Bold",["gaming","meme","impact"],{"animation":"outline","size":60}),
("shadow","Drop Shadow",["clean","caption","title"],{"animation":"shadow","size":52}),
("bubble","Bubble Caption",["fun","meme","social"],{"animation":"bubble","size":50}),
("speech","Speech Bubble",["meme","reaction","comedy"],{"animation":"speech_bubble","size":48}),
("subtitle_minimal","Minimal Subtitle",["subtitle","documentary","clean"],{"animation":"fade","size":42}),
("headline","Breaking Headline",["news","headline","report"],{"animation":"slide_left","size":56}),
("price_tag","Price Tag",["product","shopping","commerce"],{"animation":"pop","size":46}),
("location","Location Pin",["travel","vlog","map"],{"animation":"pop","size":44}),
],
"overlay":[
("dust","Dust",["film","cinematic","vintage"],{"preset":"dust","amount":.12}),
("bokeh","Bokeh",["beauty","wedding","dream"],{"preset":"bokeh","opacity":.20}),
("rain","Rain",["moody","cinematic","horror"],{"preset":"rain","opacity":.16}),
("snow","Snow",["winter","travel","cinematic"],{"preset":"snow","opacity":.14}),
("particles","Particles",["gaming","music","energy"],{"preset":"particles","opacity":.16}),
("sparkle","Sparkle",["beauty","luxury","wedding"],{"preset":"sparkle","opacity":.20}),
("speed_lines","Speed Lines",["gaming","sports","action"],{"preset":"speed_lines","opacity":.22}),
("paper_texture","Paper Texture",["education","story","retro"],{"preset":"paper","opacity":.12}),
("gradient_light","Gradient Light",["aesthetic","music","social"],{"preset":"gradient_light","opacity":.18}),
("letterbox","Letterbox",["cinematic","film"],{"preset":"letterbox","amount":.10}),
],
"sticker":[
("arrow","Arrow",["education","callout","tutorial"],{"shape":"arrow"}),
("circle","Circle Highlight",["education","sports","callout"],{"shape":"circle"}),
("check","Check",["education","review","product"],{"shape":"check"}),
("x","X Mark",["meme","review","education"],{"shape":"x"}),
("fire","Fire",["gaming","viral","hype"],{"shape":"fire"}),
("wow","WOW",["meme","reaction","viral"],{"shape":"wow"}),
("laugh","Laugh",["meme","comedy","reaction"],{"shape":"laugh"}),
("new","NEW Badge",["product","commerce","social"],{"shape":"new"}),
("sale","SALE Badge",["product","commerce","social"],{"shape":"sale"}),
("location","Location Pin",["travel","vlog"],{"shape":"location"}),
],
"template":[
("viral_short","Viral Short",["shorts","viral","retention"],{"recipe":"hook-body-payoff"}),
("podcast_clip","Podcast Clip",["podcast","talking_head"],{"recipe":"hook-quote-context"}),
("gaming_highlight","Gaming Highlight",["gaming","esports"],{"recipe":"cold-open-action-reaction"}),
("story_reel","Story Reel",["story","cinematic","reel"],{"recipe":"setup-build-payoff"}),
("product_ad","Product Ad",["product","commercial"],{"recipe":"problem-product-proof-cta"}),
("education_reel","Education Reel",["education","explainer"],{"recipe":"hook-3points-summary"}),
("meme_clip","Meme Clip",["meme","comedy"],{"recipe":"setup-punch-reaction"}),
("music_reel","Music Reel",["music","beat"],{"recipe":"beat-montage-drop"}),
("travel_reel","Travel Reel",["travel","vlog"],{"recipe":"establish-detail-montage"}),
("sports_highlight","Sports Highlight",["sports","action"],{"recipe":"anticipation-action-replay"}),
("news_short","News Short",["news","report"],{"recipe":"headline-facts-source-cta"}),
("before_after","Before After",["transformation","product","beauty"],{"recipe":"before-transition-after"}),
],
}
for _kind, _rows in _PRO38_ROWS.items():
    for _slug, _name, _tags, _params in _rows:
        ASSETS.append(CreativeAsset(f"{_kind}.{_slug}", _name, _kind, tuple(_tags), _params))



# v2.39 Thousand-Item Creative Library ---------------------------------------
# Generated from original, parameterized recipes. These are metadata/preset
# definitions, not copied proprietary media. Licensed user packs can use the
# same schema. The expansion is deterministic so IDs stay stable between builds.
_VARIANT_BANK = {
    "effect": [
        ("cinema", ["cinematic","film","grade"]), ("social", ["social","creator","shorts"]),
        ("portrait", ["portrait","skin","beauty"]), ("gaming", ["gaming","rgb","energy"]),
        ("retro", ["retro","vintage","nostalgia"]), ("dream", ["dream","soft","aesthetic"]),
        ("horror", ["horror","dark","tension"]), ("luxury", ["luxury","fashion","premium"]),
        ("sports", ["sports","action","energy"]), ("travel", ["travel","vlog","outdoor"]),
        ("food", ["food","commercial","crisp"]), ("music", ["music","beat","performance"]),
    ],
    "transition": [
        ("whip", ["whip","motion","energy"]), ("zoom", ["zoom","punch","shorts"]),
        ("blur", ["blur","cinematic","smooth"]), ("glitch", ["glitch","gaming","tech"]),
        ("flash", ["flash","impact","beat"]), ("wipe", ["wipe","clean","social"]),
        ("spin", ["spin","dynamic","music"]), ("light", ["light","dream","aesthetic"]),
        ("film", ["film","cinema","vintage"]), ("shape", ["shape","graphic","modern"]),
    ],
    "motion": [
        ("push", ["push","camera","cinematic"]), ("pull", ["pull","reveal","story"]),
        ("shake", ["shake","impact","gaming"]), ("drift", ["drift","aesthetic","slow"]),
        ("orbit", ["orbit","product","dynamic"]), ("tilt", ["tilt","camera","creator"]),
        ("bounce", ["bounce","fun","meme"]), ("swing", ["swing","social","fashion"]),
        ("parallax", ["parallax","photo","broll"]), ("handheld", ["handheld","vlog","documentary"]),
    ],
    "text": [
        ("caption", ["caption","subtitle","shorts"]), ("hook", ["hook","viral","social"]),
        ("kinetic", ["kinetic","music","lyrics"]), ("minimal", ["minimal","clean","documentary"]),
        ("comic", ["comic","meme","fun"]), ("neon", ["neon","gaming","night"]),
        ("karaoke", ["karaoke","lyrics","music"]), ("headline", ["headline","news","report"]),
        ("lowerthird", ["lowerthird","corporate","creator"]), ("callout", ["callout","education","tutorial"]),
    ],
    "overlay": [
        ("grain", ["grain","film","texture"]), ("particles", ["particles","energy","music"]),
        ("bokeh", ["bokeh","beauty","dream"]), ("weather", ["rain","snow","mood"]),
        ("light", ["light","leak","aesthetic"]), ("texture", ["texture","paper","retro"]),
        ("vignette", ["vignette","cinema","portrait"]), ("speed", ["speed","sports","action"]),
    ],
    "sticker": [
        ("reaction", ["reaction","meme","comedy"]), ("callout", ["callout","education","tutorial"]),
        ("badge", ["badge","product","commerce"]), ("emoji", ["emoji","social","fun"]),
        ("shape", ["shape","highlight","marker"]), ("hype", ["hype","gaming","viral"]),
        ("travel", ["travel","vlog","location"]),
    ],
    "sfx": [
        ("impact", ["impact","hit","shorts"]), ("whoosh", ["whoosh","transition","motion"]),
        ("riser", ["riser","build","tension"]), ("drop", ["drop","bass","beat"]),
        ("pop", ["pop","meme","social"]), ("glitch", ["glitch","gaming","tech"]),
        ("ui", ["ui","click","notification"]), ("nature", ["nature","travel","ambient"]),
    ],
    "audio_fx": [
        ("voice", ["voice","dialogue","podcast"]), ("music", ["music","ducking","mix"]),
        ("radio", ["radio","retro","voice"]), ("cinema", ["cinematic","mix","film"]),
        ("gaming", ["gaming","voice","stream"]), ("broadcast", ["broadcast","news","voice"]),
    ],
    "filter": [
        ("detail", ["detail","sharp","clean"]), ("tone", ["tone","grade","cinema"]),
        ("skin", ["skin","portrait","beauty"]), ("noise", ["noise","lowlight","recovery"]),
        ("color", ["color","social","vivid"]), ("motion", ["motion","sports","action"]),
    ],
    "template": [
        ("short", ["shorts","viral","retention"]), ("podcast", ["podcast","talking_head","clip"]),
        ("gaming", ["gaming","esports","highlight"]), ("vlog", ["vlog","lifestyle","travel"]),
        ("product", ["product","commercial","ad"]), ("education", ["education","explainer","tutorial"]),
        ("meme", ["meme","comedy","reaction"]), ("music", ["music","beat","reel"]),
        ("sports", ["sports","action","highlight"]), ("news", ["news","headline","report"]),
    ],
    "music": [
        ("beat", ["music","beat","shorts"]), ("cinematic", ["music","cinematic","story"]),
        ("lofi", ["music","lofi","vlog"]), ("hype", ["music","hype","gaming"]),
        ("ambient", ["music","ambient","documentary"]), ("commercial", ["music","commercial","product"]),
        ("travel", ["music","travel","vlog"]),
    ],
}
_VARIANT_TARGETS = {
    "effect":90, "transition":90, "motion":80, "text":80, "overlay":55,
    "sticker":45, "sfx":60, "audio_fx":55, "filter":35, "template":70, "music":51,
}

def _make_thousandth_library() -> None:
    existing = {a.id for a in ASSETS}
    added = 0
    for kind, target in _VARIANT_TARGETS.items():
        banks = _VARIANT_BANK[kind]
        made = 0
        i = 0
        while made < target:
            family, tags = banks[i % len(banks)]
            tier = i // len(banks) + 1
            slug = f"{family}_pro_{tier:02d}"
            asset_id = f"{kind}.{slug}"
            i += 1
            if asset_id in existing:
                continue
            name = f"{family.title()} {kind.replace('_',' ').title()} Pro {tier:02d}"
            params = {
                "recipe_family": family,
                "variant": tier,
                "strength": round(0.35 + ((i * 7) % 65) / 100, 2),
                "duration": round(0.12 + ((i * 13) % 90) / 100, 2),
                "original_preset": True,
            }
            if kind == "transition":
                params.update({"duration": round(0.12 + ((i * 11) % 36) / 100, 2), "easing":"ease_in_out"})
            elif kind == "motion":
                params.update({"scale_to": round(1.02 + ((i * 3) % 11) / 100, 3), "easing":"smooth"})
            elif kind == "text":
                params.update({"size": 42 + ((i * 5) % 23), "animation": family})
            elif kind in ("overlay", "filter"):
                params.update({"opacity": round(0.10 + ((i * 5) % 30) / 100, 2)})
            elif kind == "sticker":
                params.update({"shape": family, "scale": round(0.7 + ((i * 4) % 55) / 100, 2)})
            elif kind == "sfx":
                params.update({"generator": family, "pitch": -4 + ((i * 3) % 9)})
            elif kind == "audio_fx":
                params.update({"mix": round(0.55 + ((i * 3) % 40) / 100, 2)})
            elif kind == "template":
                params.update({"recipe": f"{family}-hook-body-payoff-v{tier:02d}", "pace": 0.65 + ((i * 2) % 35) / 100})
            elif kind == "music":
                params.update({"bpm": 80 + ((i * 7) % 81), "energy": round(0.4 + ((i * 5) % 55) / 100, 2), "asset_type":"music_recipe"})
            ASSETS.append(CreativeAsset(asset_id, name, kind, tuple(tags + ["pro","original","v2.39"]), params))
            existing.add(asset_id)
            made += 1
            added += 1
    assert len(ASSETS) == 1000, f"Expected 1000 creative assets, got {len(ASSETS)}"

_make_thousandth_library()

# Normalize legacy duplicate IDs so favorites/cache/preset references remain stable.
_seen_ids: dict[str, int] = {}
_normalized_assets: list[CreativeAsset] = []
for _asset in ASSETS:
    _n = _seen_ids.get(_asset.id, 0) + 1
    _seen_ids[_asset.id] = _n
    if _n == 1:
        _normalized_assets.append(_asset)
    else:
        _normalized_assets.append(CreativeAsset(
            f"{_asset.id}.dup{_n:02d}", _asset.name, _asset.kind, _asset.tags, dict(_asset.params), _asset.license
        ))
ASSETS[:] = _normalized_assets

# Lightweight search index for the 10,000-item library. Built once on import.
_SEARCH_INDEX = tuple((a, (a.id + " " + a.name + " " + " ".join(a.tags)).lower(), set(a.tags)) for a in ASSETS)

def categories() -> list[str]:
    return sorted({a.kind for a in ASSETS})


def featured(limit: int = 24) -> list[CreativeAsset]:
    priority = ("template", "transition", "effect", "text", "motion", "overlay", "sticker", "sfx", "audio_fx", "filter", "music")
    ranked = sorted(ASSETS, key=lambda a: (priority.index(a.kind) if a.kind in priority else 99, a.name.lower()))
    return ranked[:max(0, int(limit))]


def search_library(query: str = "", kind: str | None = None, tags: tuple[str, ...] = (), limit: int = 50) -> list[CreativeAsset]:
    """Search the complete creative library with weighted name/tag matching."""
    terms = [x.lower() for x in str(query).replace(',', ' ').split() if x.strip()]
    wanted = {x.lower() for x in tags}
    rows = []
    for a, hay, asset_tags in _SEARCH_INDEX:
        if kind and a.kind != kind:
            continue
        score = 0
        name_l = a.name.lower()
        for t in terms:
            if t in name_l: score += 5
            elif t in asset_tags: score += 3
            elif t in hay: score += 1
        if wanted:
            score += 4 * len(wanted.intersection(asset_tags))
        if not terms and not wanted:
            score = 1
        if score:
            rows.append((score, a))
    return [a for _, a in sorted(rows, key=lambda x: (-x[0], x[1].kind, x[1].name.lower()))[:max(0, int(limit))]]


def library_stats() -> dict[str, int]:
    return {k: sum(1 for a in ASSETS if a.kind == k) for k in categories()}

# v2.60 Ultra Creative Library ------------------------------------------------
# Exactly 50,000 original, metadata-first procedural recipes. These are NOT
# proprietary CapCut assets. They describe renderable recipes and searchable
# creative intents; licensed media/font/audio packs can be attached separately.
_FIFTY_K_TARGETS = {
    "effect": 8000, "transition": 6500, "motion": 6500, "text": 6000,
    "overlay": 4000, "sticker": 3500, "sfx": 4000, "audio_fx": 3500,
    "filter": 2500, "template": 4500, "music": 1000,
}

_STYLE_MATRIX = [
    ("clean", ["clean","minimal","creator"]), ("cinematic", ["cinematic","film","story"]),
    ("viral", ["viral","shorts","retention"]), ("luxury", ["luxury","premium","fashion"]),
    ("gaming", ["gaming","stream","esports"]), ("tech", ["tech","ui","future"]),
    ("beauty", ["beauty","portrait","skin"]), ("food", ["food","cooking","restaurant"]),
    ("travel", ["travel","adventure","vlog"]), ("sports", ["sports","action","fitness"]),
    ("meme", ["meme","comedy","reaction"]), ("retro", ["retro","vhs","nostalgia"]),
    ("horror", ["horror","dark","tension"]), ("romantic", ["romance","soft","love"]),
    ("documentary", ["documentary","journalism","real"]), ("education", ["education","explainer","tutorial"]),
    ("news", ["news","headline","breaking"]), ("podcast", ["podcast","talking_head","dialogue"]),
    ("music", ["music","beat","performance"]), ("kids", ["kids","fun","colorful"]),
]
_FORMATS = ["tiktok","instagram_reels","youtube_shorts","youtube","vertical_9_16","square_1_1","landscape_16_9"]
_INTENTS = ["hook","explain","emphasize","reveal","reaction","story","cta","sale","tutorial","before_after","list","quote","punchline","payoff","pattern_break","broll","dialogue","beat_sync"]
_MOODS = ["calm","happy","excited","dramatic","mysterious","energetic","serious","warm","dark","playful","premium","nostalgic"]


def _recipe_params(kind: str, i: int, family: str, style_tags: list[str], tier: int) -> dict:
    strength = round(0.15 + ((i * 37) % 86) / 100, 3)
    duration = round(0.08 + ((i * 17) % 120) / 100, 2)
    params = {
        "recipe_family": family, "variant": tier, "strength": strength,
        "duration": duration, "original_preset": True, "preview_seed": i * 7919,
        "style": family, "intent": _INTENTS[i % len(_INTENTS)],
        "mood": _MOODS[(i // 3) % len(_MOODS)], "formats": [_FORMATS[i % len(_FORMATS)]],
        "semantic_tags": list(style_tags), "safe_to_auto_apply": True,
    }
    if kind == "effect":
        params.update({"pipeline":"color+look", "grain":round(((i*7)%35)/100,2), "contrast":round(.85+((i*5)%35)/100,2)})
    elif kind == "transition":
        params.update({"transition_family":family, "easing":["ease_in","ease_out","ease_in_out","smooth"][i%4], "duration":round(.08+((i*11)%48)/100,2)})
    elif kind == "motion":
        params.update({"scale_to":round(1.01+((i*7)%20)/100,3), "rotation":((i*13)%11)-5, "easing":"smooth"})
    elif kind == "text":
        params.update({"animation":family, "size":36+((i*7)%34), "weight":500+((i*3)%5)*100, "tracking":((i*5)%7)-3})
    elif kind == "overlay":
        params.update({"overlay_family":family, "opacity":round(.06+((i*11)%70)/100,2), "blend":["screen","add","softlight","overlay","normal"][i%5]})
    elif kind == "sticker":
        params.update({"shape":family, "scale":round(.45+((i*9)%90)/100,2), "rotation":((i*13)%41)-20, "anchor":["top_left","top_right","center","bottom_left","bottom_right"][i%5]})
    elif kind == "sfx":
        params.update({"generator":family, "pitch":-8+((i*5)%17), "mix":round(.35+((i*3)%60)/100,2), "one_shot":True})
    elif kind == "audio_fx":
        params.update({"audio_chain":family, "mix":round(.4+((i*5)%55)/100,2), "adaptive":True})
    elif kind == "filter":
        params.update({"filter_family":family, "lut_strength":round(.25+((i*7)%75)/100,2), "preserve_skin":i%3!=0})
    elif kind == "template":
        params.update({"template_recipe":f"{family}-hook-body-payoff-v{tier:04d}", "pace":round(.45+((i*2)%56)/100,2), "slots":["hook","body","payoff","cta"]})
    elif kind == "music":
        params.update({"music_recipe":family, "bpm":70+((i*7)%111), "energy":round(.25+((i*5)%75)/100,2), "beat_grid":True})
    return params


def _expand_to_fifty_thousand() -> None:
    existing = {a.id for a in ASSETS}
    current = library_stats()
    for kind, target in _FIFTY_K_TARGETS.items():
        need = max(0, target - current.get(kind, 0))
        made = 0; i = 0
        while made < need:
            family, style_tags = _STYLE_MATRIX[i % len(_STYLE_MATRIX)]
            tier = i // len(_STYLE_MATRIX) + 1
            slug = f"{family}_studio_{tier:04d}"
            aid = f"{kind}.{slug}"
            i += 1
            if aid in existing:
                continue
            tags = list(dict.fromkeys(style_tags + [kind, _INTENTS[i % len(_INTENTS)], _MOODS[i % len(_MOODS)], "pro", "original", "v2.60"]))
            name = f"{family.title()} {kind.replace('_',' ').title()} Studio {tier:04d}"
            ASSETS.append(CreativeAsset(aid, name, kind, tuple(tags), _recipe_params(kind, i, family, tags, tier)))
            existing.add(aid); made += 1
    assert len(ASSETS) == 50000, f"Expected 50000 creative assets, got {len(ASSETS)}"

_expand_to_fifty_thousand()

# Normalize legacy recipes so the entire 50K catalog exposes the same rich
# semantic contract to the matcher and UI.
_rich_assets = []
for _a in ASSETS:
    _p = dict(_a.params)
    _p.setdefault("semantic_tags", list(_a.tags))
    _p.setdefault("intent", "general")
    _p.setdefault("mood", "neutral")
    _p.setdefault("formats", list(_FORMATS))
    _p.setdefault("safe_to_auto_apply", True)
    _rich_assets.append(CreativeAsset(_a.id, _a.name, _a.kind, _a.tags, _p, _a.license))
ASSETS[:] = _rich_assets

_SEARCH_INDEX = tuple((a, (a.id + " " + a.name + " " + " ".join(a.tags)).lower(), set(a.tags)) for a in ASSETS)


def categories() -> list[str]:
    return sorted({a.kind for a in ASSETS})


def featured(limit: int = 24) -> list[CreativeAsset]:
    priority = ("template", "transition", "effect", "text", "motion", "overlay", "sticker", "sfx", "audio_fx", "filter", "music")
    ranked = sorted(ASSETS, key=lambda a: (priority.index(a.kind) if a.kind in priority else 99, a.name.lower()))
    return ranked[:max(0, int(limit))]


_SEARCH_SYNONYMS = {
    "gamer": "gaming", "game": "gaming", "rgb": "gaming",
    "caption": "subtitle", "captions": "subtitle", "cc": "subtitle",
    "fx": "effect", "effects": "effect", "transition": "transition",
    "sfx": "sound", "whoosh": "sound", "impact": "impact",
    "broll": "b-roll", "footage": "b-roll", "travel": "travel",
    "film": "cinematic", "movie": "cinematic", "cinema": "cinematic",
    "lut": "color", "grading": "color", "colour": "color",
    "tiktok": "shorts", "reels": "shorts", "youtube": "creator",
}

def search_library(query: str = "", kind: str | None = None, tags: tuple[str, ...] = (), limit: int = 50) -> list[CreativeAsset]:
    """Search the complete 50K catalog with semantic aliases and weighted ranking."""
    raw_terms = [x.lower() for x in str(query).replace(',', ' ').split() if x.strip()]
    terms = []
    for term in raw_terms:
        terms.append(term)
        alias = _SEARCH_SYNONYMS.get(term)
        if alias and alias not in terms:
            terms.append(alias)
    wanted = {x.lower() for x in tags}
    rows = []
    for a, hay, asset_tags in _SEARCH_INDEX:
        if kind and a.kind != kind:
            continue
        score = 0
        name_l = a.name.lower()
        for t in terms:
            if t in name_l: score += 5
            elif t in asset_tags: score += 3
            elif t in hay: score += 1
        if wanted:
            score += 4 * len(wanted.intersection(asset_tags))
        if not terms and not wanted: score = 1
        if score: rows.append((score, a))
    return [a for _, a in sorted(rows, key=lambda x: (-x[0], x[1].kind, x[1].name.lower()))[:max(0, int(limit))]]


def library_stats() -> dict[str, int]:
    return {k: sum(1 for a in ASSETS if a.kind == k) for k in categories()}
