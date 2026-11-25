# gp-saml-gui for UniTN

If you have used the University of Trento VPN and hate closed software,
you have probably suffered enough already.

Enter `gp-saml-gui-unitn`. It connects to the UniTN GlobalProtect VPN
(`vpn-mfa.icts.unitn.it`) with SAML sign-in and OpenConnect. It works on macOS
and Linux.

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

### Arch and siblings

```sh
sudo pacman -S openconnect vpnc python python-gobject gtk3 webkit2gtk-4.1
python3 -m venv --system-site-packages .venv
.venv/bin/python3 -m pip install -r requirements-unitn.txt
```

`vpnc` provides `/etc/vpnc/vpnc-script`. Without `python-gobject` visible
from the venv, pywebview cannot open the login window.

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
to work (see the HIP report note below). `GP_SAML_GUI_CLIENTOS=Linux` is
untested: when using it, OpenConnect's HIP report claims "Linux Fedora 32",
an old version that the gateway likely bins as outdated.

## How it works

- The helper authenticates directly to the gateway. Portal authentication can
  succeed while the gateway still requires a separate SAML login, and a
  consumed portal cookie cannot be reused for it. Thus, the helper has to
  obtain a fresh gateway cookie and passes it to OpenConnect with
  `--usergroup=gateway:prelogin-cookie`.
- OpenConnect runs in the background through `libexec/gp-saml-vpnc-script`,
  which finds the system `vpnc-script` and calls it.

## Quirks and workarounds that were added

- `--allow-insecure-crypto` (yeah...) is needed for compatibility with the
  UniTN endpoint. Do not blame me.
- With the `Mac` profile on Linux, OpenConnect's `hipreport.sh` cannot find
  `sw_vers` and reports macOS 10.16.0. The gateway accepts that report but
  only lets DNS through: the tunnel comes up, names resolve, and nothing else
  answers. The helper therefore wraps `hipreport.sh` (in its state directory)
  with a `sw_vers` that reports macOS 15.6.1.
- On macOS, the vpnc-script wrapper drops `/32` netmasks that break routing
  and sets the VPN DNS servers on the active network service.
- On Linux without a running systemd-resolved (e.g. plain
  `resolvconf`/openresolv), the vpnc-script wrapper saves `/etc/resolv.conf`
  to `/run/gp-saml-gui/`, writes the UniTN DNS servers while connected, and
  restores the original when `stop` is run.

## What to do when something does not work

- **Login window does not open (Linux).** pywebview cannot import PyGObject.
  Install the distribution package (`python3-gi`, `python-gobject`, ...) and
  create the venv with `--system-site-packages`.
- **Tunnel works, DNS works, but nothing internal answers** (e.g.
  `dig @10.100.252.99 examina.icts.unitn.it` works, `curl` to it times out).
  The gateway has most likely rejected the HIP report and granted DNS-only
  access. If `gp-saml-gui-unitn logs` shows `HIP report submitted successfully`,
  UniTN probably raised the minimum macOS version: bump `15.6.1` in
  `mac_hip_wrapper` (`bin/gp-saml-gui-unitn`) to a newer version. Also, open a
  PR or an issue to update the wrapper for everyone. Will be appreciated.
- **`/etc/resolv.conf` still points to UniTN after a crash** (Linux without
  systemd-resolved). OpenConnect was killed before it could disconnect; the
  original is in `/run/gp-saml-gui/resolv.conf`, so restore it with
  `sudo cp -P /run/gp-saml-gui/resolv.conf /etc/resolv.conf`.
  If you rebooted in the meantime, I cannot help you.

## The underlying gp-saml-gui

`gp_saml_gui.py` is essentially untouched and you can use it on other
GlobalProtect VPNs. Its options are in the man page (`man ./gp-saml-gui.8`);
for general usage see the [upstream README][dlenski/gp-saml-gui].

## License

GPLv3 or newer.

## Thanks to

- [Riccardo Germenia](https://github.com/odinmylord) for testing on Linux and
  the `hipreport.sh` fix.
- [dlenski](https://github.com/dlenski) for the original `gp-saml-gui`.
- [lkrms](https://github.com/lkrms) for the pywebview fallback.
