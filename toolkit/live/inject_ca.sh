#!/system/bin/sh
# Runs as root on the emulator. $1 is the certificate file, named <subject_hash_old>.0.
# Android 14+ reads CA certificates from the Conscrypt APEX, per process, so bind a copy into the
# zygotes (new apps) and every running app. The change lives in memory and is gone after a reboot.
set -e
CERT="$1"
mkdir -p -m 700 /data/local/tmp/ca-copy
cp /apex/com.android.conscrypt/cacerts/* /data/local/tmp/ca-copy/
mount -t tmpfs tmpfs /system/etc/security/cacerts
mv /data/local/tmp/ca-copy/* /system/etc/security/cacerts/
mv "$CERT" /system/etc/security/cacerts/
chown root:root /system/etc/security/cacerts/*
chmod 644 /system/etc/security/cacerts/*
chcon u:object_r:system_file:s0 /system/etc/security/cacerts/*
ZYGOTES="$(pidof zygote || true) $(pidof zygote64 || true)"
for pid in $ZYGOTES; do
  nsenter --mount=/proc/$pid/ns/mnt -- /bin/mount --bind /system/etc/security/cacerts /apex/com.android.conscrypt/cacerts
done
for zygote in $ZYGOTES; do
  for pid in $(ps -o PID -P "$zygote" | grep -v PID); do
    nsenter --mount=/proc/$pid/ns/mnt -- /bin/mount --bind /system/etc/security/cacerts /apex/com.android.conscrypt/cacerts &
  done
done
wait
rm -rf /data/local/tmp/ca-copy
echo injected
