What's docker-pseudo-wan
==========
Dockerコンテナを活用して、WANネットワークの疑似環境を構築するものです.

	                   (static) +------------+         mp-BGP         +----------+	
	host_001 container -------+ |   RyuBGP   | +--------------------+ |   BGP    | +---- ...
	host_002 container -------+ |  container |                        |  Router  |
	     :                      +------------+                        +----------+
	              < AS65000 >        192.168.0.2                    192.168.0.1       < AS9598 >


Environment
==========
Ubuntu Server版を推奨とします.

	$ cat /etc/lsb-release
	DISTRIB_ID=Ubuntu
	DISTRIB_RELEASE=14.04
	DISTRIB_CODENAME=trusty
	DISTRIB_DESCRIPTION="Ubuntu 14.04.3 LTS"

Dockerコンテナで構成されるWANネットワークと外部環境と通信するために、eth1のインタフェースを前提とします.

	$ ip link
        ...
	3: eth1: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc pfifo_fast state UP mode DEFAULT group default qlen 1000
	    link/ether 00:0c:29:fc:4f:25 brd ff:ff:ff:ff:ff:ff


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
	REPOSITORY                 TAG                 IMAGE ID            CREATED             VIRTUAL SIZE
	ttsubo/ryubgp-for-general  latest              acc83513331e        4 hours ago         640.9 MB
	ubuntu                     14.04.2             63e3c10217b8        4 weeks ago         188.4 MB


Quick Start
===========
### Dockerコンテナ起動
WANネットワークの疑似環境を構築します.

	$ sudo python pseudo-wan.py

	(...snip)


Dockerコンテナ実行状況を確認します.

	$ docker ps

	(...snip)
	CONTAINER ID        IMAGE                             COMMAND             CREATED              STATUS              PORTS                    NAMES
	070df0f5266e        ubuntu:14.04.2                    "bash"              36 seconds ago       Up 35 seconds                                host_006
	15eaaca1d8cf        ubuntu:14.04.2                    "bash"              52 seconds ago       Up 51 seconds                                host_005
	d292c4438bdf        ubuntu:14.04.2                    "bash"              About a minute ago   Up About a minute                            host_004
	e918d9f264a4        ubuntu:14.04.2                    "bash"              About a minute ago   Up About a minute                            host_003
	3fbe44a98f79        ubuntu:14.04.2                    "bash"              About a minute ago   Up About a minute                            host_002
	d0373f6e2480        ubuntu:14.04.2                    "bash"              About a minute ago   Up About a minute                            host_001
	e759ab624c1c        ttsubo/ttsubo/ryubgp-for-general  "bash"              2 minutes ago        Up 2 minutes        0.0.0.0:8080->8080/tcp   BGP


Linuxブリッジ動作状況を確認します.

	$ brctl show
	bridge name	bridge id		STP enabled	interfaces
	br001-0		8000.429af835de7e	no		veth0pl22451
								veth3pl22012
	br001-1		8000.8ad213aa7d21	no		veth1pl22451
	br001-2		8000.6a2af35456c3	no		veth2pl22451
	br001-3		8000.ce5928055031	no		veth3pl22451
	br001-4		8000.eefe57da33e4	no		veth4pl22451
	br001-5		8000.4a7304fab1f3	no		veth5pl22451
	br002-0		8000.060c1ee00c64	no		veth0pl23383
								veth4pl22012

	(...snip)

	br_openflow		8000.000c29fc4f25	no		eth1
								veth1pl22012
	docker0		8000.aa25c6470df6	no		veth4a71ca0


### Dockerコンテナへアクセス
例えば、dockerコンテナ"host_001"にアクセスして、ネットワーク情報を確認してみます.

	$ docker exec -it host_001 bash
	# ip route
	default via 130.1.0.1 dev eth0
	130.1.0.0/24 dev eth0  proto kernel  scope link  src 130.1.0.2
	140.1.1.0/24 dev eth1  proto kernel  scope link  src 140.1.1.1
	140.1.2.0/24 dev eth2  proto kernel  scope link  src 140.1.2.1
	140.1.3.0/24 dev eth3  proto kernel  scope link  src 140.1.3.1
	140.1.4.0/24 dev eth4  proto kernel  scope link  src 140.1.4.1
	140.1.5.0/24 dev eth5  proto kernel  scope link  src 140.1.5.1
	# exit


