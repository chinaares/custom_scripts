#!/bin/bash

source `pwd`/config.sh

product_specification="(NULL,'`uuidgen`','虚拟网关',1,4,1,0.000000000,'{\"description\": \"vgateway\", \"vgateway_info\": {\"wans\": 3, \"rate\": 1000, \"lans\": 3}}','vgateway',2,'$OSS_DOMAIN_ID'),
(NULL,'`uuidgen`','带宽共享器',1,4,1,0.000000000,'{\"description\": \"valve\", \"valve_info\": {\"wans\": 3, \"ips\": 9, \"lans\": 1, \"bw_weight\": {\"1\": 2, \"3\": 2, \"2\": 3, \"5\": 0, \"4\": 1, \"7\": 0, \"6\":  0, \"8\": 0}}}','valve',17,'$OSS_DOMAIN_ID'),
(NULL,'`uuidgen`','负载均衡器',1,4,1,0.000000000,'{\"user_disk_size\": 0, \"description\": \"lb\", \"compute_size\": {\"mem_size\": 2, \"vcpu_num\": 2, \"sys_disk_size\": 50}}','lb',9,'$OSS_DOMAIN_ID'),
(NULL,'`uuidgen`','通用带宽',1,4,1,0.000000000,'{\"isp\": 0, \"description\": \"general_bandw\"}','general_bandw',5,'$OSS_DOMAIN_ID'),
(NULL,'`uuidgen`','移动带宽',1,4,1,0.000000000,'{\"isp\": 1, \"description\": \"mobile_bandw\"}','mobile_bandw',5,'$OSS_DOMAIN_ID'),
(NULL,'`uuidgen`','联通带宽',1,4,1,0.000000000,'{\"isp\": 2, \"description\": \"unicom_bandw\"}','unicom_bandw',5,'$OSS_DOMAIN_ID'),
(NULL,'`uuidgen`','移动IP',1,4,1,0.000000000,'{\"isp\": 1, \"description\": \"mobile_ip\"}','mobile_ip',4,'$OSS_DOMAIN_ID'),
(NULL,'`uuidgen`','联通IP',1,4,1,0.000000000,'{\"isp\": 2, \"description\": \"unicom_ip\"}','unicom_ip',4,'$OSS_DOMAIN_ID'),
(NULL,'`uuidgen`','XEN_VM',1,4,1,0.000000000,'{\"user_disk_size\": 0, \"description\": \"xen_vm\", \"compute_size\": {\"mem_size\": 4, \"vcpu_num\": 2, \"sys_disk_size\": 50}}','xen_vm',1,'$OSS_DOMAIN_ID'),
(NULL,'`uuidgen`','KVM_VM',1,4,1,0.000000000,'{\"user_disk_size\": 0, \"description\": \"kvm_vm\", \"compute_size\": {\"mem_size\": 4, \"vcpu_num\": 2, \"sys_disk_size\": 50}}','kvm_vm',1,'$OSS_DOMAIN_ID'),
(NULL,'`uuidgen`','云硬盘',2,4,1,0.000000000,'{\"block_device_type\": 0, \"description\": \"cloud_disk\"}','cloud_disk',19, '$OSS_DOMAIN_ID'),
(NULL,'`uuidgen`','云硬盘快照',2,4,1,0.000000000,'{\"block_device_type\": 0, \"description\": \"cloud_disk_snap\"}','cloud_disk_snap',20, '$OSS_DOMAIN_ID'),
(NULL,'`uuidgen`','虚拟机快照',2,4,1,0.000000000,'{\"description\": \"snapshot\"}','snapshot',11,'$OSS_DOMAIN_ID');"
