import requests
import time
import uuid
import json
import re

__all__ = ['Network']

class Network(object):
    """
    A local proxy representing the state of a remote NetworkAPI subnet.

    A :py:class:`smartdc.network.Network` object is intended to be a
    convenient container for methods and data relevant to a remotely running
    subnet managed by NetworkAPI. A :py:class:`smartdc.network.Network` is
    tied to a :py:class:`smartdc.tef.TefDataCenter` object, and makes all
    its requests via that interface. It does not attempt to manage the state
    cache in most cases, instead requiring the user to explicitly update with
    a :py:meth:`refresh` call.
    """
    def __init__(self, datacenter, network_id=None, data=None):
        """
        :param datacenter: datacenter that contains this network
        :type datacenter: :py:class:`smartdc.tef.TefDataCenter`

        :param network_id: unique ID of the network
        :type network_id: :py:class:`basestring`

        :param data: raw data for instantiation
        :type data: :py:class:`dict`

        Typically, a :py:class:`smartdc.network.Network` object is
        instantiated automatically by a
        :py:class:`smartdc.tef.TefDataCenter` object, but a user may
        instantiate one with a minimum of a `datacenter` parameter and a
        unique ID according to the network. The object then pulls in the
        network data from the datacenter API. If `data` is passed in to
        instantiate, then ingest the dict and populate internal values from
        that.

        All of the following attributes are read-only:

        :var name: human-readable label for the network
        :var id: identifier for the network
        :var subnet: private subnet (CIDR)
        :var resolver_ips: :py:class:`list` of DNS resolver IPs
        :var private_gw_ip: private IP of the subnet gateway (:py:class:`basestring`)
        :var public_gw_ip: public IP of the subnet gateway (:py:class:`basestring`)
        :var status: last-known state of the network (:py:class:`basestring`)
        """
        self.id = network_id or data.pop('id')
        self.datacenter = datacenter
        """the :py:class:`smartdc.tef.TefDataCenter` object that holds
        this machine"""
        if not data:
            data = self.datacenter.raw_network_data(self.id)
        self._save(data)

    def __str__(self):
        """
        Represents the Network by its unique ID as a string.
        """
        return self.id

    def __repr__(self):
        """
        Presents a readable representation.
        """
        if self.datacenter:
            dc = str(self.datacenter)
        else:
            dc = '<None>'
        return '<{module}.{cls}: <{name}> in {dc}>'.format(
            module=self.__module__, cls=self.__class__.__name__,
            name=self.name, dc=dc)

    def __eq__(self, other):
        if isinstance(other, dict):
            return self.id == other.get('id')
        elif isinstance(other, Network):
            return self.id == other.id
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return uuid.UUID(self.id).int

    def _save(self, data):
        """
        Take the data from a dict and commit them to appropriate attributes.
        """
        self.name = data.get('name')
        self.subnet = data.get('subnet')
        self.resolver_ips = data.get('resolver_ips')
        self.private_gw_ip = data.get('private_gw_ip')
        self.public_gw_ip = data.get('public_gw_ip')
        self.state = data.get('status')
        
    @property
    def path(self):
        """
        Convenience property to insert the id into a relative path for
        requests.
        """
        return 'networks/{id}'.format(id=self.id)

    @classmethod
    def create_in_datacenter(cls, datacenter, name, subnet, **kwargs):
        """
        ::

            POST /:login/networks

        Class method, provided as a convenience.

        :param dataceter: datacenter for creating the network
        :type datacenter: :py:class:`smartdc.tef.TefDataCenter`

        Provision a network in the current
        :py:class:`smartdc.tef.TefDataCenter`, returning an
        instantiated :py:class:`smartdc.network.Network` object.
        
        'datacenter', 'name' and 'subnet' are required arguments.
        The rest of them are passed to the datacenter object as with
        :py:meth:`smartdc.tef.TefDataCenter.create_network`.
        """
        return datacenter.create_network(name, subnet, **kwargs)

    def refresh(self):
        """
        ::

            GET /:login/networks/:id

        Fetch the existing status and values for the
        :py:class:`smartdc.network.Network` from the datacenter
        and commit the values locally.
        """
        data = self.datacenter.raw_network_data(self.id)
        self._save(data)

    def status(self):
        """
        ::

            GET /:login/networks/:id

        :Returns: the current network status
        :rtype: :py:class:`basestring`

        Refresh the network's information by fetching it remotely, then
        returning the :py:attr:`state` as a string.
        """
        self.refresh()
        return self.state

    def delete(self):
        """
        ::

            DELETE /:login/machines/:id

        Initiate deletion of an empty network.
        """
        j, r = self.datacenter.request('DELETE', self.path)
        r.raise_for_status()

    def poll_until(self, status, interval=2):
        """
        ::

            GET /:login/networks/:id

        :param status: target status
        :type status: :py:class:`basestring`

        :param interal: pause in seconds between polls
        :type interval: :py:class:`int`

        Convenience method that continuously polls the current state of the
        machine remotely, and returns until the named `status` argument is
        reached. The default wait `interval` between requests is 2 seconds,
        but it may be changed.

        .. Note:: If the next status is wrongly identified, this method may
            loop forever.
        """
        while self.status() != status:
            time.sleep(interval)

    def poll_while(self, status, interval=2):
        """
        ::

            GET /:login/networks/:id

        :param status: (assumed) current status
        :type status: :py:class:`basestring`

        :param interval: pause in seconds between polls
        :type interval: :py:class:`int`

        Convenience method that continuously polls the current status of the
        network remotely, and returns while the network has the named `status`
        argument. Once the status changes, the method returns. The default wait
        `interval` between requests is 2 seconds, but it may be changed.

        .. Note:: If a status transition has not correctly been triggered, this
            method may loop forever.
        """
        while self.status() == status:
            time.sleep(interval)

    def set_outbound(self, enabled):
        """
        ::

            PUT /:login/networks/:id/outbound

        :param enabled: new status for the curret network outbound PAT (Port
            Address Translation).
        :type enabled: :py:class:`bool`

        :Returns: the updated network outbound PAT (Port Address Translation)
            status.
        :rtype: :py:class:`bool`
        """
        assert isinstance(enabled, bool), "Illegal status"
        j, _ = self.datacenter.request('PUT', self.path + '/outbound',
            data={ 'enabled': enabled })
        return j['enabled']
        
    def get_outbound(self):
        """
        ::

            GET /:login/networks/:id/outbound

        :Returns: the current network outbound PAT (Port Address Translation)
            status.
        :rtype: :py:class:`bool`
        """
        j, _ = self.datacenter.request('GET', self.path + '/outbound')
        return j['enabled']

    def get_inbound_rules(self):
        """
        ::
        
            GET /:login/networks/:id/inbound
            
        :Returns: a list containing all the inbound port forwarding
            rules for the current Netowrk.
        :rtype: :py:class:`list` of :py:class:`dict`
        """
        j, _ = self.datacenter.request('GET', self.path + '/inbound')
        return j
        
    def add_inbound_rule(self, name, start_port, destination_ip, end_port=None,
            protocols=None, source_subnet=None, destination_base_port=None):
        """
        ::
        
            PUT /:login/networks/:id/inbound
            
        :param name: the name of the new inbound port forwarding rule
            to add. Up to 32 letters, digits and hyphens. Required.
        :type name: :py:class:`basestring`
        
        :param start_port: first inbound port to forward according to this
            rule (0...65535). Required.
        :type start_port: :py:class:`int`
        
        :param end_port: last inbound port to forward according to this rule
            (0...65535). If ommitted, the `start_port` will be taken.
        :type end_port: :py:class:`int`
        
        :param protocols: list of protocols to forward according to this list.
            Can be a list of strings or a single value. If omitted, both TCP
            and UPD will be forwarded.
        :type protocols: :py:class:`list` or :py:class:`basestring`
        
        :param source_subnet: a CIDR specifying the origin of the traffic to
            be forwarded. If omitted, it will be set to '0.0.0.0/0', thus
            forwarding all incoming traffic.
        :type source_subnet: :py:class:`basestring`
        
        :param destination_ip: internal IP to which the inbound traffic
            accepted by this rule should be forwarded to. Required.
        :type destination_ip: :py:class:`basestring`
        
        :param destination_base_port: (first) port of the destination IP to 
            forward the inbound traffic to (0...65535). If omitted, the 
            `start_port` will be taken.
        :type destination_base_port: :py:class:`int`
        
        :Returns: a dict containing the new inbound port forwarding rule.
        :rtype: :py:class:`dict`
        """
        params = {}
        assert re.match(r'[a-zA-Z0-9-_]{1,32}', name), "Illegal name"
        params['name'] = name
        assert start_port>=0 and start_port<=65535, "Illegal start_port"
        params['start_port'] = start_port
        if end_port:
            assert end_port>=start_port and end_port<=65535, \
                    "Illegal end_port"
        else:
            end_port = start_port
        params['end_port'] = end_port
        if protocols:
            if isinstance(protocols, basestring):
                protocols = [protocols]
        else:
            protocols = ["tcp", "udp"]
        params['protocols'] = protocols
        if source_subnet:
            assert re.match(r'[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+(\/[0-9]+)?', \
                    source_subnet), "Illegal source_subnet"
            if not source_subnet.find('/'):
                source_subnet = source_subnet + "/32"
            params['source_subnet'] = source_subnet
        assert re.match(r'[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+', destination_ip), \
                "Illegal destination_ip"
        params['destination_ip'] = destination_ip
        if destination_base_port:
            assert destination_base_port>=0 and destination_base_port<=65535, \
                    "Illegal destination_base_port"
        else:
            destination_base_port = start_port
        params['destination_base_port'] = destination_base_port
        j, r = self.datacenter.request('POST', self.path + '/inbound', data=params)
        r.raise_for_status()
        return j

