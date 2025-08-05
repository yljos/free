#!/bin/sh
opkg update && opkg upgrade $(opkg list-upgradable | awk '{print $1}')


