What's docker-pseudo-wan
==========
Dockerコンテナを活用して、MPLS-VPNネットワークの疑似環境を構築するものです.
なお、RyuBGPとBGPピア接続する対向BGPルータは、mp-BGPを動作させる必要があります.

	                       (static) +-----------+     mp-BGP    +----------+	
	host_001_101 container -------+ |  RyuBGP   | +-----------+ |   BGP    | +---- ...
	host_002_102 container -------+ | container | (eth1)        |  Router  |
	     :                          +-----------+               +----------+
	                     < AS65001 >   192.168.0.1             192.168.0.2  < AS65002 >

           <------- docker-pseudo-wanのスコープ ------>            <---- スコープ外 ---->


Environment
==========
Ubuntu Server版を推奨とします.

	$ cat /etc/lsb-release
	DISTRIB_ID=Ubuntu
	DISTRIB_RELEASE=14.04
	DISTRIB_CODENAME=trusty
	DISTRIB_DESCRIPTION="Ubuntu 14.04.3 LTS"


Dockerコンテナで構成されるWANネットワークと外部環境と通信するために、eth1のインタフェースを前提とします.
すなわち、RyuBGPと対向BGPルータのあいだでBGPピアを確立するためには、事前にeth1のインターフェースと結線しておく必要があります.

	$ ip link
	...
	3: eth1: <BROADCAST,MULTICAST,PROMISC,UP,LOWER_UP> mtu 1500 qdisc pfifo_fast state UP mode DEFAULT group default qlen 1000
	    link/ether 52:54:00:1a:b0:d5 brd ff:ff:ff:ff:ff:ff



Installation
==========
### 事前準備
OpenvSwitchをインストールして、"openvswitch"カーネルモジュールを組み込みます.
OpenvSwitch自体は起動する必要がないため、停止しておきます.

	$ sudo apt-get install openvswitch-switch
	$ sudo service openvswitch-switch stop
	openvswitch-switch stop/waiting

"openvswitch"カーネルモジュールが組み込まれたことを確認します.

	$ lsmod|grep open
	openvswitch            65844  0
	gre                    13796  1 openvswitch
	vxlan                  37629  1 openvswitch
	libcrc32c              12644  1 openvswitch

### リポジトリ情報
Githubよりリポジトリ情報を取得します.

	$ git clone https://github.com/ttsubo/docker-pseudo-wan.git

### インストール開始
ルート権限でdockerパッケージ類をインストールします.

	$ cd docker-pseudo-wan
	$ sudo apt-get install python-dev
	$ sudo apt-get install python-paramiko
	$ sudo apt-get install python-pip
	$ sudo pip install -r requirements.txt
	$ sudo python ./pseudo-wan.py install
	$ sudo gpasswd -a `whoami` docker


### インストール結果確認
グループ"docker"への反映を有効にするため、再ログインします.

	$ docker version
	Client version: 1.7.0
	Client API version: 1.19
	Go version (client): go1.4.2
	Git commit (client): 0baf609
	OS/Arch (client): linux/amd64
	Server version: 1.7.0
	Server API version: 1.19
	Go version (server): go1.4.2
	Git commit (server): 0baf609
	OS/Arch (server): linux/amd64


Dockerイメージを確認します.

	$ docker images
	REPOSITORY                  TAG                 IMAGE ID            CREATED             VIRTUAL SIZE
	ttsubo/ryubgp-for-general   latest              9dd5bb56bf3e        2 days ago          644.4 MB
	ubuntu                      14.04.3             91e54dfb1179        4 weeks ago         188.4 MB


Quick Start
===========
### BGPピア接続用の設定ファイルの編集
RyuBGPと対向BGPルータ間でBGPピアを確立するための設定を行います.

	$ vi OpenFlow.ini 
	------------------------------
	[Bgp]
	as_number = "65001"
	router_id = "10.10.10.1"
	label_range_start = "1000"
	label_range_end = "1999"

	[Port]
	port = "1"
	macaddress = "00:00:00:01:01:01"
	ipaddress = "192.168.0.1"
	netmask = "255.255.255.252"
	opposite_ipaddress = "192.168.0.2"
	opposite_asnumber = "65002"
	port_offload_bgp = "2"
	bgp_med = "100"
	bgp_local_pref = ""
	bgp_filter_asnumber = ""
	vrf_routeDist = ""


