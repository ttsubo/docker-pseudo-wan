from fabric.api import local
from netaddr.ip import IPNetwork
from optparse import OptionParser
from httplib import HTTPConnection
from oslo_config import cfg
import json
import sys
import os.path
import time

bgp_opts = []
port_opts = []

bgp_opts.append(cfg.StrOpt('as_number', default=[], help='as_number'))
bgp_opts.append(cfg.StrOpt('router_id', default=[], help='router_id'))
bgp_opts.append(cfg.StrOpt('label_range_start', default=[], help='label_range_start'))
bgp_opts.append(cfg.StrOpt('label_range_end', default=[], help='label_range_end'))

port_opts.append(cfg.StrOpt('port', default=[], help='OpenFlow Port'))
port_opts.append(cfg.StrOpt('macaddress', default=[], help='MacAddress'))
port_opts.append(cfg.StrOpt('ipaddress', default=[], help='IpAddress'))
port_opts.append(cfg.StrOpt('netmask', default=[], help='netmask'))
port_opts.append(cfg.StrOpt('opposite_ipaddress', default=[],
                   help='opposite_IpAddress'))
port_opts.append(cfg.StrOpt('opposite_asnumber', default=[],
                   help='opposite_asnumber'))
port_opts.append(cfg.StrOpt('port_offload_bgp', default=[], help='port_offload_bgp'))
port_opts.append(cfg.StrOpt('bgp_med', default=[], help='bgp_med'))
port_opts.append(cfg.StrOpt('bgp_local_pref', default=[], help='bgp_local_pref'))
port_opts.append(cfg.StrOpt('bgp_filter_asnumber', default=[], help='bgp_filter_asnumber'))
port_opts.append(cfg.StrOpt('vrf_routeDist', default=[], help='vrf_routeDist'))


CONF = cfg.CONF
CONF.register_cli_opts(bgp_opts, 'Bgp')
CONF.register_cli_opts(port_opts, 'Port')


host_serial_number = 0
port_serial_number = 2
macaddr_serial_number = 0
macaddr_prefix = '00-00-00-'
dpid = "0000000000000001"
HOST = "127.0.0.1"
PORT = "8080"


def install_docker_and_tools():
    print "start install packages of test environment."
    local("apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys "
          "36A1D7869245C8950F966E92D8576A8BA88D21E9", capture=True)
    local('sh -c "echo deb https://get.docker.io/ubuntu docker main > /etc/apt/sources.list.d/docker.list"',
          capture=True)
    local("apt-get update", capture=True)
    local("apt-get install -y --force-yes lxc-docker-1.7.0 bridge-utils tcpdump", capture=True)
    local("ln -sf /usr/bin/docker.io /usr/local/bin/docker", capture=True)
    local("wget https://raw.github.com/jpetazzo/pipework/master/pipework -O /usr/local/bin/pipework",
          capture=True)
    local("chmod 755 /usr/local/bin/pipework", capture=True)
    local("docker pull ubuntu:14.04.2", capture=True)
    local("docker pull ttsubo/ryubgp-w-ovs2_3_1:latest", capture=True)
    local("mkdir -p /var/run/netns", capture=True)

def request_info(url_path, method, request=None):
    session = HTTPConnection("%s:%s" % (HOST, PORT))

    header = {
        "Content-Type": "application/json"
        }
    if method == "GET":
        if request:
            session.request("GET", url_path, request, header)
        else:
            session.request("GET", url_path, "", header)
    elif method == "POST":
        session.request("POST", url_path, request, header)
    elif method == "PUT":
        session.request("PUT", url_path, request, header)
    elif method == "DELETE":
        session.request("DELETE", url_path, request, header)

    session.set_debuglevel(4)
    return json.load(session.getresponse())

