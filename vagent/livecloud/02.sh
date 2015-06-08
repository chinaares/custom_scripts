#!/bin/bash

set -x

XEN_IPS=( )
XEN_SIZE=900G
NSP_IPS=( '172.16.1.122' '172.16.1.126' )
KVM_IPS=( '172.16.1.104' '172.16.1.106' '172.16.1.112' )
passwd=yunshan3302 
LOGFILE=/var/log/config_host.log

log()
{
    echo $1 | tee -a $LOGFILE
}

update_xen_host()
{
    log "Init Xen ..."
    cd /usr/local/livecloud/xen
    for b in ${XEN_IPS[@]}; do
        /usr/local/livecloud/script/lc_xenctl.sh config $b root \
            $passwd | tee -a $LOGFILE
    done
    (echo y; ) | /usr/local/livecloud/script/lc_xenctl.sh \
        update agent xen | tee -a $LOGFILE
    cd -
}

update_nsp()
{
    log "Init NSP ..."
    cd /usr/local/livecloud/nsp
    for b in ${NSP_IPS[@]}; do
        /usr/local/livecloud/script/lc_xenctl.sh config $b root \
            $passwd | tee -a $LOGFILE
    done
    (echo y; ) | /usr/local/livecloud/script/lc_xenctl.sh \
        update nsp-livegate | tee -a $LOGFILE
    cd -
}

update_kvm()
{
    log "Init KVM ..."
    cd /usr/local/livecloud/kvm
    for b in ${KVM_IPS[@]}; do
        /usr/local/livecloud/script/lc_xenctl.sh config $b root \
            $passwd | tee -a $LOGFILE
    done
    (echo y; ) | /usr/local/livecloud/script/lc_xenctl.sh \
        update agent kvm | tee -a $LOGFILE
    cd -
}

log "Start To Update Xen Host ..."
update_xen_host

log "Start To Update NSP Host ..."
update_nsp

log "Start To Update KVM Host ..."
update_kvm

log Done
exit 0