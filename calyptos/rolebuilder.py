import yaml


class RoleBuilder():

    # Global list of roles
    ROLE_LIST = ['clc',
                 'user-facing',
                 'console',
                 'walrus',
                 'cluster-controller',
                 'storage-controller',
                 'node-controller',
                 'midonet-cluster',
                 'midolman',
                 'mon-bootstrap',
                 'ceph-mons',
                 'ceph-osds',
                 'riak-head',
                 'riak-node',
                 'haproxy',
                 'nginx',
                 'zookeeper',
                 'cassandra',
                 'all']

    def __init__(self, environment_file='environment.yml'):
        self.environment_file = environment_file
        self.env_dict = self.get_all_attributes()
        self.roles = self.get_roles()
        self.all_hosts = self.roles['all']

    def read_environment(self):
        with open(self.environment_file) as env_file:
            return yaml.load(env_file.read())

    def get_all_attributes(self):
        env_dicts = self.read_environment()
        return env_dicts['default_attributes']

    def get_euca_attributes(self):
        try:
            return self.env_dict['eucalyptus']
        except:
            return None

    def get_riak_attributes(self):
        try:
            return self.env_dict['riakcs_cluster']
        except:
            return None

    def get_zookeeper(self):
        try:
            return self.env_dict['zookeeper']
        except:
            return None

    def get_cassandra(self):
        try:
            return self.env_dict['cassandra']
        except:
            return None

    def get_ceph_attributes(self):
        try:
            return self.env_dict['ceph']
        except:
            return None

    def _initialize_roles(self):
        roles = {}
        for role in self.ROLE_LIST:
            roles[role] = set()
        return roles

    def get_euca_hosts(self):
        roles = self.get_roles()

        # Create set of Eucalytpus only componnents
        euca_components = ['user-facing', 'cluster-controller',
                           'storage-controller', 'node-controller']
        if roles['walrus']:
            euca_components.append('walrus')

        all_hosts = roles['clc']
        for component in euca_components:
            all_hosts.update(roles[component])
        return all_hosts

    def get_roles(self):
        roles = self._initialize_roles()
        euca_attributes = self.get_euca_attributes()
        ceph_attributes = self.get_ceph_attributes()
        riak_attributes = self.get_riak_attributes()
        zookeeper = self.get_zookeeper()
        cassandra = self.get_cassandra()

        roles['all'] = set([])

        if riak_attributes:
            riak_topology = riak_attributes['topology']
            if riak_topology['head']:
                roles['riak-head'] = set([riak_topology['head']['ipaddr']])
                roles['all'].add(riak_topology['head']['ipaddr'])
            else:
                raise Exception("No head node found for RiakCS cluster!")

            if riak_topology.get('nodes'):
                for n in riak_topology['nodes']:
                    roles['riak-node'].add(n)
                    roles['all'].add(n)
            if riak_topology.get('load_balancer'):
                riak_lb = None
                if self.env_dict.get('nginx'):
                    riak_lb = 'nginx'
                    raise Exception("Nginx: Not implemented yet.")
                elif self.env_dict.get('haproxy'):
                    riak_lb = 'haproxy'
                else:
                    raise Exception("No Load-Balancer found for RiakCS cluster.")
                roles[riak_lb] = set([riak_topology['load_balancer']])
                roles['all'].add(riak_topology['load_balancer'])

        if ceph_attributes:
            ceph_topology = ceph_attributes['topology']
            if ceph_topology.get('mons'):
                mon_bootstrap = set()
                monset = set()
                for mon in ceph_topology['mons']:
                    if mon.get('init') and not mon_bootstrap:
                        mon_bootstrap.add(mon['ipaddr'])
                    monset.add(mon['ipaddr'])
                    roles['all'].add(mon['ipaddr'])
                if not mon_bootstrap:
                    raise Exception("No Initial Ceph Monitor found! Please mention at least one initial monitor.\n"
                                    "e.g\n"
                                    "mons:\n"
                                    "  - ipaddr: '10.10.1.5'\n"
                                    "    hostname: 'node1'\n"
                                    "    init: true")
                roles['ceph-mons'] = monset
                roles['mon-bootstrap'] = mon_bootstrap

            if ceph_topology['osds']:
                osdset = set()
                for osd in ceph_topology['osds']:
                    osdset.add(osd['ipaddr'])
                    roles['all'].add(osd['ipaddr'])
                roles['ceph-osds'] = osdset
            else:
                raise Exception("No OSD Found!")

        if euca_attributes:
            topology = euca_attributes['topology']

            # Add CLC
            roles['clc'] = set(topology['clc'])
            roles['configure-eucalyptus'] = set()
            for clc in topology['clc']:
                roles['all'].add(clc)
                # Eucalyptus needs to be configure once
                if len(roles['configure-eucalyptus']) < 1:
                    roles['configure-eucalyptus'].add(clc)

            # Add UFS
            roles['user-facing'] = set(topology['user-facing'])
            for ufs in topology['user-facing']:
                roles['all'].add(ufs)

            # add console
            if 'console' in topology:
                roles['console'] = set(topology['console'])
                for console in topology['console']:
                    roles['all'].add(console)

            # Add Walrus
            if 'objectstorage' in topology:
                provider_client = topology['objectstorage']['providerclient']
                if provider_client:
                    walrus_backends = topology['objectstorage']['walrusbackend']
                    roles['walrus'] = set(walrus_backends)
                    for walrus in walrus_backends:
                        roles['all'].add(walrus)
            else:
                # No walrus defined assuming RiakCS
                roles['walrus'] = set()

            # Add cluster level components
            for name in topology['clusters']:
                roles['cluster'] = {}
                if 'cc' in topology['clusters'][name]:
                    cc = topology['clusters'][name]['cc']
                    for c in cc:
                        roles['cluster-controller'].add(c)
                else:
                    raise IndexError("Unable to find CC in topology for cluster " + name)

                if 'sc' in topology['clusters'][name]:
                    sc = topology['clusters'][name]['sc']
                    for s in sc:
                        roles['storage-controller'].add(s)
                else:
                    raise IndexError("Unable to find SC in topology for cluster " + name)

                roles['cluster'][name] = set(cc)
                roles['cluster'][name].update(sc)
                if 'nodes' in topology['clusters'][name]:
                    nodes = topology['clusters'][name]['nodes']
                else:
                    raise IndexError("Unable to find nodes in topology for cluster " + name)
                for node in nodes:
                    roles['node-controller'].add(node)
                    roles['cluster'][name].add(node)
                roles['all'].update(roles['cluster'][name])

        if zookeeper:
            roles['zookeeper'] = set(zookeeper['topology'])
            for zk in zookeeper['topology']:
                roles['all'].add(zk)

        if cassandra:
            roles['cassandra'] = set(cassandra['topology'])
            for cs in cassandra['topology']:
                roles['all'].add(cs)

        if euca_attributes['network']['mode'] == 'VPCMIDO':
            # in VPC mode, midonet-cluster/midonet-api host is essentially a
            # CLC host where eucanetd is running, unless it changes in future
            midonet_cluster = euca_attributes['topology']['clc']
            roles['configure-vpc'] = set()
            for mc in midonet_cluster:
                roles['midonet-cluster'].add(mc)
                # VPC needs to be configure once from midonet-cluster
                if len(roles['configure-vpc']) < 1:
                    roles['configure-vpc'].add(mc)

            midonet = euca_attributes.get('midonet', None)
            midolman_host_mapping = midonet.get('midolman-host-mapping', None)
            for hostname, host_ip in midolman_host_mapping.iteritems():
                roles['midolman'].add(host_ip)
        return roles
