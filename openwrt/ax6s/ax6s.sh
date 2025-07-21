nvram set ssh_en=1 & nvram set uart_en=1 & nvram set boot_wait=on & nvram set bootdelay=3 & nvram set flag_try_sys1_failed=0 & nvram set flag_try_sys2_failed=1
nvram set flag_boot_rootfs=0 & nvram set "boot_fw1=run boot_rd_img;bootm"
nvram set flag_boot_success=1 & nvram commit & /etc/init.d/dropbear enable & /etc/init.d/dropbear start


cd /tmp
curl -L http://nas/factory.bin -o factory.bin
mtd -r write /tmp/factory.bin firmware
