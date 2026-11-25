# gp-saml-gui for UniTN

If you have used the University of Trento VPN and hate closed software,
you have probably suffered enough already.

Enter `gp-saml-gui-unitn`. It connects to the UniTN GlobalProtect VPN
(`vpn-mfa.icts.unitn.it`) with SAML sign-in and OpenConnect. It works on macOS;
Linux support is written but still needs a spare soul that checks if I did not
write weird stuff.

It is a fork of a fork:

- [dlenski/gp-saml-gui] is the original tool, which needs WebKit2-GTK.
- [lkrms/gp-saml-gui] adds [pywebview] as a fallback for macOS, where
  WebKit2-GTK is hard to install. As discussed in [#53][macos-issue], it is not
  merged upstream; pywebview cannot inspect HTTP headers, so it only works with
  GlobalProtect VPNs that copy SAML headers into HTML comments (UniTN does).
- This repository adds the UniTN helper on top.

[dlenski/gp-saml-gui]: https://github.com/dlenski/gp-saml-gui
[lkrms/gp-saml-gui]: https://github.com/lkrms/gp-saml-gui
[pywebview]: https://pywebview.flowrl.com/
[macos-issue]: https://github.com/dlenski/gp-saml-gui/issues/53

## Quick start

```sh
brew install openconnect python@3.14                        # or see Installation
python3.14 -m venv .venv                                    # or use direnv like well-functioning humans
.venv/bin/python3 -m pip install -r requirements-unitn.txt
export PATH="$PWD/bin:$PATH"                                # or add bin/ to PATH permanently
gp-saml-gui-unitn start
```

## Installation

Nothing is installed system-wide: the helper runs from the checkout, so put
the repository's `bin/` on `PATH`. It requires Python 3.8 or newer (3.14 was
also checked).

### macOS (Homebrew)

```sh
brew install openconnect python@3.14
python3.14 -m venv .venv
.venv/bin/python3 -m pip install -r requirements-unitn.txt
```

Both Apple Silicon (`/opt/homebrew`) and Intel (`/usr/local`) Homebrew layouts
are supported, and so is a direnv environment in `.direnv/*/bin/python3`.

### Debian / Ubuntu

Install OpenConnect, the GTK/WebKit runtime used by pywebview, and the distro
PyGObject bindings:

```sh
sudo apt update
sudo apt install openconnect python3 python3-venv python3-gi python3-gi-cairo \
  gir1.2-gtk-3.0 gir1.2-webkit2-4.1
python3 -m venv --system-site-packages .venv
.venv/bin/python3 -m pip install -r requirements-unitn.txt
```

The Debian/Ubuntu `openconnect` package depends on `vpnc-scripts`, and recent
packages install `hipreport.sh` under `/usr/libexec/openconnect`.

### Other Linux distributions

Install OpenConnect, `vpnc-script`, GTK 3, WebKit2GTK and PyGObject with the
distribution package manager, then install `requirements-unitn.txt` in a
Python environment that can import those system bindings. pywebview also
supports other Linux backends, but they have not been checked.

## Usage

```sh
gp-saml-gui-unitn start     # open the login window, then connect
gp-saml-gui-unitn status    # exit 0 and print PID and address when connected
gp-saml-gui-unitn stop
gp-saml-gui-unitn restart
gp-saml-gui-unitn logs      # last 80 lines of the log
```

Complete the UniTN login in the small window that opens, then enter your
system password when prompted by `sudo` (needed to create network interfaces).
PID and log are sent to `${XDG_STATE_HOME:-~/.local/state}/gp-saml-gui/`.

## Configuration

All settings are optional environment variables:

| Variable                  | Use                                                            |
|---------------------------|----------------------------------------------------------------|
| `GP_SAML_GUI_PYTHON`      | Python executable path or command name                         |
| `GP_SAML_GUI_CLIENTOS`    | GlobalProtect client OS: `Mac` (default), `Linux` or `Windows` |
| `GP_SAML_GUI_HIP_REPORT`  | Path to OpenConnect's `hipreport.sh`                           |
| `GP_SAML_GUI_VPNC_SCRIPT` | Path to a non-standard `vpnc-script`                           |

Without `GP_SAML_GUI_PYTHON`, the helper uses the first of `.venv/bin/python3`,
`.direnv/*/bin/python3` and `python3` from `PATH`. That environment must
contain `requests` and `pywebview`, else it will just catastrophically crash.

The client OS defaults to `Mac` on Linux too, since that is the profile known
to work; try `GP_SAML_GUI_CLIENTOS=Linux gp-saml-gui-unitn start` to check the
alternative. If it works, contact me ASAP.

## How it works

- The helper authenticates directly to the gateway. Portal authentication can
  succeed while the gateway still requires a separate SAML login, and a
  consumed portal cookie cannot be reused for it. Thus, the helper has to obtain a
  fresh gateway cookie and passes it to OpenConnect with
  `--usergroup=gateway:prelogin-cookie`.
- It uses `--allow-insecure-crypto` (yeah...) for compatibility with the UniTN
  endpoint.
- OpenConnect runs in the background through `libexec/gp-saml-vpnc-script`,
  which finds the system `vpnc-script`. On macOS it also applies some
  workarounds for `/32` routes and DNS; these are not applied on Linux (yet).
- `bin/` holds only the user-facing command; internal helpers live in
  `libexec/`.

## The underlying gp-saml-gui

`gp_saml_gui.py` is essentially untouched and you can use it on other
GlobalProtect VPNs. Its options are in the man page (`man ./gp-saml-gui.8`);
for general usage see the [upstream README][dlenski/gp-saml-gui].

## License

GPLv3 or newer.
