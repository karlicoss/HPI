# TODO just eval setup file to populate paths etc?
# TODO note sure if it would

# TODO maybe just import everything?
# TODO how to make it mypy friendly? maybe defensive import? or mypy config? or interface file?

try:
    import my_configuration
    paths = my_configuration.paths # type: ignore
except ImportError:
    import warnings
    warnings.warn("my_configuration package isn't found! That might result in issues")