ちなみに、BGPピアを確立するためのIPアドレス値は、Linuxネットワーク設定情報を使用しません.
実際にBGPピア接続で使用するIPアドレス値は、OpenFlow.iniで指定したipaddress"192.168.0.1"が使用されます.macaddressも同様です.

	$ ip addr
	...
	3: eth1: <BROADCAST,MULTICAST,PROMISC,UP,LOWER_UP> mtu 1500 qdisc pfifo_fast state UP group default qlen 1000
	    link/ether 52:54:00:1a:b0:d5 brd ff:ff:ff:ff:ff:ff
	    inet6 fe80::5054:ff:fe1a:b0d5/64 scope link 
	       valid_lft forever preferred_lft forever


"eth1"ネットワーク設定では、プロミスキャストを有効にしておきます.

	$ sudo vi /etc/network/interfaces
	...
	auto eth1
	iface eth1 inet manual
	up ifconfig $IFACE 0.0.0.0 up
	up ip link set $IFACE promisc on
	down ip link set $IFACE promisc off
	down ifconfig $IFACE down


### Dockerコンテナ起動
WANネットワークの疑似環境を構築します.

	$ sudo python pseudo-wan.py

	(...snip)


Dockerコンテナ実行状況を確認します.

	$ docker ps
	CONTAINER ID        IMAGE                              COMMAND             CREATED             STATUS              PORTS                    NAMES
	932903e0a336        ubuntu:14.04.3                     "bash"              15 minutes ago      Up 15 minutes                                host_010_402        
	aa6dfeef1069        ubuntu:14.04.3                     "bash"              15 minutes ago      Up 15 minutes                                host_009_401        
	94ac2f40b68e        ubuntu:14.04.3                     "bash"              15 minutes ago      Up 15 minutes                                host_008_302        
	f41d84954f4a        ubuntu:14.04.3                     "bash"              15 minutes ago      Up 15 minutes                                host_007_301        
	3b7497494c22        ubuntu:14.04.3                     "bash"              15 minutes ago      Up 15 minutes                                host_006_203        
	ceb959815478        ubuntu:14.04.3                     "bash"              16 minutes ago      Up 16 minutes                                host_005_202        
	f2788cfc906e        ubuntu:14.04.3                     "bash"              16 minutes ago      Up 16 minutes                                host_004_201        
	8e82eee2cc1e        ubuntu:14.04.3                     "bash"              16 minutes ago      Up 16 minutes                                host_003_103        
	418137d00faf        ubuntu:14.04.3                     "bash"              16 minutes ago      Up 16 minutes                                host_002_102        
	2356b001d345        ubuntu:14.04.3                     "bash"              16 minutes ago      Up 16 minutes                                host_001_101        
	5d1ea536a8af        ttsubo/ryubgp-for-general:latest   "bash"              17 minutes ago      Up 17 minutes       0.0.0.0:8080->8080/tcp   RyuBGP 


### RyuBGPでの経路情報を確認
dockerコンテナ"RyuBGP"が開設しているBGPピア状態を確認してみます.
なお、コマンド操作は、Linux上で行います.

	$ cd show
	$ ./get_peer_status.sh
	======================================================================
	get_peer_status
	======================================================================
	/openflow/0000000000000001/status/peer
	----------
	reply: 'HTTP/1.1 200 OK\r\n'
	header: Content-Type: application/json; charset=UTF-8
	header: Content-Length: 200
	header: Date: Tue, 22 Sep 2015 21:19:02 GMT
	+++++++++++++++++++++++++++++++
	2015/09/22 21:19:02 : Peer Status
	+++++++++++++++++++++++++++++++
	occurTime            status    myPeer             remotePeer         asNumber
	-------------------- --------- ------------------ ------------------ --------
	2015/09/22 20:51:11  Peer Up   10.10.10.1         192.168.0.2        65002


