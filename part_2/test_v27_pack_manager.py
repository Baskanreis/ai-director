from app.effects.library_manager import save_pack, load_pack
from app.effects.pro_asset_library import CreativeAsset

def test_pack_roundtrip(tmp_path):
    p=tmp_path/'pack.json'
    a=CreativeAsset('template.demo','Demo','template',('demo',),{'x':1})
    save_pack(p,[a],name='Demo Pack')
    got=load_pack(p)
    assert got[0].id=='template.demo'
    assert got[0].params['x']==1
