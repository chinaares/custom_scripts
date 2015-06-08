#!/bin/bash

set -x

OSS_DOMAIN=OSS_Test
OSS_DOMAIN_ID=49cb0c40-0746-4ee8-8ad0-d5f08c74c534
OSS_CONTROLLER=10.33.37.24
BSS_DOMAIN=BSS_Test
BSS_DOMAIN_ID=79076285-f4cf-46d3-864c-bc216ca4c9f3
BSS_CONTROLLER=10.33.37.23
RACK1_NSP_IPS=( '172.16.1.122' )
RACK2_NSP_IPS=( '172.16.1.126' )
RACK1_KVM_IPS=( '172.16.1.104' '172.16.1.112' )
RACK2_KVM_IPS=( '172.16.1.106' )
RACK1_XEN_IPS=( )
RACK2_XEN_IPS=( )
LOGFILE=/var/log/config_host.log
PASSWD=yunshan3302

SERVER_CTRL_PRE=172.16.1
VM_CTRL_PRE=172.16.187
VM_SERVICE_PRE=172.18.187

log()
{
    echo $1 | tee -a $LOGFILE
}

add_domain()
{
    log "Add domain ... "    
    str1="INSERT INTO \`domain_v2_2\` VALUES (NULL,'"$OSS_DOMAIN"',
'"$OSS_CONTROLLER"',2,'"$OSS_DOMAIN_ID"','"$OSS_CONTROLLER"');"
    /usr/bin/mysql -D livecloud -e "$str1" 
    str1="INSERT INTO \`domain_v2_2\` VALUES (NULL,'"$BSS_DOMAIN"',
'"$BSS_CONTROLLER"',1,'"$BSS_DOMAIN_ID"','"$BSS_CONTROLLER"');"
    /usr/bin/mysql -D livecloud -e "$str1" 

    str1="INSERT INTO \`domain_configuration_v2_2\` VALUES 
(NULL,'controller_ctrl_ip_min','','"$OSS_DOMAIN_ID"'),
(NULL,'controller_ctrl_ip_max','','"$OSS_DOMAIN_ID"'),
(NULL,'controller_ctrl_ip_netmask','','"$OSS_DOMAIN_ID"'),
(NULL,'vm_ctrl_ip_min','','"$OSS_DOMAIN_ID"'),
(NULL,'vm_ctrl_ip_max','','"$OSS_DOMAIN_ID"'),
(NULL,'vm_ctrl_ip_netmask','','"$OSS_DOMAIN_ID"'),
(NULL,'server_ctrl_ip_min','','"$OSS_DOMAIN_ID"'),
(NULL,'server_ctrl_ip_max','','"$OSS_DOMAIN_ID"'),
(NULL,'server_ctrl_ip_netmask','','"$OSS_DOMAIN_ID"'),
(NULL,'service_provider_ip_min','','"$OSS_DOMAIN_ID"'),
(NULL,'service_provider_ip_max','','"$OSS_DOMAIN_ID"'),
(NULL,'service_provider_ip_netmask','','"$OSS_DOMAIN_ID"'),
(NULL,'vm_service_ip_min','','"$OSS_DOMAIN_ID"'),
(NULL,'vm_service_ip_max','','"$OSS_DOMAIN_ID"'),
(NULL,'vm_service_ip_netmask','','"$OSS_DOMAIN_ID"'),
(NULL,'ctrl_plane_vlan','','"$OSS_DOMAIN_ID"'),
(NULL,'serv_plane_vlan','','"$OSS_DOMAIN_ID"'),
(NULL,'ctrl_plane_bandwidth','104857600','"$OSS_DOMAIN_ID"'),
(NULL,'serv_plane_bandwidth','104857600','"$OSS_DOMAIN_ID"'),
(NULL,'tunnel_protocol','VXLAN','"$OSS_DOMAIN_ID"');"
    /usr/bin/mysql -D livecloud -e "$str1"
}