つぎに、RyuBGPのインターフェース情報を確認してみます.
各インタフェースでのvrf収容構成については、RD値により識別することができます.

	$ ./get_interface.sh 
	======================================================================
	get_interface
	======================================================================
	/openflow/0000000000000001/interface
	----------
	reply: 'HTTP/1.1 200 OK\r\n'
	header: Content-Type: application/json; charset=UTF-8
	header: Content-Length: 1290
	header: Date: Tue, 22 Sep 2015 21:20:34 GMT
	+++++++++++++++++++++++++++++++
	2015/09/22 21:20:34 : PortTable
	+++++++++++++++++++++++++++++++
	portNo   IpAddress       MacAddress        RouteDist
	-------- --------------- ----------------- ---------
	       1 192.168.0.1     00:00:00:01:01:01 
	       3 10.1.0.1        00-00-00-00-00-01 65001:101
	       4 10.2.0.1        00-00-00-00-00-02 65001:102
	       5 10.3.0.1        00-00-00-00-00-03 65001:103
	       6 20.1.0.1        00-00-00-00-00-04 65001:201
	       7 20.2.0.1        00-00-00-00-00-05 65001:202
	       8 20.3.0.1        00-00-00-00-00-06 65001:203
	       9 30.1.0.1        00-00-00-00-00-07 65001:301
	       a 30.2.0.1        00-00-00-00-00-08 65001:302
	       b 40.1.0.1        00-00-00-00-00-09 65001:401
	       c 40.2.0.1        00-00-00-00-00-0A 65001:402


RyuBGPが保持しているARPテーブルを確認することも可能です.
もし、対向BGPルータとの間でピア接続がうまく確立できない場合には、対向BGPルータのmacaddressが正しく学習できているかを確認します.

	$ ./get_arp.sh 
	======================================================================
	get_arp
	======================================================================
	/openflow/0000000000000001/arp
	----------
	reply: 'HTTP/1.1 200 OK\r\n'
	header: Content-Type: application/json; charset=UTF-8
	header: Content-Length: 963
	header: Date: Tue, 22 Sep 2015 21:22:18 GMT
	+++++++++++++++++++++++++++++++
	2015/09/22 21:22:18 : ArpTable 
	+++++++++++++++++++++++++++++++
	portNo   MacAddress        IpAddress
	-------- ----------------- ------------
	       1 7c:c3:a1:87:8f:65 192.168.0.2
	       3 c2:00:31:6c:7d:04 10.1.0.2
	       4 06:f0:61:7c:00:86 10.2.0.2
	       5 9a:5c:84:f3:fa:65 10.3.0.2
	       6 32:e6:18:b4:73:b4 20.1.0.2
	       7 fe:9f:ee:e3:cc:72 20.2.0.2
	       8 66:13:b3:72:e9:50 20.3.0.2
	       9 aa:ce:29:6d:a2:e9 30.1.0.2
	       a f6:0b:01:f5:89:d0 30.2.0.2
	       b 56:b0:09:b8:3b:3e 40.1.0.2
	       c 92:2f:1b:71:43:9b 40.2.0.2


さらに、dockerコンテナ"RyuBGP"で保持しているBGP経路情報を確認してみます.

	$ ./get_vrf.sh
	======================================================================
	get_vrf
	======================================================================
	/openflow/0000000000000001/vrf
	----------
	reply: 'HTTP/1.1 200 OK\r\n'
	header: Content-Type: application/json; charset=UTF-8
	header: Content-Length: 12819
	header: Date: Wed, 23 Sep 2015 05:02:20 GMT
	+++++++++++++++++++++++++++++++
	2015/09/23 05:02:20 : Show vrf 
	+++++++++++++++++++++++++++++++
	Status codes: * valid, > best
	Origin codes: i - IGP, e - EGP, ? - incomplete
	     Network                          Labels   Next Hop             Reason          Metric LocPrf Path

	(...snip)

	VPN: ('65001:101', 'ipv4')
	 *>  130.1.7.0/24                     None     192.168.0.2          Only Path       100           65002 ?
	 *>  110.1.0.0/24                     None     10.1.0.2             Only Path                     ?
	 *>  110.1.2.0/24                     None     10.1.0.2             Only Path                     ?
	 *>  110.1.6.0/24                     None     10.1.0.2             Only Path                     ?
	 *>  130.1.5.0/24                     None     192.168.0.2          Only Path       100           65002 ?
	 *>  110.1.5.0/24                     None     10.1.0.2             Only Path                     ?
	 *>  130.1.2.0/24                     None     192.168.0.2          Only Path       100           65002 ?
	 *>  130.1.3.0/24                     None     192.168.0.2          Only Path       100           65002 ?
	 *>  30.1.0.2/32                      None     192.168.0.2          Only Path       100           65002 ?
	 *>  10.1.0.2/32                      None     0.0.0.0              Only Path                     ?
	 *>  110.1.9.0/24                     None     10.1.0.2             Only Path                     ?
	 *>  130.1.6.0/24                     None     192.168.0.2          Only Path       100           65002 ?
	 *>  130.1.1.0/24                     None     192.168.0.2          Only Path       100           65002 ?
	 *>  130.1.9.0/24                     None     192.168.0.2          Only Path       100           65002 ?
	 *>  110.1.1.0/24                     None     10.1.0.2             Only Path                     ?
	 *>  110.1.4.0/24                     None     10.1.0.2             Only Path                     ?
	 *>  110.1.3.0/24                     None     10.1.0.2             Only Path                     ?
	 *>  110.1.7.0/24                     None     10.1.0.2             Only Path                     ?
	 *>  130.1.0.0/24                     None     192.168.0.2          Only Path       100           65002 ?
	 *>  130.1.4.0/24                     None     192.168.0.2          Only Path       100           65002 ?
	 *>  130.1.8.0/24                     None     192.168.0.2          Only Path       100           65002 ?
	 *>  110.1.8.0/24                     None     10.1.0.2             Only Path                     ?

	(...snip)