class Router(object):
    def __init__(self, name):
        self.name = name
        self.image = 'ttsubo/ryubgp-w-ovs2_3_1:latest'

        if self.name in get_containers():
            print ("--- Delete container {0} ---".format(self.name))
            self.stop()

    def start_openvswitch(self, host):
        local("docker exec {0} /tmp/start_ovs.sh".format(host), capture=True)
        local("docker exec {0} ovs-vsctl add-br br0".format(host), capture=True)
        local("docker exec {0} ovs-vsctl set-controller br0 tcp:127.0.0.1:6633".format(host), capture=True)
        local("docker exec {0} ovs-vsctl set bridge br0 other-config:datapath-id=0000000000000001".format(host), capture=True)
        local("docker exec {0} ovs-vsctl set bridge br0 protocols=OpenFlow13".format(host), capture=True)
        local("docker exec {0} ovs-vsctl set-fail-mode br0 secure".format(host), capture=True)
        local("docker exec {0} ovs-vsctl set bridge br0 datapath_type=netdev".format(host), capture=True)


    def start_simpleRouter(self, host):
        local("docker exec -d {0} ryu-manager /root/simpleRouter/ryu-app/openflowRouter.py --log-config-file /root/simpleRouter/ryu-app/logging.conf".format(host), capture=True)

    def start_bgpspeaker(self, asNum, routerId, labelStart, labelEnd):
        current_dir = os.getcwd()
        c = CmdBuffer(' ')
        c << "docker run --privileged=true"
        c << "-v {0}/work:/tmp -p 8080:8080".format(current_dir)
        c << "--name {0} -h {1} -itd {1}".format(self.name, self.image)
        c << "bash"

        print ("--- Create container {0} ---".format(self.name))
        self.id = local(str(c), capture=True)
        self.start_openvswitch(self.name)
        self.start_simpleRouter(self.name)
        time.sleep(2)
        result = self.regist_bgp_param(asNum, routerId, labelStart, labelEnd)
        print ("result: [%s]"%result)
        self.is_running = True

    def regist_bgp_param(self, as_num, router_id, label_start, label_end):
        url_path = "/openflow/" + dpid + "/bgp"
        method = "POST"
        request = {}
        bgp_param = {}
        bgp_param["as_number"] = as_num
        bgp_param["router_id"] = router_id
        bgp_param["label_range_start"] = label_start
        bgp_param["label_range_end"] = label_end
        request["bgp"] = bgp_param
        return request_info(url_path, method, str(request))

    def regist_interface_param(self, port, macaddress, ipaddress, netmask, opposite_ipaddress, opposite_asnumber, port_offload_bgp, bgp_med="", bgp_local_pref="", bgp_filter_asnumber="", vrf_routeDist=""):
        url_path = "/openflow/" + dpid + "/interface"
        method = "POST"
        request = {}
        if_param = {}
        if_param["port"] = port
        if_param["macaddress"] = macaddress
        if_param["ipaddress"] = ipaddress
        if_param["netmask"] = netmask
        if_param["opposite_ipaddress"] = opposite_ipaddress
        if_param["opposite_asnumber"] = opposite_asnumber
        if_param["port_offload_bgp"] = port_offload_bgp
        if_param["bgp_med"] = bgp_med
        if_param["bgp_local_pref"] = bgp_local_pref
        if_param["bgp_filter_asnumber"] = bgp_filter_asnumber
        if_param["vrf_routeDist"] = vrf_routeDist
        request["interface"] = if_param
        return request_info(url_path, method, str(request))

    def regist_vrf_param(self, route_dist, importRt, exportRt):
        url_path = "/openflow/" + dpid + "/vrf"
        method = "POST"
        request = {}
        vrf_param = {}
        vrf_param["route_dist"] = route_dist
        vrf_param["import"] = importRt
        vrf_param["export"] = exportRt
        request["vrf"] = vrf_param
        return request_info(url_path, method, str(request))

    def regist_redistribute_on(self, redistribute, vrf_routeDist):
        url_path = "/openflow/" + dpid + "/redistribute"
        method = "POST"
        request = {}
        redistribute_param = {}
        redistribute_param["redistribute"] = redistribute
        redistribute_param["vrf_routeDist"] = vrf_routeDist
        request["bgp"] = redistribute_param
        return request_info(url_path, method, str(request))

    def regist_route_param(self, destination, netmask, nexthop, routeDist):
        url_path = "/openflow/" + dpid + "/route"
        method = "POST"
        request = {}
        route_param = {}
        route_param["destination"] = destination
        route_param["netmask"] = netmask
        route_param["nexthop"] = nexthop
        route_param["vrf_routeDist"] = routeDist
        request["route"] = route_param
        return request_info(url_path, method, str(request))

    def create_wan_port(self, ifname, peer_addr, mac_addr):
        ifname_internal = "bgpPort_" + str(ifname)
        self.pipework('br_openflow', ifname, self.name)
        local("docker exec {0} ovs-vsctl add-port br0 {1}".format(self.name, ifname), capture=True)
        local("docker exec {0} ovs-vsctl add-port br0 {1} -- set Interface {1} type=internal".format(self.name, ifname_internal), capture=True)
        local("docker exec {0} ip addr add {1} dev {2}".format(self.name, peer_addr, ifname_internal), capture=True)
        local("docker exec {0} ip link set {1} address {2}".format(self.name, ifname_internal, mac_addr), capture=True)
        local("docker exec {0} ip link set {1} up".format(self.name, ifname_internal), capture=True)

    def create_lan_port(self, ifname, br_name, tenant_ip):
        self.pipework(br_name, ifname, self.name)
        local("docker exec {0} ovs-vsctl add-port br0 {1}".format(self.name, ifname), capture=True)

    def stop(self):
        local("docker rm -f " + self.name, capture=False)
        self.is_running = False

    def pipework(self, bridge, ifname, host):
        if not self.is_running:
            print ('*** call run() before pipeworking')
            return
        c = CmdBuffer(' ')
        c << "pipework {0}".format(bridge)

        if ifname != "":
            c << "-i {0} {1} 0.0.0.0/0".format(ifname, host)
            print ("--- add_link_for_tenant {0} ---".format(ifname))
            return local(str(c), capture=True)