add_base()
{
    log "Add cluster ... "
    mt cluster.add name=regression domain=$OSS_DOMAIN

    log "Add rack ... "
    license=$(mt license.generate user_name=Yunshan rack_serial_num=1 \
server_num=10 lease=12 activation_time=`date +"%Y-%m-%d"`)
    mt rack.add cluster_name=regression name=rack1 license=${license} switch_type=Ethernet
    license=$(mt license.generate user_name=Yunshan rack_serial_num=2 \
server_num=10 lease=12 activation_time=`date +"%Y-%m-%d"`)
    mt rack.add cluster_name=regression name=rack2 license=${license} switch_type=Ethernet
    mt vlantag-ranges.config rack_name=rack1 ranges=10-1000
    mt vlantag-ranges.config rack_name=rack2 ranges=10-1000

    log "Add ip ranges ... "
    mt ip-ranges.config type=SERVER_CTRL ip_min=${SERVER_CTRL_PRE}.0 \
    ip_max=${SERVER_CTRL_PRE}.255 netmask=16 domain=$OSS_DOMAIN
    mt ip-ranges.config type=VM_CTRL ip_min=${VM_CTRL_PRE}.0 \
    ip_max=${VM_CTRL_PRE}.255 netmask=16 domain=$OSS_DOMAIN
    mt ip-ranges.config type=VM_SERVICE ip_min=${VM_SERVICE_PRE}.0 \
    ip_max=${VM_SERVICE_PRE}.255 netmask=16 domain=$OSS_DOMAIN
}

