from functools import lru_cache

from . import paths

@lru_cache()
def stexport():
    from .common import import_file
    stexport_model = import_file(paths.stexport.repo / 'model.py')
    return stexport_model


def get_data():
    sources = [max(paths.stexport.export_dir.glob('*.json'))]
    return stexport().Model(sources).site_model('stackoverflow')