BGP経路情報に加えて、MPLSラベル情報も確認してみます.

	$ ./get_mpls.sh 
	======================================================================
	get_mpls
	======================================================================
	/openflow/0000000000000001/mpls
	----------
	reply: 'HTTP/1.1 200 OK\r\n'
	header: Content-Type: application/json; charset=UTF-8
	header: Content-Length: 18603
	header: Date: Wed, 23 Sep 2015 05:04:25 GMT
	+++++++++++++++++++++++++++++++
	2015/09/23 05:04:25 : MplsTable 
	+++++++++++++++++++++++++++++++
	routeDist  prefix             nexthop          label
	---------- ------------------ ---------------- -----
	65001:101  10.1.0.2/32        0.0.0.0          1000 
	65001:101  110.1.0.0/24       10.1.0.2         1001 
	65001:101  110.1.1.0/24       10.1.0.2         1001 
	65001:101  110.1.2.0/24       10.1.0.2         1001 
	65001:101  110.1.3.0/24       10.1.0.2         1001 
	65001:101  110.1.4.0/24       10.1.0.2         1001 
	65001:101  110.1.5.0/24       10.1.0.2         1001 
	65001:101  110.1.6.0/24       10.1.0.2         1001 
	65001:101  110.1.7.0/24       10.1.0.2         1001 
	65001:101  110.1.8.0/24       10.1.0.2         1001 
	65001:101  110.1.9.0/24       10.1.0.2         1001 
	65001:101  130.1.0.0/24       192.168.0.2      2001 
	65001:101  130.1.1.0/24       192.168.0.2      2001 
	65001:101  130.1.2.0/24       192.168.0.2      2001 
	65001:101  130.1.3.0/24       192.168.0.2      2001 
	65001:101  130.1.4.0/24       192.168.0.2      2001 
	65001:101  130.1.5.0/24       192.168.0.2      2001 
	65001:101  130.1.6.0/24       192.168.0.2      2001 
	65001:101  130.1.7.0/24       192.168.0.2      2001 
	65001:101  130.1.8.0/24       192.168.0.2      2001 
	65001:101  130.1.9.0/24       192.168.0.2      2001 
	65001:101  30.1.0.2/32        192.168.0.2      2000 

	(...snip)


### Dockerコンテナへアクセス
dockerコンテナ"host_001_101"にアクセスして、ネットワーク情報を確認してみます.

	$ docker exec -it host_001_101 bash
	# route -n
	Kernel IP routing table
	Destination     Gateway         Genmask         Flags Metric Ref    Use Iface
	0.0.0.0         10.1.0.1        0.0.0.0         UG    0      0        0 eth0
	10.1.0.0        0.0.0.0         255.255.255.0   U     0      0        0 eth0
	110.1.0.0       0.0.0.0         255.255.255.0   U     0      0        0 eth1
	110.1.1.0       0.0.0.0         255.255.255.0   U     0      0        0 eth2
	110.1.2.0       0.0.0.0         255.255.255.0   U     0      0        0 eth3
	110.1.3.0       0.0.0.0         255.255.255.0   U     0      0        0 eth4
	110.1.4.0       0.0.0.0         255.255.255.0   U     0      0        0 eth5
	110.1.5.0       0.0.0.0         255.255.255.0   U     0      0        0 eth6
	110.1.6.0       0.0.0.0         255.255.255.0   U     0      0        0 eth7
	110.1.7.0       0.0.0.0         255.255.255.0   U     0      0        0 eth8
	110.1.8.0       0.0.0.0         255.255.255.0   U     0      0        0 eth9
	110.1.9.0       0.0.0.0         255.255.255.0   U     0      0        0 eth10


