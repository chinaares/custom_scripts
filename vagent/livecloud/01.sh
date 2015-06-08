#!/bin/bash

# oss配置

oss_pub=10.33.37.24
bss_pub=10.33.37.23
control=172.16.37.24
oss_domain=49cb0c40-0746-4ee8-8ad0-d5f08c74c534
bss_domain=79076285-f4cf-46d3-864c-bc216ca4c9f3

sed -i -e "s#\(public_ip_address\ =\ \).*#\1$oss_pub#" \
-e "s#\(controller_control_ip\ =\ \).*#\1$control#" \
-e "s#\(pxe_enabled\ =\ \).*#\1false#" lc_startup.conf

(echo y; echo oss ) | ./lc_startup.sh -i -c lc_startup.conf

sed -i -e "s#\(local_public_ip\ =\ \).*#\1$oss_pub#" \
-e "s#\(local_ctrl_ip\ =\ \).*#\1$control#" \
-e "s#\(mysql_master_ip\ =\ \).*#\1$control#" \
-e "s#\(mongo_master_ip\ =\ \).*#\1$control#" \
-e "s#\(domain.lcuuid\ =\ \).*#\1$oss_domain#" /usr/local/livecloud/conf/livecloud.conf

sed -i -e "s#\(listen \)[0-9.]*\(:80;\)#\1$oss_pub\2#" \
-e "s#\(https://\)[0-9.]*\(/;\)#\1$oss_pub\2#" /etc/nginx/conf.d/ssl.conf

sed -i -e "s#\(uuid\ =\ \).*#\1$oss_domain#" \
-e "s#\(url\ =\ \).*#\1$oss_pub#" \
-e "s#\(bss.url\ =\ \).*#\1$bss_pub#" \
-e "s#\(bss.public_url\ =\ \).*#\1$bss_pub#" \
-e "s#\(bss.uuid\ =\ \).*#\1$bss_domain#" /var/www/lcweb/lcc/config.ini

(echo security421) | livecloud refresh