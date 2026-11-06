# Live capture: what the server really sends

A package holds defaults. A server can change them per player, so a short session on an isolated emulator settles what the static read cannot. Use it only when the user asks for a live run. Learning only, as everywhere in this repository.

## What it gives, best value first

1. **The config the game saved on the device.** After one launch, read the app's data folder as root. Publisher SDKs often keep the live config as plain JSON, even when the request and reply on the wire are compressed or encrypted. Firebase Remote Config keeps the activated values in `files/frc_<app id>_firebase_activate.json`, with the template version and any A/B experiments. Diff such files against the copy bundled in the package with `toolkit/live/diff_json.py`. Parameters the server does not send keep their bundled defaults, and that is a finding too. One session showed 245 differences: other pacing, a 14-step floor ladder, a per-device floor base, a segment number and A/B experiment ids.
2. **Local state.** Shared preferences and small JSON files hold the client's segment, offers already shown and impression history.
3. **Traffic.** Which hosts, which MAX ad units and waterfalls, and when impressions fire.
4. **Logs.** `adb logcat -b all` shows what the game and SDKs print.

## Setup on a Mac (Apple silicon)

Android Studio's emulator with a **Google APIs** arm64 image, not a Google Play image: only the first allows root. Make a separate AVD for captures, so the user's own AVD is never touched.

```sh
brew install mitmproxy
mitmdump --listen-host 127.0.0.1 -p 8877 -w <live>/flows.mitm --set validate_inbound_headers=false --set normalize_outbound_headers=false
emulator -avd <capture-avd> -http-proxy http://127.0.0.1:8877 -tcpdump <live>/net.pcap -no-snapshot -gpu host   # add -wipe-data for a new device
adb root
openssl x509 -inform PEM -subject_hash_old -in ~/.mitmproxy/mitmproxy-ca-cert.pem -noout   # -> <hash>; copy the pem to <hash>.0
adb push <hash>.0 toolkit/live/inject_ca.sh /data/local/tmp/
adb shell sh /data/local/tmp/inject_ca.sh /data/local/tmp/<hash>.0
adb shell 'iptables -A OUTPUT -p udp --dport 443 -j DROP; ip6tables -A OUTPUT -p udp --dport 443 -j DROP'
adb install-multiple <work>/<game>/splits/*.apk
```

- `inject_ca.sh` handles Android 14 and later, where trusted certificates live in the Conscrypt APEX per process. The certificate lives in memory and is gone after a reboot, so run it after every boot.
- Blocking UDP 443 stops QUIC, so apps fall back to TCP through the proxy.
- Relax mitmproxy's header checks: SDKs send malformed headers (an empty `Bearer `), and strict mode drops those requests.
- `-tcpdump` records everything the emulator sends. `python3 toolkit/live/pcap_hosts.py net.pcap` lists DNS and TLS names, so you can confirm that nothing bypassed the proxy.

## Run

```sh
adb shell monkey -p <package> -c android.intent.category.LAUNCHER 1
adb exec-out 'cd /data/data/<package> && tar cf - .' > <live>/data.tar     # after the first launch
mitmdump -n -q -r <live>/flows.mitm -s toolkit/live/summarize_flows.py --set out=<live>/summary
python3 toolkit/live/diff_json.py <work>/<game>/unzipped/assets/<bundled config>.json <live>/data/<saved config>.json
```

- Drive the game from screenshots (`adb exec-out screencap -p`) and `adb shell input swipe`. Blind random swipes do not play these games: tutorials wait for a specific tap.
- Before every input, check the focused window (`dumpsys window | grep mCurrentFocus`) and never touch an ad. Close a stuck test ad by relaunching the game.
- Wait a minute after an impression before you force-stop: SDKs batch their events, and a quick kill loses them.
- `pm clear` resets the app but not the device: servers keyed on device id or advertising id still remember it. `-wipe-data` gives a new device.

## Limits

- MAX marks emulator traffic as testing: test creatives and zero revenue. Real waterfalls need a real device, and live ads on test devices can count as invalid traffic, so keep any such session short and never click.
- Encrypted requests stay closed: do not extract keys or hook the app. Do not defeat PairIP or other protection; a protected game may refuse to run, and that is the result.
- Store purchases do not work without the Play Store, so payer and whale behaviour stay out of reach.
- Many games open with a terms or consent screen and load nothing until it is accepted. Accepting is the user's decision: ask once at the start of the run.
- Some SDK replies use `Content-Encoding: encrypted`. The summary keeps their raw bytes; leave them closed.
- Scripted input does not play every game: an aiming tutorial may ignore swipes. Read what a launch gives before planning a long play session.
- One session is one player in one country and one A/B arm. Say so in every finding.
- Captures and data folders hold device ids, advertising ids and tokens. Keep them in the work folder, mask them in reports, delete the work folder afterwards.
