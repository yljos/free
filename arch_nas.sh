#!/bin/bash

# 配置磁盘变量
DISK="/dev/mmcblk0"  # 请根据实际硬盘设备修改

# 设置时间同步
echo ">> Enabling NTP time synchronization"
timedatectl set-ntp true

# 分区磁盘
echo ">> Partitioning disk $DISK"
(
echo g                      # 创建新的 GPT 分区表
echo n                      # 创建 boot 分区
echo 1
echo
echo +512M                  # 分配 512MB 给 boot 分区
echo n                      # 创建 Swap 分区
echo 2
echo
echo +1G                    # Swap 分区 1GB
echo n                      # 创建根分区
echo 3
echo
echo                        # 将剩余的空间分配给根分区
echo t                      # 修改 boot 分区类型
echo 1
echo 1                      # 设置 boot 分区类型
echo t                      # 修改 Swap 分区类型
echo 2
echo 19                     # Linux Swap 类型
echo w                      # 写入分区表并退出
) | fdisk $DISK

# 格式化分区
echo ">> Formatting partitions"
mkfs.fat -F32 "${DISK}p1"
mkswap "${DISK}p2"
swapon "${DISK}p2"
mkfs.ext4 "${DISK}p3"
echo ">> Disk setup completed successfully!"

# 配置镜像源
echo ">> Configuring mirrorlist"
echo 'Server = http://mirrors.tuna.tsinghua.edu.cn/archlinux/$repo/os/$arch' > /etc/pacman.d/mirrorlist

# 挂载分区
echo ">> Mounting partitions"
mount "${DISK}p3" /mnt
mkdir -p /mnt/boot && mount "${DISK}p1" /mnt/boot

# 安装基本系统
echo ">> Installing base system"
pacstrap /mnt base base-devel nfs-utils linux linux-firmware vim dhcpcd zsh git rsync openssh polkit p7zip ranger curl samba mdadm

# 生成 fstab
echo ">> Generating fstab"
genfstab -U /mnt >> /mnt/etc/fstab
# 获取根分区的 UUID
ROOT_UUID=$(blkid -s UUID -o value "${DISK}p3")
# 在 chroot 环境中执行命令
echo ">> Entering chroot environment"
arch-chroot /mnt env ROOT_UUID="$ROOT_UUID" /bin/bash -c '
echo "The root UUID is: $ROOT_UUID"
sleep 10
# 设置时区
echo ">> Setting timezone"
ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime
hwclock --systohc

# 配置本地化
echo ">> Configuring localization"
echo -e "en_US.UTF-8 UTF-8" >> /etc/locale.gen
locale-gen
echo "LANG=en_US.UTF-8" > /etc/locale.conf

# 网络配置
echo ">> Configuring network"
echo "nas" > /etc/hostname
echo -e "127.0.0.1       localhost\n::1             localhost\n127.0.0.1       nas.localdomain  nas" > /etc/hosts

# 设置 root 密码
echo ">> Setting root password"
echo "root:1" | chpasswd

# 安装引导程序和 CPU 微码
echo ">> Installing systemd-boot bootloader and CPU microcode"
pacman -S --noconfirm intel-ucode efibootmgr

# 配置 systemd-boot
echo ">> Configuring systemd-boot"
bootctl install --path=/boot

# 配置 loader
echo ">> Setting up loader configuration"
echo "default arch.conf" > /boot/loader/loader.conf
echo "#timeout 5" >> /boot/loader/loader.conf
echo "#editor no" >> /boot/loader/loader.conf

# 设置 Arch Linux 启动项
echo "title   Arch Linux" > /boot/loader/entries/arch.conf
echo "linux   /vmlinuz-linux" >> /boot/loader/entries/arch.conf
echo "initrd  /initramfs-linux.img" >> /boot/loader/entries/arch.conf
echo "initrd  /intel-ucode.img" >> /boot/loader/entries/arch.conf
echo "options root=UUID=$ROOT_UUID rw quiet" >> /boot/loader/entries/arch.conf

# 添加新用户并设置密码
echo ">> Adding new user huai"
useradd -m -G wheel huai
echo "huai ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers
echo "huai:1" | chpasswd
systemctl enable sshd dhcpcd
'

# 退出并重启
echo ">> Exiting chroot and rebooting"
umount -R /mnt
reboot

