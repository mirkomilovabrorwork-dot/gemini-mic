"""XM5 mic trial switch (owner 2026-11-05: room voices still leak at 5-10 cm on MICUSB1).

    python xm5_trial.py on   -> app records from the WH-1000XM5 hands-free mic first
                                (falls back to MICUSB1 when the headset is off),
                                XM5 capture level -> 100 %, app restarted
    python xm5_trial.py off  -> config restored from the backup, app restarted

Not on by default: an open headset mic forces Bluetooth hands-free mode, so music
on the XM5 drops to phone quality while the trial is on.
"""
import json
import os
import shutil
import subprocess
import sys

XM5 = "WH-1000XM5"
CFG = os.path.join(os.environ["APPDATA"], "GeminiMic", "config.json")
BACKUP = CFG + ".before_xm5"
HERE = os.path.dirname(os.path.abspath(__file__))


def set_xm5_level():
    """XM5 hands-free capture endpoint -> 100 %. Returns old %, or None when not connected."""
    import comtypes
    from comtypes import CLSCTX_ALL
    from pycaw.utils import AudioUtilities
    from pycaw.constants import AudioDeviceState
    from pycaw.pycaw import IAudioEndpointVolume
    comtypes.CoInitialize()
    for d in AudioUtilities.GetAllDevices():
        if (XM5.lower() in (d.FriendlyName or "").lower() and d.state == AudioDeviceState.Active
                and "Capture" in str(AudioUtilities.GetEndpointDataFlow(d.id))):
            dev = AudioUtilities.GetDeviceEnumerator().GetDevice(d.id)
            ev = dev.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None).QueryInterface(IAudioEndpointVolume)
            old = round(ev.GetMasterVolumeLevelScalar() * 100)
            ev.SetMasterVolumeLevelScalar(1.0, None)
            ev.SetMute(0, None)
            return old
    return None


def restart_app():
    subprocess.run(["powershell", "-NoProfile", "-Command",
                    "Get-CimInstance Win32_Process -Filter \"name='pythonw.exe'\" | "
                    "Where-Object { $_.CommandLine -like '*gemini_mic.py*' } | "
                    "ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"], check=False)
    subprocess.Popen([os.path.join(HERE, ".venv", "Scripts", "pythonw.exe"), "gemini_mic.py"], cwd=HERE)


def main(mode):
    if mode == "on":
        with open(CFG, encoding="utf-8") as f:
            cfg = json.load(f)
        if not os.path.exists(BACKUP):
            shutil.copyfile(CFG, BACKUP)
        rest = [p for p in (cfg.get("input_device") or "").split("|") if p.strip() and XM5 not in p]
        cfg["input_device"] = "|".join([XM5] + rest)
        with open(CFG, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
        old = set_xm5_level()
        print("XM5 level: %s" % ("not connected - run 'on' again once it is" if old is None
                                  else "%d%% -> 100%%" % old))
    elif mode == "off":
        if not os.path.exists(BACKUP):
            sys.exit("no backup - trial was never on")
        shutil.copyfile(BACKUP, CFG)
        os.remove(BACKUP)
    else:
        sys.exit(__doc__)
    restart_app()
    print("input_device now: %s" % json.load(open(CFG, encoding="utf-8"))["input_device"])


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "")
