1. Flash Raspbian Lite on a Micro SD card
1. On the flashed card, edit
    - `/boot/config.txt` to have `dtoverlay=dwc2`
    - `/etc/modules` to have `dwc2` and `libcomposite`
    - `/etc/rc.local` to have `/home/pi/evdev-transformer/experiments/usb_device_emu` before `exit 0`
    - `/etc/systemd/system/dhcpcd.service.d/wait.conf` to have `ExecStart=/usr/lib/dhcpcd5/dhcpcd -b -q %I` instead of the previous command. Speeds up boot by ~30 seconds when a DHCP server is not immediately available.
1. Clone this repository to `/home/pi/`
1. Boot the Pi with the card
