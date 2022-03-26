#!/bin/bash

pip install .
sudo mkdir -p /usr/local/lib/systemd/user
sudo cp services/evdev_transformer@.service /usr/local/lib/systemd/user/