add_host()
{
    log "Add gateway ... "
    for host in ${RACK1_NSP_IPS[@]}; do
        mt host.add ip=${RACK1_NSP_IPS} type=NSP uplink_ip="192.168.2.${RACK1_NSP_IPS##*.}" \
        uplink_netmask=16 uplink_gateway=192.168.0.1 user_name=root \
        user_passwd=$PASSWD rack_name=rack1 nic_type=Gigabit 
    done
    for host in ${RACK2_NSP_IPS[@]}; do
        mt host.add ip=${RACK2_NSP_IPS} type=NSP uplink_ip="192.168.2.${RACK2_NSP_IPS##*.}" \
        uplink_netmask=16 uplink_gateway=192.168.0.1 user_name=root \
        user_passwd=$PASSWD rack_name=rack2 nic_type=Gigabit 
    done

    log "Add kvm hosts ... "
    for host in ${RACK1_KVM_IPS[@]}; do
        mt host.add ip=$host type=VM user_name=root user_passwd=$PASSWD \
            rack_name=rack1 htype=KVM nic_type=Gigabit 
    done
    for host in ${RACK2_KVM_IPS[@]}; do
        mt host.add ip=$host type=VM user_name=root user_passwd=$PASSWD \
            rack_name=rack2 htype=KVM nic_type=Gigabit 
    done

    log "Add xen hosts ... "
    for host in ${RACK1_XEN_IPS[@]}; do
        mt host.add ip=$host type=VM user_name=root user_passwd=$PASSWD \
            rack_name=rack1 htype=Xen nic_type=Gigabit
    done
    for host in ${RACK2_XEN_IPS[@]}; do
        mt host.add ip=$host type=VM user_name=root user_passwd=$PASSWD \
            rack_name=rack2 htype=Xen nic_type=Gigabit
    done

    log "Add pool ... "
    mt pool.add name=NSPPool type=NSP cluster_name=regression
    mt pool.add name=KVMPool type=VM cluster_name=regression ctype=KVM stype=local
    mt pool.add name=XenPool type=VM cluster_name=regression ctype=Xen stype=local

    log "Host join ... "
    for host in ${RACK1_NSP_IPS[@]}; do
        mt host.join ip=${RACK1_NSP_IPS} name=nsp${RACK1_NSP_IPS##*.} pool_name=NSPPool 
    done
    for host in ${RACK2_NSP_IPS[@]}; do
        mt host.join ip=${RACK2_NSP_IPS} name=nsp${RACK2_NSP_IPS##*.} pool_name=NSPPool 
    done
    for host in ${RACK1_KVM_IPS[@]}; do
        mt host.join pool_name=KVMPool ip=$host name=centos${host##*.} 
    done
    for host in ${RACK2_KVM_IPS[@]}; do
        mt host.join pool_name=KVMPool ip=$host name=centos${host##*.} 
    done
    for host in ${RACK1_XEN_IPS[@]}; do
        mt host.join pool_name=XenPool ip=$host name=xenserver${host##*.} 
    done
    for host in ${RACK2_XEN_IPS[@]}; do
        mt host.join pool_name=XenPool ip=$host name=xenserver${host##*.} 
    done
    # mt host.join ip=${gateway} name=nsp${gateway##*.} pool_name=NSPPool
    # mt host.peer-join ip1=172.16.1.111 ip2=172.16.1.112 name=xen pool_name=XenPool
}

mtps()
{
    USER_UUID=19bdb1cc-c8a9-47d4-baa3-8d49a7b89b1c
    str1="INSERT INTO \`fdb_user_v2_2\` VALUES 
(10000,1,'autotest','\$1\$pnJ4qnFW\$s/aPqss.82iaoW4WMVadh0','','',2,'','',
'autotest@yunshan.net.cn',NULL,'2015-01-01 00:15:38','','0','yunshan3302','',
2000000,0.000000000,'"$USER_UUID"');"
    /usr/bin/mysql -D livecloud -e "$str1" 

    str1="INSERT INTO \`user_v2_2\` VALUES 
(10000,'autotest','\$1\$BS5W1zRS\$1xyu33ECm6HVyUk7YIB...',2,NULL,NULL,NULL,
NULL,10,NULL,NULL,NULL,'autotest@yunshan.net.cn',0,'"$USER_UUID"');"
    /usr/bin/mysql -D livecloud -e "$str1" 

    str1="INSERT INTO \`product_specification_v2_2\` VALUES
(NULL,'ff767ffb-1993-4941-8925-de3650ca492e','虚拟网关',1,4,1,0.000000000,
'{\"description\": \"vgateway\", \"vgateway_info\": {\"wans\": 3, \"rate\": 1000, \"lans\": 3}}',
'vgateway',2,'"$OSS_DOMAIN_ID"'),
(NULL,'81a60ad8-94de-4891-b6bb-ce79ada522b6','带宽共享器',1,4,1,0.000000000,
'{\"description\": \"valve\", \"valve_info\": {\"wans\": 3, \"ips\": 9, \"lans\": 1, \"bw_weight\": {\"1\": 2, \"3\": 2, \"2\": 3, \"5\": 0, \"4\": 1, \"7\": 0, \"6\"
: 0, \"8\": 0}}}',
'valve',17,'"$OSS_DOMAIN_ID"'),
(NULL,'cdd9895e-86c6-4e25-ba02-1695dcca4de6','负载均衡器',1,4,1,0.000000000,
'{\"user_disk_size\": 0, \"description\": \"lb\", \"compute_size\": {\"mem_size\": 2, \"vcpu_num\": 2, \"sys_disk_size\": 50}}',
'lb',9,'"$OSS_DOMAIN_ID"'),
(NULL,'6c7f3d38-a592-4831-b82b-dcde97f6f1c6','通用带宽',1,4,1,0.000000000,
'{\"isp\": 0, \"description\": \"general_bandw\"}','general_bandw',5,'"$OSS_DOMAIN_ID"'),
(NULL,'ed77f5ae-f5d9-4149-ba47-b7e4ece075d8','移动带宽',1,4,1,0.000000000,
'{\"isp\": 1, \"description\": \"mobile_bandw\"}','mobile_bandw',5,'"$OSS_DOMAIN_ID"'),
(NULL,'ed77f5ae-f5d9-4149-ba47-b7e4ece075d9','联通带宽',1,4,1,0.000000000,
'{\"isp\": 2, \"description\": \"unicom_bandw\"}','unicom_bandw',5,'"$OSS_DOMAIN_ID"'),
(NULL,'cc2482f3-2b8f-4210-a6fd-7d0a7490e7e4','移动IP',1,4,1,0.000000000,
'{\"isp\": 1, \"description\": \"mobile_ip\"}','mobile_ip',4,'"$OSS_DOMAIN_ID"'),
(NULL,'cc2482f3-2b8f-4210-a6fd-7d0a7490e7e5','联通IP',1,4,1,0.000000000,
'{\"isp\": 2, \"description\": \"unicom_ip\"}','unicom_ip',4,'"$OSS_DOMAIN_ID"'),
(NULL,'df4de4fc-7994-4949-ad68-0efd48f9d110','XEN_VM',1,4,1,0.000000000,
'{\"user_disk_size\": 0, \"description\": \"xen_vm\", \"compute_size\": {\"mem_size\": 1, \"vcpu_num\": 1, \"sys_disk_size\": 40}}',
'xen_vm',1,'"$OSS_DOMAIN_ID"'),
(NULL,'df4de4fc-7994-4949-ad68-0efd48f9d111','KVM_VM',1,4,1,0.000000000,
'{\"user_disk_size\": 0, \"description\": \"kvm_vm\", \"compute_size\": {\"mem_size\": 1, \"vcpu_num\": 1, \"sys_disk_size\": 40}}',
'kvm_vm',1,'"$OSS_DOMAIN_ID"'),
(NULL,'4be7a187-6f54-4ddd-b1a2-ba8b6889f359','云硬盘',2,4,1,0.000000000,
'{\"block_device_type\": 0, \"description\": \"cloud_disk\"}','cloud_disk',19, '"$OSS_DOMAIN_ID"'),
(NULL,'4be7a187-6f54-4ddd-b1a2-ba8b6889f358','云硬盘快照',2,4,1,0.000000000,
'{\"block_device_type\": 0, \"description\": \"cloud_disk_snap\"}','cloud_disk_snap',20, '"$OSS_DOMAIN_ID"'),
(NULL,'80d5b83a-de17-4bea-840b-a81401750107','虚拟机快照',2,4,1,0.000000000,
'{\"description\": \"snapshot\"}','snapshot',11,'"$OSS_DOMAIN_ID"');"
    /usr/bin/mysql -D livecloud -e "$str1"

    XEN_POOL=`mt pool.list | awk '/XenPool/{print $6}'`
    mt pool.add-product-specification name=XenPool product_specification=xen_vm
    mt pool.add-product-specification name=KVMPool product_specification=kvm_vm
    mt pool.add-product-specification name=KVMPool product_specification=lb
}

add_IP_template()
{
    log "Add ISP ... "
    mt isp.config domain=$OSS_DOMAIN ISP=1 name=Mobile
    mt isp.config domain=$OSS_DOMAIN ISP=2 name=Unicom
    log "Add IPS ... "
    for i in `seq 160 200`; do
        mt ip.add ip=192.168.190.$i netmask=16 pool_name=NSPPool \
            gateway=192.168.0.1 ISP=1 product_specification=mobile_ip \
            domain=$OSS_DOMAIN 
    done
    for i in `seq 160 200`; do
        mt ip.add ip=10.34.190.$i netmask=16 pool_name=NSPPool \
            gateway=10.34.0.1 ISP=2 product_specification=unicom_ip \
            vlantag=4 domain=$OSS_DOMAIN
    done
    mt template.config name=centos6.3 ttype=VM domain=$OSS_DOMAIN vendor=YUNSHAN
    mt template.config name=centos6.5 ttype=VM domain=$OSS_DOMAIN vendor=YUNSHAN
    mt template.config name=centos6.6 ttype=VM domain=$OSS_DOMAIN vendor=YUNSHAN
    mt template.config name=centos7.0 ttype=VM domain=$OSS_DOMAIN vendor=YUNSHAN
    mt template.config name=debian7.8 ttype=VM domain=$OSS_DOMAIN vendor=YUNSHAN
    mt template.config name=debian8.0 ttype=VM domain=$OSS_DOMAIN vendor=YUNSHAN
    mt template.config name=ubuntu12.04 ttype=VM domain=$OSS_DOMAIN vendor=YUNSHAN 
    mt template.config name=ubuntu14.04 ttype=VM domain=$OSS_DOMAIN vendor=YUNSHAN 
    mt template.config name=opensuse12.3 ttype=VM domain=$OSS_DOMAIN vendor=YUNSHAN 
    mt template.config name=opensuse13.1 ttype=VM domain=$OSS_DOMAIN vendor=YUNSHAN 
    mt template.config name=opensuse13.2 ttype=VM domain=$OSS_DOMAIN vendor=YUNSHAN 
    mt template.config name=centos6.5-lb ttype=LoadBalancer domain=$OSS_DOMAIN vendor=YUNSHAN
    mt storage.list | awk '/SR_Local/{cmd="mt storage.activate id="$1" host="$7;system(cmd)}'
    for host in ${RACK1_KVM_IPS[@]}; do
        mt storage.add backend=ceph-rbd domain=$OSS_DOMAIN name=capacity type=CAPACITY host=$host 
        mt storage.add backend=ceph-rbd domain=$OSS_DOMAIN name=performance type=PERFORMANCE host=$host 
        mt storage.add backend=ceph-rbd domain=$OSS_DOMAIN name=template type=CAPACITY host=$host 
    done
    for host in ${RACK2_KVM_IPS[@]}; do
        mt storage.add backend=ceph-rbd domain=$OSS_DOMAIN name=capacity type=CAPACITY host=$host 
        mt storage.add backend=ceph-rbd domain=$OSS_DOMAIN name=performance type=PERFORMANCE host=$host 
        mt storage.add backend=ceph-rbd domain=$OSS_DOMAIN name=template type=CAPACITY host=$host 
    done
}

reload_talker()
{
    kill -9 `ps -ef| grep talker | grep -v "grep" | awk '{print $2}'`
    /usr/bin/python /usr/local/livecloud/bin/talker/talker.py -d
}

add_domain
add_base
add_host
mtps
add_IP_template
reload_talker

echo "Domain id is $OSS_DOMAIN_ID"

echo "Done"
exit 0