class Host(object):
    def __init__(self, name, serial, conn_ip, tenant_ip, tenant_num):
        self.name = name
        self.image = 'ubuntu:14.04.2'
        self.serial = serial
        self.conn_ip = conn_ip
        self.tenant_ip = tenant_ip
        self.tenant_num = tenant_num

        if self.name in get_containers():
            print ("--- Delete container {0} ---".format(self.name))
            self.stop()

    def run(self):
        c = CmdBuffer(' ')
        c << "docker run --privileged=true --net=none"
        c << "--name {0} -h {1} -itd {1}".format(self.name, self.image)
        c << "bash"

        print ("--- Create container {0} ---".format(self.name))
        self.id = local(str(c), capture=True)
        self.is_running = True
        self.add_link_for_wan(self.name, self.serial, self.conn_ip)
        self.add_link_for_lan(self.name, self.serial, self.tenant_ip, self.tenant_num)
        self.add_gw(self.conn_ip)
        return 0

    def add_link_for_wan(self, host, serial, hostip):
        subnet = IPNetwork(hostip)
        ipaddr = subnet.ip + 2
        mask = subnet.netmask
        prefix = IPNetwork(str(ipaddr) + '/' + str(mask))

        br_name = "br%03d"%serial + '-0'
        ifname = 'eth0'
        self.pipework(br_name, ifname, host, prefix)

    def add_link_for_lan(self, host, serial, hostip, num):
        for i in range(num):
            subnet = IPNetwork(hostip)
            ipaddr = subnet.ip + (256 * i) + 1
            mask = subnet.netmask
            prefix = IPNetwork(str(ipaddr) + '/' + str(mask))

            br_name = "br%03d"%serial + '-' + str(i+1)
            ifname = 'eth'+str(i+1)
            self.pipework(br_name, ifname, host, prefix)

    def add_gw(self, conn_ip):
        subnet = IPNetwork(conn_ip)
        ipaddr = subnet.ip + 1
        gateway = str(ipaddr)

        c = CmdBuffer(' ')
        c << "docker exec {0}".format(self.name)
        c << "route add -net 0.0.0.0/0 gw {0}".format(gateway)
        print ("--- Add gateway {0} ---".format(self.name))
        return local(str(c), capture=True)

    def stop(self):
        local("docker rm -f " + self.name, capture=False)
        self.is_running = False

    def pipework(self, bridge, ifname, host, ip_addr):
        if not self.is_running:
            print ('*** call run() before pipeworking')
            return
        c = CmdBuffer(' ')
        c << "pipework {0}".format(bridge)

        if ifname != "":
            c << "-i {0}".format(ifname)
            c << "{0} {1}".format(host, ip_addr)
            print ("--- add_link_for_tenant {0} ---".format(ifname))
            return local(str(c), capture=True)


