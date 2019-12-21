import mycfg.repos.stexport.model as stexport
from mycfg import paths


def get_data():
    sources = [max(paths.stexport.export_dir.glob('*.json'))]
    return stexport.Model(sources).site_model('stackoverflow')
