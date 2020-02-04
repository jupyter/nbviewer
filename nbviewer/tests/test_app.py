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
    assert 'NBViewer.answer_yes' in cfg_text
    assert 'NBViewer.base_url' in cfg_text
    assert 'NBViewer._base_url' not in cfg_text # This shouldn't be configurable
    assert 'NBViewer.binder_base_url' in cfg_text
    assert 'NBViewer.cache_expiry_max' in cfg_text
    assert 'NBViewer.cache_expiry_min' in cfg_text
    assert 'NBViewer.client' in cfg_text
    assert 'NBViewer.config_file' in cfg_text
    assert 'NBViewer.content_security_policy' in cfg_text
    assert 'NBViewer.default_format' in cfg_text
    assert 'NBViewer.frontpage' in cfg_text
    assert 'NBViewer.generate_config' in cfg_text
    assert 'NBViewer.host' in cfg_text
    assert 'NBViewer.index' in cfg_text
    assert 'NBViewer.ipywidgets_base_url' in cfg_text
    assert 'NBViewer.jupyter_js_widgets_version' in cfg_text
    assert 'NBViewer.jupyter_widgets_html_manager_version' in cfg_text
    assert 'NBViewer.localfile_any_user' in cfg_text
    assert 'NBViewer.local_handler' in cfg_text
    assert 'NBViewer.localfile_follow_symlinks' in cfg_text
    assert 'NBViewer.localfiles' in cfg_text
    assert 'NBViewer.mathjax_url' in cfg_text
    assert 'NBViewer.max_cache_uris' in cfg_text
    assert 'NBViewer.mc_threads' in cfg_text
    assert 'NBViewer.no_cache' in cfg_text
    assert 'NBViewer.no_check_certificate' in cfg_text
    assert 'NBViewer.port' in cfg_text
    assert 'NBViewer.processes' in cfg_text
    assert 'NBViewer.providers' in cfg_text
    assert 'NBViewer.provider_rewrites' in cfg_text
    assert 'NBViewer.proxy_host' in cfg_text
    assert 'NBViewer.proxy_port' in cfg_text
    assert 'NBViewer.rate_limit' in cfg_text
    assert 'NBViewer.rate_limit_interval' in cfg_text
    assert 'NBViewer.render_timeout' in cfg_text
    assert 'NBViewer.sslcert' in cfg_text
    assert 'NBViewer.sslkey' in cfg_text
    assert 'NBViewer.static_path' in cfg_text
    assert 'NBViewer.static_url_prefix' in cfg_text
    assert 'NBViewer._static_url_prefix' not in cfg_text # This shouldn't be configurable
    assert 'NBViewer.statsd_host' in cfg_text
    assert 'NBViewer.statsd_port' in cfg_text
    assert 'NBViewer.statsd_prefix' in cfg_text
    assert 'NBViewer.template_path' in cfg_text
    assert 'NBViewer.cache' not in cfg_text # Shouldn't be configurable, is a property
    assert 'NBViewer.default_endpoint' not in cfg_text # Shouldn't be configurable, is a property
    assert 'NBViewer.env' not in cfg_text # Ditto the above
    assert 'NBViewer.fetch_kwargs' not in cfg_text
    assert 'NBViewer.formats' not in cfg_text
    assert 'NBViewer.frontpage_setup' not in cfg_text
    assert 'NBViewer.pool' not in cfg_text
    assert 'NBViewer.rate_limiter' not in cfg_text
    assert 'NBViewer.static_paths' not in cfg_text
    assert 'NBViewer.template_paths' not in cfg_text