class CmdBuffer(list):
    def __init__(self, delim='\n'):
        super(CmdBuffer, self).__init__()
        self.delim = delim

    def __lshift__(self, value):
        self.append(value)

    def __str__(self):
        return self.delim.join(self)


def get_bridges():
    return local("brctl show | awk '$3==\"no\"{print $1}'| grep -v 'docker0'",
                 capture=True).split('\n')

def get_containers():
    output = local("docker ps -a | awk 'NR > 1 {print $NF}'", capture=True)
    if output == '':
        return []
    return output.split('\n')



def start_deploy():

    print "###########################"
    print "1. Start bgpspeaker"
    print "###########################"
    print "--- start_bgpspeaker ---"
    try:
        CONF(default_config_files=['OpenFlow.ini'])
        as_number = CONF.Bgp.as_number
        router_id = CONF.Bgp.router_id
        label_range_start = CONF.Bgp.label_range_start
        label_range_end = CONF.Bgp.label_range_end
    except cfg.ConfigFilesNotFoundError:
        print "Error: Not Found <OpenFlow.ini> "
    ryubgp = Router('BGP')
    ryubgp.start_bgpspeaker(as_number, router_id, label_range_start, label_range_end)

    print "###########################"
    print "2. Activate Wan interface"
    print "###########################"
    print "--- create_wan_interface ---"
    try:
        CONF(default_config_files=['OpenFlow.ini'])
        port = CONF.Port.port
        macaddress = CONF.Port.macaddress
        ipaddress = CONF.Port.ipaddress
        netmask = CONF.Port.netmask
        opposite_ipaddress = CONF.Port.opposite_ipaddress
        opposite_asnumber = CONF.Port.opposite_asnumber
        port_offload_bgp = CONF.Port.port_offload_bgp
        bgp_med = CONF.Port.bgp_med
        bgp_local_pref = CONF.Port.bgp_local_pref
        bgp_filter_asnumber = CONF.Port.bgp_filter_asnumber
        vrf_routeDist = CONF.Port.vrf_routeDist
    except cfg.ConfigFilesNotFoundError:
        print "Error: Not Found <OpenFlow.ini> "

    wan_subnet = IPNetwork(ipaddress + '/' + netmask)
    ryubgp.create_wan_port('eth1', wan_subnet, macaddress)
    local("brctl addif br_openflow eth1", capture=True)
    time.sleep(2)
    ret = ryubgp.regist_interface_param(port, macaddress, ipaddress, netmask,
                                    opposite_ipaddress, opposite_asnumber,
                                    port_offload_bgp, bgp_med, bgp_local_pref,
                                    bgp_filter_asnumber, vrf_routeDist)
    print ("result: [%s]"%ret)
    return ryubgp


