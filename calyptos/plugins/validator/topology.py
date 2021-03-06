from calyptos.plugins.validator.validatorplugin import ValidatorPlugin

class Topology(ValidatorPlugin):
    def validate(self):
        self.failed_hosts = []
        self.good_hosts = []
        # Check each cluster
        self._single_cluster_per_host()

        riakcs_keys_master = ['access-key', 'admin-email', 'admin-name', 'endpoint', 'port', 'secret-key']
        self.topology = self.environment['default_attributes']['eucalyptus']['topology']
        assert self.roles['clc']
        assert self.roles['user-facing']
        if 'walrus' in self.topology and 'riakcs' in self.topology:
            raise AssertionError("Can only have riakcs or walrus in topology, not both")
        if 'walrus' in self.topology:
            assert self.roles['walrus']
            self.success('Found valid walrus key')
        elif 'riakcs' in self.topology:
            for val in riakcs_keys_master:
                try:
                    assert val in self.topology['riakcs']
                    self.success('Found riakcs key: ' + val)
                except AssertionError, e:
                    self.failure('riakcs key "' + val + '" is missing or invalid!  ' + str(e))
        for name in self.topology['clusters'].keys():
            assert self.topology['clusters'][name]['cc-1']
            assert self.topology['clusters'][name]['sc-1']
            self.success('Cluster ' + name + ' has both an SC and CC')
            assert self.topology['clusters'][name]['nodes']
            self.success('Cluster ' + name + ' has node controllers')



    def _single_cluster_per_host(self):
        cluster_hosts = self.roles['cluster']
        for name, hosts in cluster_hosts.iteritems():
            # Check that each host...
            for host in hosts:
                # Only appears in one cluster
                appearances = []
                for cluster in cluster_hosts.keys():
                    if host in cluster:
                        appearances.append(cluster)
                if len(appearances) > 1:
                    raise AssertionError("Found " + host + " in multiple clusters: " + str(
                            appearances))
                else:
                    self.success(host + " only in 1 cluster")
                    self.good_hosts.append(host)