さらに、対向BGPルータ側に接続されたhost(30.1.0.2)に対して、疎通性を確認してみます.

	# ping 30.1.0.2
	PING 30.1.0.2 (30.1.0.2) 56(84) bytes of data.
	64 bytes from 30.1.0.2: icmp_seq=1 ttl=64 time=1.40 ms
	64 bytes from 30.1.0.2: icmp_seq=2 ttl=64 time=1.72 ms
	64 bytes from 30.1.0.2: icmp_seq=3 ttl=64 time=1.40 ms
	64 bytes from 30.1.0.2: icmp_seq=4 ttl=64 time=1.56 ms
	64 bytes from 30.1.0.2: icmp_seq=5 ttl=64 time=1.22 ms
	^C
	--- 30.1.0.2 ping statistics ---
	5 packets transmitted, 5 received, 0% packet loss, time 4011ms
	rtt min/avg/max/mdev = 1.222/1.462/1.723/0.173 ms

	# exit


### RyuBGPでの通過パケット流量を確認
RyuBGPが転送したパケット流量を確認します.
以下の表示例では、上りパケット数と下りパケット数が同量であったことがわかります.
これは、さきほどのホスト間でのping通信(ICMP Echo request/reply)がすべて成功したことを裏付ける結果となります.

	$ ./get_flow_stats.sh 
	======================================================================
	get_flowstats
	======================================================================
	/openflow/0000000000000001/stats/flow
	----------
	reply: 'HTTP/1.1 200 OK\r\n'
	header: Content-Type: application/json; charset=UTF-8
	header: Content-Length: 1577
	header: Date: Wed, 23 Sep 2015 05:15:22 GMT
	+++++++++++++++++++++++++++++++
	2015/09/23 05:15:22 : FlowStats
	+++++++++++++++++++++++++++++++
	destination(label) packets    bytes
	------------------ ---------- ----------
	1000                       72       7344
	1001                        0          0
	1002                        0          0

	(...snip)
	
	130.1.5.0/24                0          0
	130.1.6.0/24                0          0
	130.1.7.0/24                0          0
	130.1.8.0/24                0          0
	130.1.9.0/24                0          0
	30.1.0.2                   72       7056


いっぽう、RyuBGPが転送したパケット流量を、port単位で確認することも可能です.

	$ ./get_port_stats.sh 
	======================================================================
	get_portstats
	======================================================================
	/openflow/0000000000000001/stats/port
	----------
	reply: 'HTTP/1.1 200 OK\r\n'
	header: Content-Type: application/json; charset=UTF-8
	header: Content-Length: 1438
	header: Date: Wed, 23 Sep 2015 05:25:11 GMT
	+++++++++++++++++++++++++++++++
	2015/09/23 05:25:11 : PortStats
	+++++++++++++++++++++++++++++++
	portNo   rxPackets rxBytes  rxErrors txPackets txBytes  txErrors
	-------- --------- -------- -------- --------- -------- --------
	       1       529    42178        0       887   101990        0
	       2       749    90506        0       415    31420        0
	       3       115     9286        0       111     9006        0
	       4        43     2230        0        39     1950        0
	       5        43     2230        0        39     1950        0
	       6        42     2188        0        38     1908        0
	       7        42     2188        0        38     1908        0
	       8        42     2188        0        38     1908        0
	       9        42     2188        0        38     1908        0
	       a        42     2188        0        38     1908        0
	       b        42     2188        0        38     1908        0
	       c        42     2188        0        38     1908        0


### Dockerコンテナ停止
Dockerコンテナを停止します.

	$ sudo python pseudo-wan.py stop

	(...snip)


Dockerコンテナが起動していないことを確認します.

	$ docker ps
	CONTAINER ID        IMAGE               COMMAND             CREATED             STATUS              PORTS
