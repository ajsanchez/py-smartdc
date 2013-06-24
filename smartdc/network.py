import requests
import time
import uuid
import json

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
		return '<{module}.{cls}: {name} in {dc}'.format(
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

		if isinstance(j, basestring): j = json.loads(j) #BUGBUGBUG

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

		if isinstance(j, basestring): j = json.loads(j) #BUGBUGBUG

		return j['enabled']
