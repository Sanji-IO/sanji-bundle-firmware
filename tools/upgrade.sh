#!/bin/sh

# MAR-2000: upgradehfm -y /run/shm/LATEST_FIRMWARE
# UC-8100: apt-get update; apt-get upgrade uc8100-system

mar2000 ()
{
	upgradehfm -y /run/shm/LATEST_FIRMWARE
	if [ $? -ne 0 ]; then
		return 1
	fi
	return 0
}

uc8100 ()
{
	apt-get update
	if [ $? -ne 0 ]; then
		echo "Cannot update the database, please check the internet."
		return 1
	fi
	apt-get upgrade --only-upgrade mxcloud-cg
	#apt-get install --only-upgrade uc8100-system
	if [ $? -ne 0 ]; then
		return 1
	fi
	return 0
}

PRODUCT=$(kversion | cut -d" " -f1 | sed -e "s/-LX//g")
case $PRODUCT in
	"UC-8100" | "UC-8112" | "UC-8131" | "UC-8132" | "UC-8162")
		uc8100
		;;
	"MAR-2000" | "MAR-2001" | "MAR-2002")
		mar2000
		;;
esac
exit $?