### BGPルータでの経路情報を確認
dockerコンテナ"BGP"が開設しているBGPピア状態を確認してみます.
なお、コマンド操作は、linux母艦上で行います.

	$ cd show
	$ ./get_peer_status.sh
	======================================================================
	get_peer_status
	======================================================================
	/openflow/0000000000000001/status/peer
	----------
	reply: 'HTTP/1.1 200 OK\r\n'
	header: Content-Type: application/json; charset=UTF-8
	header: Content-Length: 194
	header: Date: Mon, 14 Sep 2015 07:59:50 GMT
	+++++++++++++++++++++++++++++++
	2015/09/14 07:59:50 : Peer Status
	+++++++++++++++++++++++++++++++
	occurTime            status    myPeer             remotePeer         asNumber
	-------------------- --------- ------------------ ------------------ --------
	2015/09/14 07:51:45  Peer Up   10.0.1.1           10.0.0.3           9598



さらに、dockerコンテナ"BGP"で保持しているBGP経路情報を確認してみます.

	$ ./get_rib.sh
	======================================================================
	get_rib
	======================================================================
	/openflow/0000000000000001/rib
	----------
	reply: 'HTTP/1.1 200 OK\r\n'
	header: Content-Type: application/json; charset=UTF-8
	header: Content-Length: 1781
	header: Date: Mon, 14 Sep 2015 07:59:32 GMT
	+++++++++++++++++++++++++++++++
	2015/09/14 07:59:32 : Show rib
	+++++++++++++++++++++++++++++++
	Status codes: * valid, > best
	Origin codes: i - IGP, e - EGP, ? - incomplete
	     Network                          Labels   Next Hop             Reason          Metric LocPrf Path
	 *>  9598:202:141.2.1.0/24            [1009]   131.2.0.2            Only Path                     ?
	 *>  9598:203:141.3.1.0/24            [1011]   131.3.0.2            Only Path                     ?
	 *>  9598:203:131.3.0.2/32            [1010]   0.0.0.0              Only Path                     ?
	 *>  9598:103:192.168.103.1/32        [33]     192.168.0.1          Only Path                     9598 ?
	 *>  9598:201:141.1.1.0/24            [1007]   131.1.0.2            Only Path                     ?
	 *>  9598:201:131.1.0.2/32            [1006]   0.0.0.0              Only Path                     ?
	 *>  9598:202:131.2.0.2/32            [1008]   0.0.0.0              Only Path                     ?
	 *>  9598:102:192.168.102.0/30        [32]     192.168.0.1          Only Path                     9598 ?
	 *>  9598:103:130.3.0.2/32            [1004]   0.0.0.0              Only Path                     ?
	 *>  9598:101:130.1.0.2/32            [1000]   0.0.0.0              Only Path                     ?
	 *>  9598:101:140.1.1.0/24            [1001]   130.1.0.2            Only Path                     ?
	 *>  9598:102:140.2.1.0/24            [1003]   130.2.0.2            Only Path                     ?
	 *>  9598:102:130.2.0.2/32            [1002]   0.0.0.0              Only Path                     ?
	 *>  9598:101:192.168.101.0/30        [29]     192.168.0.1          Only Path                     9598 ?
	 *>  9598:103:140.3.1.0/24            [1005]   130.3.0.2            Only Path                     ?




### Dockerコンテナ停止
Dockerコンテナを停止します.

	$ sudo python pseudo-wan.py stop

	(...snip)


Dockerコンテナが起動していないことを確認します.

	$ docker ps
	CONTAINER ID        IMAGE               COMMAND             CREATED             STATUS              PORTS
