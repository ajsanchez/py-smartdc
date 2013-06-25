from __future__ import print_function
from .legacy import LegacyDataCenter
from .network import Network
from .machine import Machine

import re
import sys

class TefDataCenter(LegacyDataCenter):
    """
    This class provides support for the network extensiones present
    on TEF datacenters to the legacy (~6.5) SmartDataCenter API.

    More information: https://api-eu-lon-1.instantservers.telefonica.com/docs/networkapi_docs.html
    """

    def create_network(self, name, subnet, resolver_ips=None):
        """
        ::

            POST /:login/networks

        Provision a machine in the current
        :py:class:`smartdc.tef.TefDataCenter`, returning an instantiated
        :py:class:`smartdc.network.Network` object.

        :param name: a human-readable label for the machine
        :type name: :py:class:`basestring`, up to 32 letters, digits and
        hyphens. This parameter value is required.

        :param subnet: a private :type subnet: :py:class:`basestring` (CDR),
        containing a base IP address plus a mask, which must be in the
        range from /22 to /27. This parameter value is required.

        :param resolver_ips: list of DNS resolver IPs to be used by the
        subnet. If not supplied, the default IPs ("8.8.8.8" and "4.4.4.4")
        will be used.
        :type resolver_ips: :py:class:`list`

        :rtype: :py:class:`smartdc.network.Network'
        """
        params = {}
        assert re.match(r'[a-zA-Z0-9-]{1,32}', name), "Illegal name"
        params['name'] = name
        assert re.match(r'[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+\/[0-9]+',
            subnet), "Illegal subnet"
        params['subnet'] = subnet
        if resolver_ips:
            if isinstance(resolver_ips, list):
                params['resolver_ips'] = resolver_ips
        j, r = self.request('POST', 'networks', data=params)
        if r.status_code >= 400:
            print(j, file=sys.stderr)
            r.raise_for_status()
        return Network(datacenter=self, data=j)

    def raw_network_data(self, network_id):
        """
        ::

            GET /:login/networks/:network

        :param network_id: identifier for the network
        :type network_id: :py:class:`basestring` or :py:class:`dict`

        :rtype: :py:class:`dict`

        Primarily used internally to get a raw dict for a single network.
        """
        params = {}
        if isinstance(network_id, dict):
            network_id = network_id['id']
        j, r = self.request('GET', 'networks/' + str(network_id),
            params=params)
        return j

    def networks(self, search=None, fields=('name,')):
        """
        ::

            GET /:login/networks

        :param search: optionally filter (locally) with a regular expression
            search on the listed fields
        :type search: :py:class:`basestring` that compiles as a regular
            expression

        :param fields: filter on the listed fields (defaulting to
            ``name``)
        :type fields: :py:class:`list` of :py:class:`basestring`\s

        :Returns: network available in this datacenter
        :rtype: :py:class:`list` of :py:class:`dict`\s
        """
        j, _ = self.request('GET', 'networks')
        if search:
            j = list(search_dicts(j, search, fields))
        return [Network(datacenter=self, data=m) for m in j]

    def network(self, identifier):
        """
        ::

            GET /:login/networks/:id

        :param identifier: match on the listed network identifier
        :type identifier: :py:class:`basestring` or :py:class:`dict`

        :Returns: characteristics of the requested network
        :rtype: :py:class:`dict`

        Either a string or a dictionary with an ``id`` key may be passed in.
        """

        if isinstance(identifier, dict):
            identifier = identifier.get('id')
        j, _ = self.request('GET', 'networks/' + str(identifier))
        return j

    def create_machine(self, name=None, package=None, dataset=None,
            metadata=None, tags=None, boot_script=None, credentials=False,
            image=None, network_id=None):
        """
        ::

        POST /:login/machines

        Provision a machine in the current 
        :py:class:`smartdc.tef.TefDataCenter`, returning an instantiated 
        :py:class:`smartdc.machine.Machine` object. All of the parameter 
        values are optional, as they are assigned default values by the 
        datacenter's API itself.

        :param name: a human-readable label for the machine
        :type name: :py:class:`basestring`

        :param package: cluster of resource values identified by name
        :type package: :py:class:`basestring` or :py:class:`dict`

        :param image: an identifier for the base operating system image
            (formerly a ``dataset``)
        :type image: :py:class:`basestring` or :py:class:`dict`

        :param dataset: base operating system image identified by a globally 
            unique ID or URN (deprecated)
        :type dataset: :py:class:`basestring` or :py:class:`dict`

        :param metadata: keys & values with arbitrary supplementary 
            details for the machine, accessible from the machine itself
        :type metadata: :py:class:`dict`

        :param tags: keys & values with arbitrary supplementary 
            identifying information for filtering when querying for machines
        :type tags: :py:class:`dict`

        :param network_id: network id where this machine will belong to; if
            omitted, the machine will have a public IP address. PLEASE note
            that if this parameter is specified, then ``name``, ``package``
            and ``dataset`` are compulsory.
        :type network_id: :py:class:`basestring`

        :param boot_script: path to a file to upload for execution on boot
        :type boot_script: :py:class:`basestring` as file path

        :rtype: :py:class:`smartdc.machine.Machine`

        If `package`, `image`, or `dataset` are passed a :py:class:`dict` containing a 
        `name` key (in the case of `package`) or an `id` key (in the case of
        `image` or `dataset`), it passes the corresponding value. The server API 
        appears to resolve incomplete or ambiguous dataset URNs with the 
        highest version number.
        """
        params = {}
        if name:
            assert re.match(r'[a-zA-Z0-9]([a-zA-Z0-9\-\.]*[a-zA-Z0-9])?$',
                name), "Illegal name"
            params['name'] = name
        if package:
            if isinstance(package, dict):
                package = package['name']
            params['package'] = package
        if image:
            if isinstance(image, dict):
                image = image['id']
            params['image'] = image
        if dataset and not image:
            if isinstance(dataset, dict):
                dataset = dataset.get('id', dataset['urn'])
            params['dataset'] = dataset
        if metadata:
            for k, v in metadata.items():
                params['metadata.' + str(k)] = v
        if tags:
            for k, v in tags.items():
                params['tag.' + str(k)] = v
        if boot_script:
            with open(boot_script) as f:
                params['metadata.user-script'] = f.read()
        if network_id:
            if isinstance(network_id, basestring):
                params['network_id'] = network_id
        j, r = self.request('POST', 'machines', data=params)
        if r.status_code >= 400:
            if self.verbose:
                print(j, file=sys.stderr)
            r.raise_for_status()
        return Machine(datacenter=self, data=j)
