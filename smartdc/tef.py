from __future__ import print_function
from .legacy import LegacyDataCenter
from .network import Network

import re

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

		if isinstance(j, basestring): j = eval(j) #BUGBUGBUG

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

		if isinstance(j, basestring): j = eval(j) #BUGBUGBUG

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

		if isinstance(j, basestring): j = eval(j) #BUGBUGBUG

		if search:
			return list(search_dicts(j, search, fields))
		else:
			return j

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

		if isinstance(j, basestring): j = eval(j) #BUGBUGBUG

		return j
