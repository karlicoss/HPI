'''
Stackexchange data
'''

import my.config.repos.stexport.model as stexport
from my.config import stackexchange as config


def get_data():
    sources = [max(config.export_dir.glob('*.json'))]
    return stexport.Model(sources).site_model('stackoverflow')
