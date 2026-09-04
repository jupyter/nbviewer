import os

if (
    os.getenv("JUPYTERHUB_SERVICE_URL")
    and os.getenv("NBVIEWER_JUPYTERHUB_AUTH", "1") == "1"
):
    # if a JupyterHub service, enable JupyterHub Auth
    from jupyterhub.services.auth import HubOAuthenticated  # type: ignore

    _is_jupyterhub = True
else:
    _is_jupyterhub = False


class AuthDisabled:
    def get_current_user(self):
        return "anonymous"


if _is_jupyterhub:
    AuthMixin = HubOAuthenticated
else:
    AuthMixin = AuthDisabled
