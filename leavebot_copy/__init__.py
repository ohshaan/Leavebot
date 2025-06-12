import importlib, sys

# Expose the top-level scripts package under leavebot_copy.scripts
scripts = importlib.import_module('scripts')
sys.modules[__name__ + '.scripts'] = scripts
