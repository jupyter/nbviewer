import os
import sys

from tempfile import NamedTemporaryFile
from subprocess import PIPE
from subprocess import Popen

# Also copied mostly from JupyterHub since again -- if not broken, don't fix.
def test_generate_config():
    with NamedTemporaryFile(prefix='nbviewer_config', suffix='.py') as tf:
        cfg_file = tf.name
    with open(cfg_file, 'w') as f:
        f.write("c.A = 5")
    p = Popen(
        [sys.executable, '-m', 'nbviewer', '--generate-config', '--config-file={}'.format(cfg_file)],
        stdout=PIPE,
        stdin=PIPE,
    )
    out, _ = p.communicate(b'n')
    out = out.decode('utf8', 'replace')
    assert os.path.exists(cfg_file)
    with open(cfg_file) as f:
        cfg_text = f.read()
    assert cfg_text == 'c.A = 5'

    p = Popen(
        [sys.executable, '-m', 'nbviewer', '--generate-config', '--config-file={}'.format(cfg_file)],
        stdout=PIPE,
        stdin=PIPE,
    )
    out, _ = p.communicate(b'x\ny')
    out = out.decode('utf8', 'replace')
    assert os.path.exists(cfg_file)
    with open(cfg_file) as f:
        cfg_text = f.read()
    os.remove(cfg_file)
    assert cfg_file in out
    assert 'NBViewer.name' not in cfg_text # This shouldn't be configurable
    assert 'NBViewer.local_handler' in cfg_text
    assert 'NBViewer.static_path' in cfg_text