def create_prefix(ryubgp, connectPrefix_init, localPrefix_init, routeDist_init, num):
    global port_serial_number
    global host_serial_number
    global macaddr_serial_number
    routeDist_split = routeDist_init.split(":")
    routeDist_prefix = routeDist_split[0] + ':'
    routeDist_serial_number = int(routeDist_split[1])
    print routeDist_prefix
    print routeDist_serial_number
    
    print "###########################"
    print "3. Activate Lan interface"
    print "###########################"
    for current in range(1, num+1):
        if current == 1:
            connect_prefix = connectPrefix_init
            local_prefix = localPrefix_init
            route_dist = routeDist_prefix +  "%03d"%routeDist_serial_number
        else:
            connect_subnet = IPNetwork(connect_prefix)
            connect_ipaddr = connect_subnet.ip + 256 * 256
            connect_mask = connect_subnet.netmask
            connect_prefix = IPNetwork(str(connect_ipaddr) + '/' + str(connect_mask))
            local_subnet = IPNetwork(local_prefix)
            local_ipaddr = local_subnet.ip + 256 * 256
            local_mask = local_subnet.netmask
            local_prefix = IPNetwork(str(local_ipaddr) + '/' + str(local_mask))
            routeDist_serial_number += 1
            route_dist = routeDist_prefix +  "%03d"%routeDist_serial_number

        port_serial_number += 1
        macaddr_serial_number += 1
        host_serial_number += 1

        hosts = []
        host = "host_%03d"%host_serial_number

        print "///////////////////////////"
        print "Create Host"
        print "///////////////////////////"
        print "--- create_host ({0}) ---".format(host)
        hostname = Host(host, host_serial_number, connect_prefix, local_prefix, 5)
        hosts.append(hostname)
        [host.run() for host in hosts]

        print "///////////////////////////"
        print "create_vrf ({0})".format(route_dist)
        print "///////////////////////////"
        ret = ryubgp.regist_vrf_param(route_dist, route_dist, route_dist)
        print ("result: [%s]"%ret)
        time.sleep(3)

        print "////////////////////////////////////////"
        print "create_lan_interface ({0})".format(route_dist)
        print "////////////////////////////////////////"
        br_name = "br%03d"%host_serial_number + '-0'
        if_name = 'eth'+str(port_serial_number)
        ryubgp.create_lan_port(if_name, br_name, connect_prefix)

        mac = str("{:06X}".format(macaddr_serial_number))
        macaddr = macaddr_prefix + mac[0:2] + '-' + mac[2:4] + '-' + mac[4:6]
        interface_subnet = IPNetwork(connect_prefix)
        router_ipaddress = interface_subnet.ip + 1
        netmask = interface_subnet.netmask
        host_ipaddress = interface_subnet.ip + 2
        opposite_asnumber = ""
        port_offload_bgp = ""
        bgp_med = ""
        bgp_local_pref = ""
        bgp_filter_asnumber = ""
        ret = ryubgp.regist_interface_param(str(port_serial_number),
                                          str(macaddr), str(router_ipaddress),
                                          str(netmask), str(host_ipaddress),
                                          opposite_asnumber, port_offload_bgp,
                                          bgp_med, bgp_local_pref,
                                          bgp_filter_asnumber, route_dist)
        print ("result: [%s]"%ret)
        time.sleep(3)

        print "////////////////////////////////////////"
        print "set_redistribute_on ({0})".format(route_dist)
        print "////////////////////////////////////////"
        redistribute = "ON"
        ret = ryubgp.regist_redistribute_on(redistribute, route_dist)
        print ("result: [%s]"%ret)
        time.sleep(3)

        print "////////////////////////////////////////"
        print "create_route ({0})".format(route_dist)
        print "////////////////////////////////////////"
        host_subnet = IPNetwork(local_prefix)
        destination = host_subnet.ip
        netmask = host_subnet.netmask
        ret = ryubgp.regist_route_param(str(destination), str(netmask),
                                        str(host_ipaddress), route_dist)
        print ("result: [%s]"%ret)

def create_tenant():
    ryubgp = start_deploy()
    create_prefix(ryubgp, '130.1.0.0/24', '140.1.1.0/24','9598:101', 3)
    create_prefix(ryubgp, '131.1.0.0/24', '141.1.1.0/24','9598:201', 3)


if __name__ == '__main__':
    parser = OptionParser(usage="usage: %prog [install|stop|")
    options, args = parser.parse_args()

    if len(args) == 0:
        create_tenant()
    elif args[0] == 'install':
        install_docker_and_tools()
    elif args[0] == 'stop':
        for ctn in get_containers():
            local("docker rm -f {0}".format(ctn), capture=True)

        for bridge in get_bridges():
            local("ip link set down dev {0}".format(bridge), capture=True)
            local("ip link delete {0} type bridge".format(bridge), capture=True)
